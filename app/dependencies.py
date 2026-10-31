from __future__ import annotations
from typing import Any

import logging
import secrets
from datetime import datetime, timezone
from pathlib import Path

import jwt
from fastapi import HTTPException, Request, status

from app import store
from app.config import ALGORITHM, SECRET_KEY, STORAGE_PATH

logger = logging.getLogger(__name__)

APP_DIR = Path(__file__).resolve().parent
STATIC_DIR = APP_DIR / "static"
ATTACHMENTS_DIR = Path(STORAGE_PATH).resolve() / "attachments"

DUMMY_PASSWORD_HASH = store._password_hash("dummy_fallback_timing_attack_mitigation")
class RateLimitStoreProxy(dict):
    """Database-backed rate limit proxy with an in-memory dictionary interface for backward compatibility."""

    def __init__(self, key_prefix: str, window_seconds: float):
        super().__init__()
        self.key_prefix = key_prefix
        self.window_seconds = window_seconds

    def _full_key(self, key: str) -> str:
        return f"{self.key_prefix}:{key}"

    def __getitem__(self, key: str) -> list[float]:
        attempts = store.get_rate_limit_attempts(self._full_key(key), self.window_seconds)
        if not attempts:
            raise KeyError(key)
        return attempts

    def get(self, key: str, default: Any = None) -> Any:
        attempts = store.get_rate_limit_attempts(self._full_key(key), self.window_seconds)
        return attempts if attempts else default

    def __contains__(self, key: object) -> bool:
        if not isinstance(key, str):
            return False
        return bool(store.get_rate_limit_attempts(self._full_key(key), self.window_seconds))

    def pop(self, key: str, default: Any = None) -> Any:
        attempts = store.get_rate_limit_attempts(self._full_key(key), self.window_seconds)
        store.reset_rate_limit(self._full_key(key))
        return attempts if attempts else default

    def clear(self) -> None:
        super().clear()
        store.clear_all_rate_limits(self.key_prefix)

    def record(self, key: str) -> None:
        store.record_rate_limit_attempt(self._full_key(key))

    def check(self, key: str, limit: int, error_message: str) -> None:
        attempts = store.get_rate_limit_attempts(self._full_key(key), self.window_seconds)
        if len(attempts) >= limit:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=error_message,
            )


FAILED_LOGIN_LIMIT = 5
FAILED_LOGIN_WINDOW_SECONDS = 900.0
_failed_logins: RateLimitStoreProxy = RateLimitStoreProxy("login", FAILED_LOGIN_WINDOW_SECONDS)

FORGOT_PASSWORD_LIMIT = 5
FORGOT_PASSWORD_WINDOW_SECONDS = 900.0
_forgot_password_attempts: RateLimitStoreProxy = RateLimitStoreProxy("forgot", FORGOT_PASSWORD_WINDOW_SECONDS)
_forgot_password_target_cooldown: dict[str, float] = {}

CHANGE_PASSWORD_LIMIT = 5
CHANGE_PASSWORD_WINDOW_SECONDS = 900.0
_change_password_attempts: RateLimitStoreProxy = RateLimitStoreProxy("change", CHANGE_PASSWORD_WINDOW_SECONDS)


def _cleanup_rate_limits(store_dict: Any, window_seconds: float) -> None:
    store.cleanup_expired_rate_limits(window_seconds)


def _check_rate_limit(
    proxy: Any,
    key: str,
    limit: int,
    window_seconds: float,
    error_message: str,
) -> None:
    if hasattr(proxy, "check"):
        proxy.check(key, limit, error_message)
    else:
        attempts = [t for t in proxy.get(key, []) if datetime.now(timezone.utc).timestamp() - t < window_seconds]
        if len(attempts) >= limit:
            raise HTTPException(status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail=error_message)


def _record_attempt(
    proxy: Any,
    key: str,
    window_seconds: float,
) -> None:
    if hasattr(proxy, "record"):
        proxy.record(key)
    else:
        now = datetime.now(timezone.utc).timestamp()
        attempts = [t for t in proxy.get(key, []) if now - t < window_seconds]
        attempts.append(now)
        proxy[key] = attempts


def _check_login_rate_limit(key: str, limit: int = FAILED_LOGIN_LIMIT) -> None:
    _failed_logins.check(
        key,
        limit,
        "Đã thử đăng nhập sai quá nhiều lần. Vui lòng thử lại sau 15 phút.",
    )


def _record_failed_login(key: str) -> None:
    _failed_logins.record(key)


def _clear_failed_login(key: str) -> None:
    _failed_logins.pop(key, None)


def _check_forgot_password_rate_limit(key: str) -> None:
    _forgot_password_attempts.check(
        key,
        FORGOT_PASSWORD_LIMIT,
        "Bạn đã yêu cầu đặt lại mật khẩu quá nhiều lần. Vui lòng thử lại sau 15 phút.",
    )


def _record_forgot_password_attempt(key: str) -> None:
    _forgot_password_attempts.record(key)


def _check_change_password_rate_limit(key: str) -> None:
    _change_password_attempts.check(
        key,
        CHANGE_PASSWORD_LIMIT,
        "Bạn đã nhập sai mật khẩu hiện tại quá nhiều lần. Vui lòng thử lại sau 15 phút.",
    )


def _record_change_password_attempt(key: str) -> None:
    _change_password_attempts.record(key)


def _clear_change_password_attempts(key: str) -> None:
    _change_password_attempts.pop(key, None)


def current_user(request: Request) -> dict[str, str]:
    """Read credentials synchronously; async callers must offload this DB-backed helper."""
    auth_header = request.headers.get("Authorization", "")
    scheme, _, token = auth_header.partition(" ")
    if scheme.lower() != "bearer" or not token:
        raise HTTPException(status_code=401, detail="Vui lòng đăng nhập để tiếp tục.")
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM],
                             options={"require": ["sub", "exp", "iat", "session_epoch"]})
    except jwt.PyJWTError as exc:
        raise HTTPException(
            status_code=401, detail="Phiên đăng nhập không hợp lệ hoặc đã hết hạn."
        ) from exc

    username = payload.get("sub")
    user = store.get_user_credentials(username) if isinstance(username, str) else None
    if user is None or not user["is_active"] or payload.get("role") != user["role"]:
        raise HTTPException(status_code=401, detail="Tài khoản không còn hợp lệ.")

    if user.get("password_changed_at"):
        if payload.get("pwd_at") != user.get("password_changed_at"):
            raise HTTPException(
                status_code=401,
                detail="Mật khẩu đã được thay đổi. Vui lòng đăng nhập lại.",
            )

    epoch = payload.get("session_epoch")
    if (not isinstance(epoch, str) or len(epoch) != 64 or not epoch.isascii()
            or not secrets.compare_digest(epoch, user.get("session_epoch") or "")):
        raise HTTPException(status_code=401, detail="Phiên đăng nhập đã bị thu hồi. Vui lòng đăng nhập lại.")

    if user.get("force_password_change"):
        allowed_paths = {prefix + path for prefix in ("", "/api")
                         for path in ("/auth/change-password", "/auth/me", "/auth/logout")}
        if request.url.path not in allowed_paths:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Quản trị viên yêu cầu bạn đổi mật khẩu trước khi tiếp tục.",
            )

    return {
        "username": username,
        "role": user["role"],
        "session_epoch": user["session_epoch"],
        "force_password_change": bool(user.get("force_password_change")),
    }


def require_staff(user: dict[str, str]) -> None:
    if user["role"] not in {"agent", "admin"}:
        raise HTTPException(status_code=403, detail="Chỉ nhân viên IT mới được thực hiện thao tác này.")


def require_admin(user: dict[str, str]) -> None:
    if user["role"] != "admin":
        raise HTTPException(status_code=403, detail="Chỉ Admin mới có quyền thực hiện thao tác này.")


def visible_ticket(ticket_id: int, user: dict[str, str]) -> dict:
    ticket = store.get_ticket(ticket_id)
    if ticket is None:
        raise HTTPException(status_code=404, detail="Không tìm thấy ticket.")
    if user["role"] == "user" and ticket["requester"] != user["username"]:
        raise HTTPException(status_code=404, detail="Không tìm thấy ticket.")
    return ticket
