from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, BackgroundTasks, HTTPException, Request, status

from app import config, email_sender, store
from app.dependencies import current_user, require_admin
from app.notifications import (
    get_notification_channels_status,
    send_test_notification_result,
)
from app.schemas import (
    AdminResetPasswordRequest,
    NotificationTestRequest,
    UserCreate,
    UserUpdate,
    UserDeletion,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/admin", tags=["admin"])


@router.get("/users")
def get_users(request: Request) -> list[dict[str, object]]:
    user = current_user(request)
    if user["role"] != "admin":
        raise HTTPException(status_code=403, detail="Chỉ Admin mới được quản lý tài khoản.")
    return store.list_users()


@router.post("/users", status_code=status.HTTP_201_CREATED)
def add_user(
    request: Request,
    payload: UserCreate,
    background_tasks: BackgroundTasks,
) -> dict[str, str]:
    user = current_user(request)
    if user["role"] != "admin":
        raise HTTPException(status_code=403, detail="Chỉ Admin mới được tạo tài khoản.")
    try:
        created = store.create_user(
            payload.username,
            payload.password,
            payload.role,
            payload.full_name.strip(),
            payload.email.strip(),
            payload.department.strip(),
            payload.phone.strip(),
            force_password_change=1,
            invitation_base_url=(config.PUBLIC_BASE_URL or str(request.base_url).rstrip('/')) if payload.email.strip() else None,
        )
        if payload.email.strip():
            from app.email_outbox import wake_email_worker
            background_tasks.add_task(wake_email_worker)
        return created
    except email_sender.EmailConfigurationError as exc:
        raise HTTPException(status_code=503, detail="Email chưa được cấu hình hợp lệ; chưa tạo tài khoản.") from exc
    except store.DatabaseError as exc:
        raise HTTPException(status_code=503, detail="Chưa lưu được tài khoản và thư mời.") from exc
    except ValueError as exc:
        raise HTTPException(status_code=409, detail="Tên đăng nhập đã tồn tại.") from exc


@router.patch("/users/{username}")
def update_admin_user(
    request: Request,
    username: str,
    payload: UserUpdate,
) -> dict[str, object]:
    actor = current_user(request)
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
        raise HTTPException(
            status_code=409, detail="Không thể vô hiệu hóa hoặc hạ quyền Admin cuối cùng."
        )
    if actor["username"] == username and (
        updates.get("role", actor["role"]) != "admin" or updates.get("is_active") is False
    ):
        raise HTTPException(
            status_code=409, detail="Không thể tự hạ quyền hoặc khóa tài khoản đang đăng nhập."
        )
    try:
        updated = store.update_user(username, updates)
    except ValueError as exc:
        raise HTTPException(
            status_code=409, detail="Không thể khóa hoặc hạ quyền Admin cuối cùng."
        ) from exc
    if updated is None:
        raise HTTPException(status_code=404, detail="Không tìm thấy tài khoản.")
    return updated


@router.delete("/users/{username}")
def delete_admin_user(request: Request, username: str, payload: UserDeletion) -> dict[str, str]:
    actor = current_user(request)
    require_admin(actor)
    if payload.confirm_username != username:
        raise HTTPException(status_code=422, detail="Tên xác nhận phải khớp chính xác tài khoản cần xóa.")
    try:
        deleted = store.delete_user(username, actor['username'])
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    if not deleted:
        raise HTTPException(status_code=404, detail="Không tìm thấy tài khoản.")
    return {'message': 'Đã xóa tài khoản và dữ liệu đăng nhập. Lịch sử nghiệp vụ đã ẩn danh.'}


@router.post("/users/{username}/reset-password")
def admin_reset_user_password(
    request: Request,
    username: str,
    payload: AdminResetPasswordRequest,
) -> dict[str, Any]:
    actor = current_user(request)
    if actor["role"] != "admin":
        raise HTTPException(status_code=403, detail="Chỉ Admin mới được quản lý tài khoản.")
    existing = store.get_user_credentials(username)
    if existing is None:
        raise HTTPException(status_code=404, detail="Không tìm thấy tài khoản.")
    if len(payload.new_password) < 12:
        raise HTTPException(status_code=422, detail="Mật khẩu mới phải có ít nhất 12 ký tự.")
    if payload.new_password.lower() == username.lower():
        raise HTTPException(
            status_code=400, detail="Mật khẩu mới không được trùng với tên đăng nhập."
        )
    store.admin_reset_password(
        username,
        payload.new_password,
        force_password_change=1 if payload.force_change else 0,
    )
    return {
        "status": "success",
        "message": f"Đã đặt lại mật khẩu cho tài khoản {username}.",
        "username": username,
        "is_self": actor["username"].lower() == username.lower(),
        "require_relogin": actor["username"].lower() == username.lower(),
    }


@router.post("/users/{username}/create-reset-token")
def admin_create_user_reset_token(request: Request, username: str) -> dict[str, Any]:
    """Cấp mã xác thực và liên kết khôi phục mật khẩu dùng một lần (Dành cho IT Support hỗ trợ trực tiếp)."""
    actor = current_user(request)
    if actor["role"] != "admin":
        raise HTTPException(
            status_code=403, detail="Chỉ Admin mới được cấp mã khôi phục mật khẩu."
        )
    existing = store.get_user_credentials(username)
    if existing is None:
        raise HTTPException(status_code=404, detail="Không tìm thấy tài khoản.")

    token = store.create_password_reset_token(
        username, expires_minutes=config.RESET_TOKEN_EXPIRE_MINUTES
    )
    base_url = config.PUBLIC_BASE_URL or str(request.base_url).rstrip("/")
    reset_link = f"{base_url}/#reset-token={token}"

    return {
        "status": "success",
        "username": username,
        "token": token,
        "reset_link": reset_link,
        "expires_minutes": config.RESET_TOKEN_EXPIRE_MINUTES,
    }


@router.get("/notifications/status")
def get_notifications_status(request: Request) -> dict:
    actor = current_user(request)
    if actor["role"] != "admin":
        raise HTTPException(status_code=403, detail="Chỉ Admin mới được xem cấu hình thông báo.")
    return get_notification_channels_status()


@router.post("/notifications/test")
def test_notification_channel(
    request: Request, payload: NotificationTestRequest
) -> dict:
    actor = current_user(request)
    if actor["role"] != "admin":
        raise HTTPException(status_code=403, detail="Chỉ Admin mới được gửi thông báo thử nghiệm.")
    ok, msg = send_test_notification_result(payload.channel, target_email=payload.target_email or "")
    if not ok:
        raise HTTPException(status_code=400, detail=msg)
    return {"success": True, "channel": payload.channel, "message": msg}


@router.get("/notifications/deliveries")
def notification_deliveries(request: Request, status: str | None = None, limit: int = 50, before_id: str | None = None) -> list[dict]:
    from app.notification_outbox import list_deliveries
    require_admin(current_user(request))
    if status not in {None, 'pending', 'processing', 'accepted', 'failed', 'not_configured', 'config_changed'}:
        raise HTTPException(status_code=422, detail="Invalid delivery status")
    try:
        return list_deliveries(status, limit, before_id)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.post("/notifications/deliveries/{delivery_id}/retry")
def retry_notification_delivery(request: Request, delivery_id: str, background_tasks: BackgroundTasks) -> dict:
    from app.notification_outbox import retry_delivery, wake_notification_worker
    actor = current_user(request)
    require_admin(actor)
    try:
        retry_delivery(delivery_id, actor['username'])
    except LookupError as exc:
        raise HTTPException(status_code=404, detail="Delivery not found") from exc
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    background_tasks.add_task(wake_notification_worker)
    return {"message": "Delivery queued; provider acceptance is not yet confirmed."}


@router.get("/email-deliveries")
def email_deliveries(request: Request, limit: int = 50) -> list[dict]:
    from app.email_outbox import list_deliveries
    require_admin(current_user(request))
    try:
        return list_deliveries(limit)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
