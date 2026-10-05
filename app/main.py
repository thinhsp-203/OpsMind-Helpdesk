from __future__ import annotations

import csv
import io
import re
import uuid
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Literal

import jwt
from fastapi import FastAPI, File, Form, HTTPException, Query, Request, UploadFile, status
from fastapi.responses import FileResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field, field_validator, model_validator

from app.config import (
    ALGORITHM,
    DEMO_MODE,
    SECRET_KEY,
    STORAGE_PATH,
    TOKEN_EXPIRE_MINUTES,
)
from app import store
from app.rag import (
    KNOWLEDGE_DIR,
    build_retrieval_index,
    generate_answer,
    load_knowledge_base,
    save_knowledge_document,
)

APP_DIR = Path(__file__).resolve().parent
STATIC_DIR = APP_DIR / "static"
ATTACHMENTS_DIR = Path(STORAGE_PATH).resolve() / "attachments"
Role = Literal["user", "agent", "admin"]
TicketStatus = Literal[
    "new", "in_progress", "pending_waiting_user", "resolved", "closed", "escalated"
]
Priority = Literal["low", "medium", "high", "urgent"]

app = FastAPI(
    title="Helpdesk RAG",
    description="Cổng tự phục vụ CNTT và bảng điều phối ticket có trợ lý tri thức dẫn nguồn.",
    version="1.0.0",
)
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")


class LoginRequest(BaseModel):
    username: str = Field(min_length=1, max_length=50)
    password: str = Field(min_length=1, max_length=200)

    @field_validator("username", mode="before")
    @classmethod
    def normalize_username(cls, value: object) -> object:
        return value.strip() if isinstance(value, str) else value


class UserCreate(BaseModel):
    username: str = Field(min_length=3, max_length=50, pattern=r"^[a-zA-Z0-9._-]+$")
    password: str = Field(min_length=12, max_length=200)
    role: Role
    full_name: str = Field(default="", max_length=120)
    email: str = Field(default="", max_length=254)
    department: str = Field(default="", max_length=120)
    phone: str = Field(default="", max_length=40)

    @field_validator("username", mode="before")
    @classmethod
    def normalize_username(cls, value: object) -> object:
        return value.strip().lower() if isinstance(value, str) else value

    @field_validator("email")
    @classmethod
    def validate_email(cls, value: str) -> str:
        return _validated_email(value) or ""


class UserUpdate(BaseModel):
    role: Role | None = None
    full_name: str | None = Field(default=None, max_length=120)
    email: str | None = Field(default=None, max_length=254)
    department: str | None = Field(default=None, max_length=120)
    phone: str | None = Field(default=None, max_length=40)
    is_active: bool | None = None

    @field_validator("email")
    @classmethod
    def validate_email(cls, value: str | None) -> str | None:
        return _validated_email(value)

    @model_validator(mode="after")
    def require_update_field(self) -> "UserUpdate":
        if not any(
            getattr(self, field_name) is not None for field_name in type(self).model_fields
        ):
            raise ValueError("Cần cung cấp ít nhất một trường để cập nhật.")
        return self


class TicketCreate(BaseModel):
    title: str = Field(min_length=5, max_length=160)
    description: str = Field(min_length=10, max_length=5000)
    category: str = Field(default="general", min_length=2, max_length=50)
    priority: Priority = "medium"

    @field_validator("title", "description", "category", mode="before")
    @classmethod
    def trim_nonempty_fields(cls, value: object) -> object:
        if not isinstance(value, str):
            return value
        normalized = value.strip()
        if not normalized:
            raise ValueError("Giá trị không được để trống.")
        return normalized

    @field_validator("category")
    @classmethod
    def normalize_category(cls, value: str) -> str:
        return value.lower()


class StatusUpdate(BaseModel):
    status: TicketStatus


class TicketUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=5, max_length=160)
    description: str | None = Field(default=None, min_length=10, max_length=5000)
    category: str | None = Field(default=None, min_length=2, max_length=50)
    priority: Priority | None = None

    @field_validator("title", "description", "category", mode="before")
    @classmethod
    def trim_nonempty_fields(cls, value: object) -> object:
        if value is None or not isinstance(value, str):
            return value
        normalized = value.strip()
        if not normalized:
            raise ValueError("Giá trị không được để trống.")
        return normalized

    @field_validator("category")
    @classmethod
    def normalize_category(cls, value: str | None) -> str | None:
        return value.lower() if value else value

    @model_validator(mode="after")
    def require_update_field(self) -> "TicketUpdate":
        if not any(
            getattr(self, field_name) is not None for field_name in type(self).model_fields
        ):
            raise ValueError("Cần cung cấp ít nhất một trường để cập nhật.")
        return self


class AssignmentUpdate(BaseModel):
    assignee: str = Field(min_length=1, max_length=50)


class CommentCreate(BaseModel):
    comment: str = Field(min_length=1, max_length=3000)

    @field_validator("comment", mode="before")
    @classmethod
    def trim_comment(cls, value: object) -> object:
        return value.strip() if isinstance(value, str) else value


class RAGQuestion(BaseModel):
    question: str = Field(min_length=3, max_length=2000)
    session_id: str | None = Field(default=None, min_length=1, max_length=64)

    @field_validator("question", mode="before")
    @classmethod
    def trim_question(cls, value: object) -> object:
        return value.strip() if isinstance(value, str) else value


class TicketRating(BaseModel):
    rating: int = Field(ge=1, le=5)
    comment: str | None = Field(default=None, max_length=2000)

    @field_validator("comment", mode="before")
    @classmethod
    def trim_optional_comment(cls, value: object) -> object:
        if isinstance(value, str):
            return value.strip() or None
        return value


class RAGFeedback(BaseModel):
    message_id: int = Field(gt=0)
    feedback: Literal["up", "down"]


async def current_user(request: Request) -> dict[str, str]:
    auth_header = request.headers.get("Authorization", "")
    scheme, _, token = auth_header.partition(" ")
    if scheme.lower() != "bearer" or not token:
        raise HTTPException(status_code=401, detail="Vui lòng đăng nhập để tiếp tục.")
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    except jwt.PyJWTError as exc:
        raise HTTPException(status_code=401, detail="Phiên đăng nhập không hợp lệ hoặc đã hết hạn.") from exc

    username = payload.get("sub")
    user = store.get_user_credentials(username) if isinstance(username, str) else None
    if user is None or not user["is_active"] or payload.get("role") != user["role"]:
        raise HTTPException(status_code=401, detail="Tài khoản không còn hợp lệ.")
    return {"username": username, "role": user["role"]}


def require_staff(user: dict[str, str]) -> None:
    if user["role"] not in {"agent", "admin"}:
        raise HTTPException(status_code=403, detail="Chỉ nhân viên IT mới được thực hiện thao tác này.")


def _validated_email(value: str | None) -> str | None:
    if value is None or value == "":
        return value
    cleaned = value.strip()
    if not re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", cleaned):
        raise ValueError("Địa chỉ email không hợp lệ.")
    return cleaned


def visible_ticket(ticket_id: int, user: dict[str, str]) -> dict:
    ticket = store.get_ticket(ticket_id)
    if ticket is None:
        raise HTTPException(status_code=404, detail="Không tìm thấy ticket.")
    if user["role"] == "user" and ticket["requester"] != user["username"]:
        raise HTTPException(status_code=404, detail="Không tìm thấy ticket.")
    return ticket


@app.get("/", include_in_schema=False)
async def serve_index() -> FileResponse:
    return FileResponse(STATIC_DIR / "index.html")


@app.get("/config", tags=["system"])
async def public_config() -> dict[str, bool]:
    return {"demo_mode": DEMO_MODE}


@app.get("/health", tags=["system"])
async def health() -> dict[str, str]:
    try:
        store.check_database()
    except store.DatabaseError as exc:
        raise HTTPException(status_code=503, detail="Cơ sở dữ liệu hiện không sẵn sàng.") from exc
    return {"status": "ok", "service": "helpdesk-rag"}


@app.post("/auth/login", tags=["auth"])
async def login(payload: LoginRequest) -> dict[str, str]:
    user = store.get_user_credentials(payload.username)
    if (
        user is None
        or not user["is_active"]
        or not store.verify_password(payload.password, user["password_hash"])
    ):
        raise HTTPException(status_code=401, detail="Tên đăng nhập hoặc mật khẩu không đúng.")
    issued_at = datetime.now(timezone.utc)
    token = jwt.encode(
        {
            "sub": payload.username,
            "role": user["role"],
            "iat": issued_at,
            "exp": issued_at + timedelta(minutes=TOKEN_EXPIRE_MINUTES),
        },
        SECRET_KEY,
        algorithm=ALGORITHM,
    )
    return {"token": token, "username": payload.username, "role": user["role"]}


@app.get("/auth/me", tags=["auth"])
async def who_am_i(request: Request) -> dict[str, str]:
    user = await current_user(request)
    return user


@app.get("/admin/users", tags=["admin"])
async def get_users(request: Request) -> list[dict[str, object]]:
    user = await current_user(request)
    if user["role"] != "admin":
        raise HTTPException(status_code=403, detail="Chỉ Admin mới được quản lý tài khoản.")
    return store.list_users()


@app.get("/staff", tags=["tickets"])
async def get_staff_directory(request: Request) -> list[dict[str, str]]:
    user = await current_user(request)
    require_staff(user)
    return store.list_staff()


@app.post("/admin/users", tags=["admin"], status_code=status.HTTP_201_CREATED)
async def add_user(request: Request, payload: UserCreate) -> dict[str, str]:
    user = await current_user(request)
    if user["role"] != "admin":
        raise HTTPException(status_code=403, detail="Chỉ Admin mới được tạo tài khoản.")
    try:
        return store.create_user(
            payload.username,
            payload.password,
            payload.role,
            payload.full_name.strip(),
            payload.email.strip(),
            payload.department.strip(),
            payload.phone.strip(),
        )
    except ValueError as exc:
        raise HTTPException(status_code=409, detail="Tên đăng nhập đã tồn tại.") from exc


@app.patch("/admin/users/{username}", tags=["admin"])
async def update_admin_user(
    request: Request,
    username: str,
    payload: UserUpdate,
) -> dict[str, object]:
    actor = await current_user(request)
    if actor["role"] != "admin":
        raise HTTPException(status_code=403, detail="Chỉ Admin mới được quản lý tài khoản.")
    existing = store.get_user_credentials(username)
    if existing is None:
        raise HTTPException(status_code=404, detail="Không tìm thấy tài khoản.")
    updates = payload.model_dump(exclude_unset=True, exclude_none=True)
    leaving_active_admin = (
        existing["role"] == "admin"
        and existing["is_active"]
        and (updates.get("role", "admin") != "admin" or updates.get("is_active") is False)
    )
    if leaving_active_admin and store.count_active_admins() <= 1:
        raise HTTPException(status_code=409, detail="Không thể vô hiệu hóa hoặc hạ quyền Admin cuối cùng.")
    if actor["username"] == username and (
        updates.get("role", actor["role"]) != "admin" or updates.get("is_active") is False
    ):
        raise HTTPException(status_code=409, detail="Không thể tự hạ quyền hoặc khóa tài khoản đang đăng nhập.")
    try:
        updated = store.update_user(username, updates)
    except ValueError as exc:
        raise HTTPException(status_code=409, detail="Không thể khóa hoặc hạ quyền Admin cuối cùng.") from exc
    if updated is None:
        raise HTTPException(status_code=404, detail="Không tìm thấy tài khoản.")
    return updated


@app.get("/tickets", tags=["tickets"])
async def get_tickets(
    request: Request,
    status_filter: TicketStatus | None = Query(default=None, alias="status"),
    category: str | None = Query(default=None, max_length=50),
    q: str | None = Query(default=None, max_length=160),
    from_date: date | None = Query(default=None, alias="from"),
    to_date: date | None = Query(default=None, alias="to"),
) -> list[dict]:
    user = await current_user(request)
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


@app.post("/tickets", tags=["tickets"], status_code=status.HTTP_201_CREATED)
async def create_new_ticket(request: Request, payload: TicketCreate) -> dict:
    user = await current_user(request)
    ticket = store.create_ticket(
        title=payload.title.strip(),
        description=payload.description.strip(),
        category=payload.category.strip().lower(),
        priority=payload.priority,
        requester=user["username"],
    )
    return {"message": "Đã tạo ticket.", "ticket": ticket}


@app.get("/tickets/{ticket_id}", tags=["tickets"])
async def get_one_ticket(request: Request, ticket_id: int) -> dict:
    user = await current_user(request)
    return visible_ticket(ticket_id, user)


@app.patch("/tickets/{ticket_id}", tags=["tickets"])
async def patch_ticket(request: Request, ticket_id: int, payload: StatusUpdate) -> dict:
    user = await current_user(request)
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
    return {"message": "Đã cập nhật trạng thái.", "ticket": ticket}


@app.put("/tickets/{ticket_id}", tags=["tickets"])
async def update_ticket(request: Request, ticket_id: int, payload: TicketUpdate) -> dict:
    user = await current_user(request)
    ticket = visible_ticket(ticket_id, user)
    if user["role"] == "user":
        if ticket["status"] != "new":
            raise HTTPException(status_code=409, detail="Chỉ có thể sửa ticket khi còn ở trạng thái Mới.")
    else:
        require_staff(user)
    try:
        updated = store.update_ticket_fields(
            ticket_id,
            user["username"],
            payload.model_dump(exclude_unset=True, exclude_none=True),
        )
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    return {"message": "Đã cập nhật nội dung ticket.", "ticket": updated}


@app.delete("/tickets/{ticket_id}", tags=["tickets"])
async def delete_ticket(request: Request, ticket_id: int) -> dict[str, str]:
    user = await current_user(request)
    if user["role"] != "admin":
        raise HTTPException(status_code=403, detail="Chỉ Admin mới được lưu trữ ticket.")
    visible_ticket(ticket_id, user)
    store.archive_ticket(ticket_id, user["username"])
    return {"message": "Ticket đã được lưu trữ; lịch sử audit vẫn được giữ lại."}


@app.put("/tickets/{ticket_id}/assignment", tags=["tickets"])
async def assign_ticket(request: Request, ticket_id: int, payload: AssignmentUpdate) -> dict:
    user = await current_user(request)
    require_staff(user)
    visible_ticket(ticket_id, user)
    assignee = store.get_user_credentials(payload.assignee)
    if (
        assignee is None
        or not assignee["is_active"]
        or assignee["role"] not in {"agent", "admin"}
    ):
        raise HTTPException(status_code=422, detail="Người được giao phải là tài khoản Agent hoặc Admin.")
    ticket = store.assign_ticket(ticket_id, payload.assignee, user["username"])
    return {"message": "Đã giao ticket.", "ticket": ticket}


@app.post("/tickets/{ticket_id}/comments", tags=["tickets"])
async def add_ticket_comment(request: Request, ticket_id: int, payload: CommentCreate) -> dict:
    user = await current_user(request)
    ticket = visible_ticket(ticket_id, user)
    if ticket["status"] == "closed":
        raise HTTPException(status_code=409, detail="Ticket đã đóng, không thể thêm trao đổi.")
    ticket = store.add_comment(ticket_id, user["username"], payload.comment.strip())
    return {"message": "Đã thêm trao đổi.", "ticket": ticket}


@app.post("/tickets/{ticket_id}/attachments", tags=["tickets"], status_code=status.HTTP_201_CREATED)
async def upload_ticket_attachment(
    request: Request,
    ticket_id: int,
    file: UploadFile = File(...),
) -> dict:
    user = await current_user(request)
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
    content = await file.read(10_485_761)
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
    ATTACHMENTS_DIR.mkdir(parents=True, exist_ok=True)
    target = ATTACHMENTS_DIR / stored_name
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


@app.get("/tickets/{ticket_id}/attachments/{attachment_id}", tags=["tickets"])
async def download_ticket_attachment(
    request: Request,
    ticket_id: int,
    attachment_id: str,
) -> FileResponse:
    user = await current_user(request)
    visible_ticket(ticket_id, user)
    attachment = store.get_attachment(attachment_id)
    if attachment is None or attachment["ticket_id"] != ticket_id:
        raise HTTPException(status_code=404, detail="Không tìm thấy tệp đính kèm.")
    target = (ATTACHMENTS_DIR / attachment["stored_name"]).resolve()
    if target.parent != ATTACHMENTS_DIR.resolve() or not target.is_file():
        raise HTTPException(status_code=404, detail="Tệp đính kèm không còn khả dụng.")
    return FileResponse(
        target,
        media_type=attachment["content_type"],
        filename=attachment["original_name"],
        content_disposition_type="attachment",
        headers={"X-Content-Type-Options": "nosniff"},
    )


@app.post("/tickets/{ticket_id}/rate", tags=["tickets"])
async def rate_resolved_ticket(
    request: Request,
    ticket_id: int,
    payload: TicketRating,
) -> dict:
    user = await current_user(request)
    ticket = visible_ticket(ticket_id, user)
    if ticket["requester"] != user["username"]:
        raise HTTPException(status_code=403, detail="Chỉ người tạo ticket mới được đánh giá.")
    try:
        rated = store.rate_ticket(ticket_id, payload.rating, payload.comment, user["username"])
    except ValueError as exc:
        raise HTTPException(status_code=409, detail="Chỉ đánh giá được ticket đã giải quyết.") from exc
    return {"message": "Cảm ơn bạn đã đánh giá.", "ticket": rated}


@app.get("/tickets/{ticket_id}/audit", tags=["tickets"])
async def ticket_audit(request: Request, ticket_id: int) -> list[dict]:
    user = await current_user(request)
    visible_ticket(ticket_id, user)
    return store.get_ticket_audit(ticket_id)


@app.get("/analytics", tags=["analytics"])
async def analytics(request: Request) -> dict:
    user = await current_user(request)
    require_staff(user)
    return store.get_analytics()


@app.get("/analytics/agents/me", tags=["analytics"])
async def agent_analytics(request: Request) -> dict:
    user = await current_user(request)
    require_staff(user)
    return store.get_agent_analytics(user["username"])


@app.get("/knowledge", tags=["rag"])
async def knowledge_documents(request: Request) -> list[dict[str, str]]:
    await current_user(request)
    return [
        {"title": document["title"], "source": document["source"]}
        for document in load_knowledge_base()
    ]


@app.delete("/knowledge/{source}", tags=["rag"])
async def delete_knowledge_document(request: Request, source: str) -> dict[str, str]:
    user = await current_user(request)
    if user["role"] != "admin":
        raise HTTPException(status_code=403, detail="Chỉ Admin mới được quản lý tài liệu tri thức.")
    if not re.fullmatch(r"[a-z0-9][a-z0-9-]{0,63}\.md", source):
        raise HTTPException(status_code=422, detail="Tên nguồn tài liệu không hợp lệ.")
    target = (KNOWLEDGE_DIR / source).resolve()
    if target.parent != KNOWLEDGE_DIR.resolve() or not target.is_file():
        raise HTTPException(status_code=404, detail="Không tìm thấy tài liệu.")
    try:
        target.unlink()
    except OSError as exc:
        raise HTTPException(status_code=500, detail="Không thể xóa tài liệu tri thức.") from exc
    load_knowledge_base.cache_clear()
    build_retrieval_index.cache_clear()
    return {"message": "Đã xóa tài liệu khỏi Knowledge Base."}


@app.post("/knowledge/{source}/reindex", tags=["rag"])
async def reindex_knowledge_document(request: Request, source: str) -> dict[str, str]:
    user = await current_user(request)
    if user["role"] != "admin":
        raise HTTPException(status_code=403, detail="Chỉ Admin mới được quản lý tài liệu tri thức.")
    if not re.fullmatch(r"[a-z0-9][a-z0-9-]{0,63}\.md", source):
        raise HTTPException(status_code=422, detail="Tên nguồn tài liệu không hợp lệ.")
    if not (KNOWLEDGE_DIR / source).is_file():
        raise HTTPException(status_code=404, detail="Không tìm thấy tài liệu.")
    load_knowledge_base.cache_clear()
    build_retrieval_index.cache_clear()
    build_retrieval_index()
    return {"message": "Đã làm mới chỉ mục BM25 từ Knowledge Base hiện tại."}


@app.get("/analytics/export", tags=["analytics"])
async def export_analytics(request: Request) -> StreamingResponse:
    user = await current_user(request)
    if user["role"] != "admin":
        raise HTTPException(status_code=403, detail="Chỉ Admin mới được xuất báo cáo.")
    tickets = store.list_tickets("", "admin")
    stream = io.StringIO()
    writer = csv.writer(stream)
    writer.writerow(
        ["ticket_id", "title", "requester", "assignee", "category", "priority", "status", "created_at", "sla_deadline", "rating"]
    )
    def safe_csv_value(value: object) -> object:
        if not isinstance(value, str):
            return value
        if value.lstrip().startswith(("=", "+", "-", "@")):
            return f"'{value}"
        return value

    for ticket in tickets:
        writer.writerow(
            [safe_csv_value(value) for value in [
                ticket["id"],
                ticket["title"],
                ticket["requester"],
                ticket["assignee"] or "",
                ticket["category"],
                ticket["priority"],
                ticket["status"],
                ticket["created_at"],
                ticket["sla_deadline"],
                ticket["rating"] or "",
            ]]
        )
    content = "\ufeff" + stream.getvalue()
    return StreamingResponse(
        iter([content]),
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": 'attachment; filename="helpdesk-report.csv"'},
    )


@app.post("/knowledge", tags=["rag"], status_code=status.HTTP_201_CREATED)
async def upload_knowledge_document(
    request: Request,
    title: str = Form(min_length=3, max_length=120),
    document: UploadFile = File(...),
) -> dict[str, str]:
    user = await current_user(request)
    if user["role"] != "admin":
        raise HTTPException(status_code=403, detail="Chỉ Admin mới được nạp tài liệu tri thức.")
    original_name = Path(document.filename or "").name
    if not original_name.lower().endswith(".md"):
        raise HTTPException(status_code=415, detail="Chỉ hỗ trợ tài liệu Markdown (.md).")
    if document.size is not None and document.size > 262_144:
        raise HTTPException(status_code=413, detail="Tài liệu vượt quá giới hạn 256 KiB.")
    content = await document.read(262_145)
    if len(content) > 262_144:
        raise HTTPException(status_code=413, detail="Tài liệu vượt quá giới hạn 256 KiB.")
    try:
        text = content.decode("utf-8-sig").strip()
    except UnicodeDecodeError as exc:
        raise HTTPException(status_code=422, detail="Tài liệu phải được mã hóa UTF-8.") from exc
    if not text or not re.search(r"(?m)^#\s+\S+", text):
        raise HTTPException(status_code=422, detail="Tài liệu cần có tiêu đề Markdown cấp 1.")
    cleaned_title = title.strip()
    if len(cleaned_title) < 3:
        raise HTTPException(status_code=422, detail="Tiêu đề cần có ít nhất 3 ký tự.")
    try:
        saved = save_knowledge_document(
            KNOWLEDGE_DIR,
            original_name,
            cleaned_title,
            text,
        )
    except FileExistsError as exc:
        raise HTTPException(status_code=409, detail="Tên tài liệu này đã tồn tại.") from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail="Tên tệp hoặc tiêu đề tài liệu không hợp lệ.") from exc
    except OSError as exc:
        raise HTTPException(status_code=500, detail="Không thể lưu tài liệu tri thức.") from exc
    return {"message": "Đã nạp tài liệu tri thức.", **saved}


@app.post("/rag/ask", tags=["rag"])
async def ask_rag(request: Request, payload: RAGQuestion) -> dict:
    user = await current_user(request)
    result = generate_answer(payload.question.strip())
    try:
        result["session_id"] = store.save_chat_exchange(
            user["username"],
            payload.session_id,
            payload.question.strip(),
            result["answer"],
            result["sources"],
        )
    except LookupError as exc:
        raise HTTPException(status_code=404, detail="Không tìm thấy phiên hội thoại.") from exc
    saved_session = store.get_chat_session(user["username"], result["session_id"])
    result["assistant_message_id"] = saved_session["messages"][-1]["id"]
    return result


@app.get("/rag/sessions", tags=["rag"])
async def get_rag_sessions(request: Request) -> list[dict]:
    user = await current_user(request)
    return store.list_chat_sessions(user["username"])


@app.get("/rag/sessions/{session_id}", tags=["rag"])
async def get_rag_session(request: Request, session_id: str) -> dict:
    user = await current_user(request)
    session = store.get_chat_session(user["username"], session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Không tìm thấy phiên hội thoại.")
    return session


@app.post("/rag/feedback", tags=["rag"])
async def provide_rag_feedback(request: Request, payload: RAGFeedback) -> dict[str, str]:
    user = await current_user(request)
    if not store.set_chat_feedback(user["username"], payload.message_id, payload.feedback):
        raise HTTPException(status_code=404, detail="Không tìm thấy câu trả lời để đánh giá.")
    return {"message": "Đã ghi nhận phản hồi."}
