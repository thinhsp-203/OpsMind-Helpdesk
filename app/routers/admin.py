from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, BackgroundTasks, HTTPException, Request, status

from app import config, email_sender, store
from app.dependencies import current_user
from app.notifications import (
    get_notification_channels_status,
    send_test_notification,
)
from app.schemas import (
    AdminResetPasswordRequest,
    NotificationTestRequest,
    UserCreate,
    UserUpdate,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/admin", tags=["admin"])


@router.get("/users")
async def get_users(request: Request) -> list[dict[str, object]]:
    user = await current_user(request)
    if user["role"] != "admin":
        raise HTTPException(status_code=403, detail="Chỉ Admin mới được quản lý tài khoản.")
    return store.list_users()


@router.post("/users", status_code=status.HTTP_201_CREATED)
async def add_user(
    request: Request,
    payload: UserCreate,
    background_tasks: BackgroundTasks,
) -> dict[str, str]:
    user = await current_user(request)
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
        )
        if payload.email.strip():
            base_url = config.PUBLIC_BASE_URL or str(request.base_url).rstrip("/")
            background_tasks.add_task(
                email_sender.send_account_created_email,
                to_email=payload.email.strip(),
                username=payload.username,
                temp_password=payload.password,
                base_url=base_url,
                force_change=True,
            )
        return created
    except ValueError as exc:
        raise HTTPException(status_code=409, detail="Tên đăng nhập đã tồn tại.") from exc


@router.patch("/users/{username}")
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


@router.post("/users/{username}/reset-password")
async def admin_reset_user_password(
    request: Request,
    username: str,
    payload: AdminResetPasswordRequest,
) -> dict[str, Any]:
    actor = await current_user(request)
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
async def admin_create_user_reset_token(request: Request, username: str) -> dict[str, Any]:
    """Cấp mã xác thực và liên kết khôi phục mật khẩu dùng một lần (Dành cho IT Support hỗ trợ trực tiếp)."""
    actor = await current_user(request)
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
async def get_notifications_status(request: Request) -> dict:
    actor = await current_user(request)
    if actor["role"] != "admin":
        raise HTTPException(status_code=403, detail="Chỉ Admin mới được xem cấu hình thông báo.")
    return get_notification_channels_status()


@router.post("/notifications/test")
async def test_notification_channel(
    request: Request, payload: NotificationTestRequest
) -> dict:
    actor = await current_user(request)
    if actor["role"] != "admin":
        raise HTTPException(status_code=403, detail="Chỉ Admin mới được gửi thông báo thử nghiệm.")
    if payload.channel == "email":
        target = (payload.target_email or "").strip() or config.EMAIL_FROM
        ok, msg = email_sender.send_test_email(target)
        if not ok:
            raise HTTPException(status_code=400, detail=msg)
        return {"success": True, "channel": "email", "message": msg}

    ok = send_test_notification(payload.channel, target_email=payload.target_email or "")
    if not ok:
        raise HTTPException(
            status_code=400,
            detail=f"Không thể gửi thông báo tới kênh {payload.channel}. Vui lòng kiểm tra lại cấu hình và biến môi trường.",
        )
    return {
        "success": True,
        "channel": payload.channel,
        "message": f"Đã gửi thông báo thử nghiệm thành công tới {payload.channel}.",
    }
