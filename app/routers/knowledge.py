from __future__ import annotations

import logging
import re
from pathlib import Path
from typing import Any

from fastapi import APIRouter, HTTPException, Query, Request, status
from starlette.concurrency import run_in_threadpool

from app import store
from app.dependencies import current_user, require_staff
from app.rag import (
    BASE_KNOWLEDGE_DIR,
    build_retrieval_index,
    load_knowledge_base,
    save_knowledge_document,
)
from app.schemas import (
    KnowledgeDocumentCreate,
    KnowledgeDocumentUpdate,
    KnowledgeReviewRequest,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/knowledge", tags=["rag"])


@router.get("")
def knowledge_documents(
    request: Request,
    status_filter: str | None = Query(default=None, alias="status"),
    category: str | None = Query(default=None),
    search: str | None = Query(default=None),
) -> list[dict[str, Any]]:
    user = current_user(request)
    is_staff = user["role"] in {"agent", "admin"}
    effective_status = status_filter if is_staff else "published"
    docs = store.list_knowledge_documents(
        status=effective_status,
        category=category,
        query=search,
    )
    return [{**doc, "source": doc["slug"]} for doc in docs]


@router.get("/{identifier}")
def get_single_knowledge_document(
    request: Request,
    identifier: str,
) -> dict[str, Any]:
    user = current_user(request)
    doc = store.get_knowledge_document(identifier)
    if not doc:
        raise HTTPException(status_code=404, detail="Không tìm thấy tài liệu.")

    if user["role"] == "user" and doc["status"] != "published":
        raise HTTPException(status_code=404, detail="Không tìm thấy tài liệu.")

    return {**doc, "source": doc["slug"]}


@router.put("/{identifier}")
def edit_knowledge_document(
    request: Request,
    identifier: str,
    payload: KnowledgeDocumentUpdate,
) -> dict[str, Any]:
    user = current_user(request)
    require_staff(user)
    doc = store.get_knowledge_document(identifier)
    if not doc:
        raise HTTPException(status_code=404, detail="Không tìm thấy tài liệu.")

    if user["role"] == "agent":
        if doc["author"] != user["username"] and doc["status"] == "draft":
            raise HTTPException(
                status_code=403, detail="Chỉ tác giả hoặc Admin mới được sửa bản nháp này."
            )
        if payload.status == "archived":
            raise HTTPException(
                status_code=403,
                detail="Chỉ Quản trị viên (Admin) mới có quyền lưu trữ (archive) tài liệu tri thức.",
            )
        if doc["status"] == "published" or payload.status == "published":
            payload.status = "pending_review"

    updates = {k: v for k, v in payload.model_dump().items() if v is not None}
    summary = updates.pop("change_summary", "Cập nhật tài liệu")
    updated = store.update_knowledge_document(
        doc["id"],
        updates,
        actor=user["username"],
        change_summary=summary,
    )
    load_knowledge_base.cache_clear()
    build_retrieval_index.cache_clear()
    return {
        "message": "Đã cập nhật tài liệu tri thức.",
        **(updated or {}),
        "source": updated["slug"] if updated else "",
    }


@router.post("/{identifier}/review")
def review_knowledge_document_endpoint(
    request: Request,
    identifier: str,
    payload: KnowledgeReviewRequest,
) -> dict[str, Any]:
    user = current_user(request)
    if user["role"] != "admin":
        raise HTTPException(status_code=403, detail="Chỉ Admin mới có quyền duyệt tài liệu.")
    doc = store.get_knowledge_document(identifier)
    if not doc:
        raise HTTPException(status_code=404, detail="Không tìm thấy tài liệu.")

    reviewed = store.review_knowledge_document(
        doc["id"],
        action=payload.action,
        reviewer=user["username"],
        feedback=payload.feedback or "",
    )
    load_knowledge_base.cache_clear()
    build_retrieval_index.cache_clear()
    msg = (
        "Đã duyệt và xuất bản tài liệu."
        if payload.action == "approve"
        else "Đã trả về bản nháp."
    )
    return {
        "message": msg,
        **(reviewed or {}),
        "source": reviewed["slug"] if reviewed else "",
    }


@router.get("/{identifier}/versions")
def get_knowledge_versions(
    request: Request,
    identifier: str,
) -> list[dict[str, Any]]:
    user = current_user(request)
    require_staff(user)
    doc = store.get_knowledge_document(identifier)
    if not doc:
        raise HTTPException(status_code=404, detail="Không tìm thấy tài liệu.")
    return store.list_knowledge_versions(doc["id"])


@router.post("/{identifier}/restore/{version_number}")
def restore_knowledge_version_endpoint(
    request: Request,
    identifier: str,
    version_number: int,
) -> dict[str, Any]:
    user = current_user(request)
    if user["role"] != "admin":
        raise HTTPException(status_code=403, detail="Chỉ Admin mới có quyền khôi phục phiên bản.")
    doc = store.get_knowledge_document(identifier)
    if not doc:
        raise HTTPException(status_code=404, detail="Không tìm thấy tài liệu.")
    restored = store.restore_knowledge_version(
        doc["id"],
        version_number=version_number,
        actor=user["username"],
    )
    if not restored:
        raise HTTPException(status_code=404, detail="Không tìm thấy phiên bản cần khôi phục.")
    load_knowledge_base.cache_clear()
    build_retrieval_index.cache_clear()
    return {
        "message": f"Đã khôi phục về phiên bản #{version_number}.",
        **restored,
        "source": restored["slug"],
    }


@router.delete("/{source}")
def delete_knowledge_document(request: Request, source: str) -> dict[str, str]:
    user = current_user(request)
    if user["role"] != "admin":
        raise HTTPException(status_code=403, detail="Chỉ Admin mới được quản lý tài liệu tri thức.")
    if not re.fullmatch(r"[a-z0-9][a-z0-9_-]{0,63}\.md", source):
        raise HTTPException(status_code=422, detail="Tên nguồn tài liệu không hợp lệ.")
    try:
        doc = store.get_knowledge_document(source)
        if not doc:
            raise HTTPException(status_code=404, detail="Không tìm thấy tài liệu.")
        # Reject legacy rows colliding with packaged input BEFORE any DB mutation.
        if doc["is_builtin"] or (BASE_KNOWLEDGE_DIR / source).is_file():
            raise HTTPException(status_code=403, detail="Không thể xóa tài liệu mặc định của hệ thống.")
        if not store.delete_knowledge_document(doc["id"]):
            raise HTTPException(status_code=404, detail="Không tìm thấy tài liệu.")
    except store.DatabaseError as exc:
        raise HTTPException(status_code=503, detail="Kho tri thức tạm thời không khả dụng.") from exc
    # Legacy file copies are offline migration input, never part of this mutation.
    load_knowledge_base.cache_clear()
    build_retrieval_index.cache_clear()
    return {"message": "Đã xóa tài liệu khỏi Knowledge Base."}


@router.post("/{source}/reindex")
def reindex_knowledge_document(request: Request, source: str) -> dict[str, str]:
    user = current_user(request)
    if user["role"] != "admin":
        raise HTTPException(status_code=403, detail="Chỉ Admin mới được quản lý tài liệu tri thức.")
    if not re.fullmatch(r"[a-z0-9][a-z0-9_-]{0,63}\.md", source):
        raise HTTPException(status_code=422, detail="Tên nguồn tài liệu không hợp lệ.")
    doc = store.get_knowledge_document(source)
    if not doc:
        raise HTTPException(status_code=404, detail="Không tìm thấy tài liệu.")
    load_knowledge_base.cache_clear()
    build_retrieval_index.cache_clear()
    build_retrieval_index()
    return {"message": "Đã làm mới chỉ mục BM25 từ Knowledge Base hiện tại."}


@router.post("", status_code=status.HTTP_201_CREATED)
async def upload_knowledge_document(
    request: Request,
) -> dict[str, Any]:
    content_type = request.headers.get("content-type", "")
    if "multipart/form-data" in content_type:
        user = await run_in_threadpool(current_user, request)
        if user["role"] != "admin":
            raise HTTPException(status_code=403, detail="Chỉ Admin mới được nạp tài liệu tri thức.")
        form = await request.form()
        title_val = form.get("title")
        doc_file = form.get("document")
        if not title_val or not isinstance(title_val, str):
            raise HTTPException(status_code=422, detail="Tiêu đề là bắt buộc.")
        cleaned_title = title_val.strip()
        if len(cleaned_title) < 3 or len(cleaned_title) > 120:
            raise HTTPException(status_code=422, detail="Tiêu đề cần có từ 3 đến 120 ký tự.")
        if not doc_file or not hasattr(doc_file, "filename"):
            raise HTTPException(status_code=422, detail="Tài liệu tải lên là bắt buộc.")

        original_name = Path(doc_file.filename or "").name
        if not original_name.lower().endswith(".md"):
            raise HTTPException(status_code=415, detail="Chỉ hỗ trợ tài liệu Markdown (.md).")

        file_size = getattr(doc_file, "size", None)
        if file_size is not None and file_size > 262_144:
            raise HTTPException(status_code=413, detail="Tài liệu vượt quá giới hạn 256 KiB.")
        content = await doc_file.read(262_145)
        if len(content) > 262_144:
            raise HTTPException(status_code=413, detail="Tài liệu vượt quá giới hạn 256 KiB.")
        try:
            text = content.decode("utf-8-sig").strip()
        except UnicodeDecodeError as exc:
            raise HTTPException(status_code=422, detail="Tài liệu phải được mã hóa UTF-8.") from exc
        if not text or not re.search(r"(?m)^#\s+\S+", text):
            raise HTTPException(status_code=422, detail="Tài liệu cần có tiêu đề Markdown cấp 1.")
        try:
            saved = await run_in_threadpool(
                save_knowledge_document,
                original_name,
                cleaned_title,
                text,
                author=user["username"],
            )
        except FileExistsError as exc:
            raise HTTPException(status_code=409, detail="Tên tài liệu này đã tồn tại.") from exc
        except ValueError as exc:
            raise HTTPException(
                status_code=422, detail="Tên tệp hoặc tiêu đề tài liệu không hợp lệ."
            ) from exc
        except store.DatabaseError as exc:
            raise HTTPException(status_code=503, detail="Kho tri thức tạm thời không khả dụng.") from exc
        except OSError as exc:
            raise HTTPException(status_code=500, detail="Không thể lưu tài liệu tri thức.") from exc
        return {"message": "Đã nạp tài liệu tri thức.", **saved}

    user = await run_in_threadpool(current_user, request)
    require_staff(user)
    try:
        data = await request.json()
    except Exception as exc:
        raise HTTPException(status_code=422, detail="Dữ liệu JSON không hợp lệ.") from exc

    try:
        payload = KnowledgeDocumentCreate.model_validate(data)
    except Exception as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    if payload.status == "published" and user["role"] != "admin":
        raise HTTPException(
            status_code=403, detail="Chỉ Admin mới có quyền xuất bản tài liệu trực tiếp."
        )

    target_status = payload.status
    if user["role"] == "agent" and target_status not in ("draft", "pending_review"):
        target_status = "draft"

    doc = await run_in_threadpool(
        store.create_knowledge_document,
        title=payload.title,
        category=payload.category,
        content=payload.content,
        tags=payload.tags,
        status=target_status,
        author=user["username"],
    )

    if doc["status"] == "published":
        load_knowledge_base.cache_clear()
        build_retrieval_index.cache_clear()

    return {"message": "Đã tạo tài liệu tri thức.", **doc, "source": doc["slug"]}
