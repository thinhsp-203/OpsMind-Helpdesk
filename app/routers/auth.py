from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from typing import Any

import jwt
from fastapi import APIRouter, BackgroundTasks, HTTPException, Request, status

from app import config, email_sender, store
from app.config import ALGORITHM, SECRET_KEY, TOKEN_EXPIRE_MINUTES
from app.dependencies import (
    DUMMY_PASSWORD_HASH,
    _check_change_password_rate_limit,
    _check_forgot_password_rate_limit,
    _check_login_rate_limit,
    _clear_change_password_attempts,
    _clear_failed_login,
    _forgot_password_target_cooldown,
    _record_change_password_attempt,
    _record_failed_login,
    _record_forgot_password_attempt,
    current_user,
)
from app.schemas import (
    ChangePasswordRequest,
    ForgotPasswordRequest,
    LoginRequest,
    ProfileUpdate,
    ResetPasswordRequest,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/login")
def login(request: Request, payload: LoginRequest) -> dict[str, Any]:
    client_ip = request.client.host if request.client else "unknown"
    combo_key = f"attempt:{client_ip}:{payload.username.lower()}"
    ip_key = f"ip:{client_ip}"

    _check_login_rate_limit(combo_key, limit=5)
    _check_login_rate_limit(ip_key, limit=20)

    user = store.get_user_credentials(payload.username)
    if user is None or not user["is_active"]:
        store.verify_password(payload.password, DUMMY_PASSWORD_HASH)
        _record_failed_login(combo_key)
        _record_failed_login(ip_key)
        raise HTTPException(status_code=401, detail="Tên đăng nhập hoặc mật khẩu không đúng.")

    if not store.verify_password(payload.password, user["password_hash"]):
        _record_failed_login(combo_key)
        _record_failed_login(ip_key)
        raise HTTPException(status_code=401, detail="Tên đăng nhập hoặc mật khẩu không đúng.")

    _clear_failed_login(combo_key)

    if not isinstance(user.get("session_epoch"), str) or len(user["session_epoch"]) != 64:
        raise HTTPException(status_code=503, detail="Tài khoản chưa sẵn sàng tạo phiên. Vui lòng thử lại sau.")

    issued_at = datetime.now(timezone.utc)
    token = jwt.encode(
        {
            "sub": payload.username,
            "role": user["role"],
            "iat": int(issued_at.timestamp()),
            "exp": issued_at + timedelta(minutes=TOKEN_EXPIRE_MINUTES),
            "pwd_at": user.get("password_changed_at"),
            "session_epoch": user["session_epoch"],
            "force_pwd": bool(user.get("force_password_change", 0)),
        },
        SECRET_KEY,
        algorithm=ALGORITHM,
    )
    return {
        "token": token,
        "username": payload.username,
        "role": user["role"],
        "force_password_change": bool(user.get("force_password_change", 0)),
    }


@router.post("/logout")
def logout(request: Request) -> dict[str, Any]:
    actor = current_user(request)
    try:
        revoked = store.revoke_user_sessions(actor["username"], actor["session_epoch"])
    except store.DatabaseError as exc:
        raise HTTPException(status_code=503, detail="Chưa xác nhận thu hồi phiên trên máy chủ.") from exc
    return {"status": "success", "revoked": revoked, "scope": "all_sessions_in_authenticated_epoch"}


@router.post("/change-password")
def change_password(request: Request, payload: ChangePasswordRequest) -> dict[str, Any]:
    actor = current_user(request)
    user_key = f"user:{actor['username'].lower()}"
    _check_change_password_rate_limit(user_key)

    user = store.get_user_credentials(actor["username"])
    if user is None:
        raise HTTPException(status_code=404, detail="Không tìm thấy tài khoản.")

    if not store.verify_password(payload.old_password, user["password_hash"]):
        _record_change_password_attempt(user_key)
        raise HTTPException(status_code=400, detail="Mật khẩu hiện tại không chính xác.")

    if len(payload.new_password) < 12:
        raise HTTPException(status_code=422, detail="Mật khẩu mới phải có ít nhất 12 ký tự.")

    if payload.new_password.lower() == actor["username"].lower():
        raise HTTPException(
            status_code=400, detail="Mật khẩu mới không được trùng với tên đăng nhập."
        )

    if payload.new_password == payload.old_password:
        raise HTTPException(
            status_code=400, detail="Mật khẩu mới không được trùng với mật khẩu hiện tại."
        )

    _clear_change_password_attempts(user_key)
    store.update_user_password(actor["username"], payload.new_password, force_password_change=0)
    return {
        "status": "success",
        "message": (
            "Đổi mật khẩu thành công. Vui lòng đăng nhập lại bằng mật khẩu mới."
        ),
        "username": actor["username"],
        "require_relogin": True,
    }


@router.get("/me")
def who_am_i(request: Request) -> dict[str, Any]:
    user = current_user(request)
    profile = store.get_user_credentials(user["username"])
    if not profile:
        return user
    activity = store.get_user_activity(user["username"])
    return {
        "username": profile["username"],
        "role": profile["role"],
        "full_name": profile.get("full_name") or "",
        "email": profile.get("email") or "",
        "department": profile.get("department") or "",
        "phone": profile.get("phone") or "",
        "is_active": bool(profile.get("is_active", 1)),
        "password_changed_at": profile.get("password_changed_at") or "",
        "activity": activity,
    }


@router.patch("/profile")
def update_my_profile(request: Request, payload: ProfileUpdate) -> dict[str, Any]:
    actor = current_user(request)
    user = store.get_user_credentials(actor["username"])
    if user is None:
        raise HTTPException(status_code=404, detail="Không tìm thấy tài khoản.")

    updates = payload.model_dump(exclude_unset=True, exclude_none=True)
    updates.pop("current_password", None)
    if not updates:
        raise HTTPException(status_code=400, detail="Cần cung cấp ít nhất một trường để cập nhật.")

    new_email = updates.get("email")
    current_email = user.get("email") or ""
    if new_email is not None and new_email.strip().lower() != current_email.strip().lower():
        user_key = f"user:{actor['username'].lower()}"
        _check_change_password_rate_limit(user_key)
        if not payload.current_password:
            raise HTTPException(
                status_code=400,
                detail="Cần nhập mật khẩu hiện tại để thay đổi địa chỉ email bảo mật.",
            )
        if not store.verify_password(payload.current_password, user["password_hash"]):
            _record_change_password_attempt(user_key)
            raise HTTPException(
                status_code=403,
                detail="Mật khẩu hiện tại không chính xác. Không thể đổi email.",
            )
        _clear_change_password_attempts(user_key)

    safe_updates = {
        k: v for k, v in updates.items() if k in {"full_name", "email", "department", "phone"}
    }
    updated = store.update_user(actor["username"], safe_updates)
    if updated is None:
        raise HTTPException(status_code=404, detail="Không tìm thấy tài khoản.")
    activity = store.get_user_activity(actor["username"])
    return {
        "status": "success",
        "message": "Cập nhật thông tin cá nhân thành công.",
        "profile": {
            "username": updated["username"],
            "role": updated["role"],
            "full_name": updated.get("full_name") or "",
            "email": updated.get("email") or "",
            "department": updated.get("department") or "",
            "phone": updated.get("phone") or "",
            "is_active": bool(updated.get("is_active", 1)),
            "password_changed_at": updated.get("password_changed_at") or "",
            "activity": activity,
        },
    }


@router.post("/forgot-password")
def forgot_password(
    request: Request,
    payload: ForgotPasswordRequest,
    background_tasks: BackgroundTasks,
) -> dict[str, str]:
    client_ip = request.client.host if request.client else "unknown"
    ip_key = f"ip:{client_ip}"

    _check_forgot_password_rate_limit(ip_key)
    _record_forgot_password_attempt(ip_key)

    uniform_message = (
        "Nếu thông tin khớp với tài khoản trong hệ thống, hướng dẫn đặt lại mật khẩu "
        "sẽ được gửi đến email đăng ký của bạn. Vui lòng chờ và kiểm tra hộp thư."
    )

    user = store.find_user_for_password_reset(payload.identifier)
    if user is None or not user.get("is_active"):
        logger.warning(
            "Password reset requested for '%s' but no matching active user was found in database.",
            payload.identifier,
        )
        return {"status": "success", "message": uniform_message}

    user_email = user.get("email", "").strip()
    if not user_email:
        logger.warning(
            "Password reset requested for user %s but no email is configured.",
            user["username"],
        )
        return {"status": "success", "message": uniform_message}

    now = datetime.now(timezone.utc).timestamp()
    target_key = f"target:{user['username'].lower()}"
    last_sent = _forgot_password_target_cooldown.get(target_key, 0.0)
    if now - last_sent < 60.0:
        logger.info(
            "Password reset request for user %s is throttled by cooldown.",
            user["username"],
        )
        return {"status": "success", "message": uniform_message}

    _forgot_password_target_cooldown[target_key] = now
    if len(_forgot_password_target_cooldown) > 1000:
        _forgot_password_target_cooldown.clear()

    from app.email_outbox import request_password_email, wake_email_worker
    try:
        request_password_email(user['username'], 'reset', config.PUBLIC_BASE_URL or str(request.base_url).rstrip('/'))
    except (email_sender.EmailConfigurationError, *store.DatabaseError) as exc:
        logger.warning("Password email enqueue failed: %s", type(exc).__name__)
        return {"status": "success", "message": uniform_message}
    background_tasks.add_task(wake_email_worker)

    return {"status": "success", "message": uniform_message}


@router.post("/reset-password")
def reset_password(payload: ResetPasswordRequest) -> dict[str, Any]:
    if len(payload.new_password) < 12:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Mật khẩu mới phải có ít nhất 12 ký tự.",
        )
    username = store.reset_password_with_token(payload.token, payload.new_password)
    if not username:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Mã xác thực không hợp lệ, đã được sử dụng hoặc đã hết hạn.",
        )
    return {
        "status": "success",
        "message": "Đặt lại mật khẩu thành công. Vui lòng đăng nhập lại với mật khẩu mới.",
        "username": username,
        "require_relogin": True,
    }
