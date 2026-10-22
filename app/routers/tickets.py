from __future__ import annotations

import logging
import uuid
from datetime import date
from pathlib import Path

from fastapi import (
    APIRouter,
    BackgroundTasks,
    File,
    HTTPException,
    Query,
    Request,
    UploadFile,
    status,
)
from fastapi.responses import FileResponse

from app import store
from app.dependencies import (
    ATTACHMENTS_DIR,
    current_user,
    require_staff,
    visible_ticket,
)
from app.notification_outbox import wake_notification_worker
from app.schemas import (
    AssignmentUpdate,
    CommentCreate,
    StatusUpdate,
    TicketCreate,
    TicketRating,
    TicketStatus,
    TicketUpdate,
)

logger = logging.getLogger(__name__)

router = APIRouter(tags=["tickets"])


def _get_attachments_dir() -> Path:
    import sys

    main_module = sys.modules.get("app.main")
    if main_module and hasattr(main_module, "ATTACHMENTS_DIR"):
        return getattr(main_module, "ATTACHMENTS_DIR")
    return ATTACHMENTS_DIR


@router.get("/staff")
def get_staff_directory(request: Request) -> list[dict[str, str]]:
    user = current_user(request)
    require_staff(user)
    return store.list_staff()


@router.get("/tickets")
def get_tickets(
    request: Request,
    status_filter: TicketStatus | None = Query(default=None, alias="status"),
    category: str | None = Query(default=None, max_length=50),
    q: str | None = Query(default=None, max_length=160),
    from_date: date | None = Query(default=None, alias="from"),
    to_date: date | None = Query(default=None, alias="to"),
) -> list[dict]:
    user = current_user(request)
    if from_date and to_date and from_date > to_date:
        raise HTTPException(status_code=422, detail="Ngày bắt đầu phải trước hoặc bằng ngày kết thúc.")
    return store.list_tickets(
        user["username"],
        user["role"],
        status_filter,
        category,
        q,
        from_date.isoformat() if from_date else None,
        to_date.isoformat() if to_date else None,
    )


@router.post("/tickets", status_code=status.HTTP_201_CREATED)
def create_new_ticket(
    request: Request,
    payload: TicketCreate,
    background_tasks: BackgroundTasks,
) -> dict:
    user = current_user(request)
    ticket = store.create_ticket(
        title=payload.title.strip(),
        description=payload.description.strip(),
        category=payload.category.strip().lower(),
        priority=payload.priority,
        requester=user["username"],
    )
    background_tasks.add_task(wake_notification_worker)
    return {"message": "Đã tạo ticket.", "ticket": ticket}


@router.get("/tickets/{ticket_id}")
def get_one_ticket(request: Request, ticket_id: int) -> dict:
    user = current_user(request)
    return visible_ticket(ticket_id, user)


@router.patch("/tickets/{ticket_id}")
def patch_ticket(request: Request, ticket_id: int, payload: StatusUpdate, background_tasks: BackgroundTasks) -> dict:
    user = current_user(request)
    ticket = visible_ticket(ticket_id, user)
    if user["role"] == "user":
        if not (
            ticket["status"] == "resolved"
            and payload.status in {"closed", "in_progress"}
        ):
            raise HTTPException(
                status_code=403,
                detail="Bạn chỉ có thể xác nhận đã giải quyết hoặc yêu cầu IT xử lý lại.",
            )
    else:
        require_staff(user)
        if payload.status == "closed":
            raise HTTPException(
                status_code=403,
                detail="Chỉ người gửi mới xác nhận đóng ticket đã giải quyết.",
            )
    try:
        ticket = store.update_ticket_status(ticket_id, payload.status, user["username"])
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    if payload.status == "escalated":
        background_tasks.add_task(wake_notification_worker)
    return {"message": "Đã cập nhật trạng thái.", "ticket": ticket}


@router.put("/tickets/{ticket_id}")
def update_ticket(request: Request, ticket_id: int, payload: TicketUpdate) -> dict:
    user = current_user(request)
    ticket = visible_ticket(ticket_id, user)
    if user["role"] == "user":
        if ticket["status"] != "new":
            raise HTTPException(
                status_code=409, detail="Chỉ có thể sửa ticket khi còn ở trạng thái Mới."
            )
    else:
        require_staff(user)
        if (
            ticket["status"] in {"resolved", "closed"}
            and payload.priority
            and payload.priority != ticket["priority"]
        ):
            raise HTTPException(
                status_code=409,
                detail="Không thể thay đổi mức độ ưu tiên trên ticket đã giải quyết hoặc đã đóng.",
            )
    try:
        updated = store.update_ticket_fields(
            ticket_id,
            user["username"],
            payload.model_dump(exclude_unset=True, exclude_none=True),
        )
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    return {"message": "Đã cập nhật nội dung ticket.", "ticket": updated}


@router.delete("/tickets/{ticket_id}")
def delete_ticket(request: Request, ticket_id: int) -> dict[str, str]:
    user = current_user(request)
    if user["role"] != "admin":
        raise HTTPException(status_code=403, detail="Chỉ Admin mới được lưu trữ ticket.")
    visible_ticket(ticket_id, user)
    store.archive_ticket(ticket_id, user["username"])
    return {"message": "Ticket đã được lưu trữ; lịch sử audit vẫn được giữ lại."}


@router.put("/tickets/{ticket_id}/assignment")
def assign_ticket(request: Request, ticket_id: int, payload: AssignmentUpdate) -> dict:
    user = current_user(request)
    require_staff(user)
    visible_ticket(ticket_id, user)
    assignee = store.get_user_credentials(payload.assignee)
    if (
        assignee is None
        or not assignee["is_active"]
        or assignee["role"] not in {"agent", "admin"}
    ):
        raise HTTPException(
            status_code=422, detail="Người được giao phải là tài khoản Agent hoặc Admin."
        )
    try:
        ticket = store.assign_ticket(ticket_id, payload.assignee, user["username"])
    except LookupError as exc:
        raise HTTPException(status_code=404, detail="Không tìm thấy ticket.") from exc
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    return {"message": "Đã giao ticket.", "ticket": ticket}


@router.post("/tickets/{ticket_id}/comments")
def add_ticket_comment(request: Request, ticket_id: int, payload: CommentCreate) -> dict:
    user = current_user(request)
    ticket = visible_ticket(ticket_id, user)
    if ticket["status"] == "closed":
        raise HTTPException(status_code=409, detail="Ticket đã đóng, không thể thêm trao đổi.")
    ticket = store.add_comment(ticket_id, user["username"], payload.comment.strip())
    return {"message": "Đã thêm trao đổi.", "ticket": ticket}


@router.post("/tickets/{ticket_id}/attachments", status_code=status.HTTP_201_CREATED)
def upload_ticket_attachment(
    request: Request,
    ticket_id: int,
    file: UploadFile = File(...),
) -> dict:
    user = current_user(request)
    ticket = visible_ticket(ticket_id, user)
    if ticket["status"] == "closed":
        raise HTTPException(status_code=409, detail="Ticket đã đóng, không thể thêm tệp.")
    filename = Path(file.filename or "").name.replace("\r", "").replace("\n", "").strip()
    if not filename or filename in {".", ".."}:
        raise HTTPException(status_code=422, detail="Tên tệp không hợp lệ.")
    allowed_types = {
        ".png": "image/png",
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".txt": "text/plain",
        ".log": "text/plain",
    }
    extension = Path(filename).suffix.lower()
    if extension not in allowed_types:
        raise HTTPException(status_code=415, detail="Chỉ hỗ trợ ảnh PNG/JPG và tệp TXT/LOG.")
    content = file.file.read(10_485_761)
    if len(content) > 10_485_760:
        raise HTTPException(status_code=413, detail="Tệp vượt quá giới hạn 10 MiB.")
    if not content:
        raise HTTPException(status_code=422, detail="Tệp đính kèm đang trống.")
    if extension == ".png" and not content.startswith(b"\x89PNG\r\n\x1a\n"):
        raise HTTPException(status_code=422, detail="Nội dung tệp không khớp định dạng PNG.")
    if extension in {".jpg", ".jpeg"} and not content.startswith(b"\xff\xd8\xff"):
        raise HTTPException(status_code=422, detail="Nội dung tệp không khớp định dạng JPEG.")
    if extension in {".txt", ".log"}:
        try:
            content.decode("utf-8-sig")
        except UnicodeDecodeError as exc:
            raise HTTPException(status_code=422, detail="Tệp TXT/LOG phải là UTF-8.") from exc
    attachment_id = uuid.uuid4().hex
    stored_name = f"{attachment_id}{extension}"
    attachments_dir = _get_attachments_dir()
    attachments_dir.mkdir(parents=True, exist_ok=True)
    target = attachments_dir / stored_name
    try:
        target.write_bytes(content)
        attachment = store.add_attachment(
            ticket_id,
            attachment_id,
            filename[:255],
            stored_name,
            allowed_types[extension],
            len(content),
            user["username"],
        )
    except (OSError, *store.DatabaseError) as exc:
        target.unlink(missing_ok=True)
        raise HTTPException(status_code=500, detail="Không thể lưu tệp đính kèm.") from exc
    return attachment


@router.get("/tickets/{ticket_id}/attachments/{attachment_id}")
def download_ticket_attachment(
    request: Request,
    ticket_id: int,
    attachment_id: str,
) -> FileResponse:
    user = current_user(request)
    visible_ticket(ticket_id, user)
    attachment = store.get_attachment(attachment_id)
    if attachment is None or attachment["ticket_id"] != ticket_id:
        raise HTTPException(status_code=404, detail="Không tìm thấy tệp đính kèm.")
    attachments_dir = _get_attachments_dir()
    target = (attachments_dir / attachment["stored_name"]).resolve()
    if target.parent != attachments_dir.resolve() or not target.is_file():
        raise HTTPException(status_code=404, detail="Tệp đính kèm không còn khả dụng.")
    return FileResponse(
        target,
        media_type=attachment["content_type"],
        filename=attachment["original_name"],
        content_disposition_type="attachment",
        headers={"X-Content-Type-Options": "nosniff"},
    )


@router.post("/tickets/{ticket_id}/rate")
def rate_resolved_ticket(
    request: Request,
    ticket_id: int,
    payload: TicketRating,
) -> dict:
    user = current_user(request)
    ticket = visible_ticket(ticket_id, user)
    if ticket["requester"] != user["username"]:
        raise HTTPException(status_code=403, detail="Chỉ người tạo ticket mới được đánh giá.")
    try:
        rated = store.rate_ticket(ticket_id, payload.rating, payload.comment, user["username"])
    except ValueError as exc:
        msg = (
            "Yêu cầu này đã được đánh giá trước đó."
            if "already been rated" in str(exc)
            else "Chỉ đánh giá được ticket đã giải quyết."
        )
        raise HTTPException(status_code=409, detail=msg) from exc
    return {"message": "Cảm ơn bạn đã đánh giá.", "ticket": rated}


@router.get("/tickets/{ticket_id}/audit")
def ticket_audit(request: Request, ticket_id: int) -> list[dict]:
    user = current_user(request)
    visible_ticket(ticket_id, user)
    return store.get_ticket_audit(ticket_id)
