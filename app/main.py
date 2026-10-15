from __future__ import annotations

import csv
import io
import logging
import re
import uuid
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Literal

import jwt
from fastapi import BackgroundTasks, FastAPI, File, HTTPException, Query, Request, UploadFile, status
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
from app import config, email_sender, store
from app.notifications import (
    dispatch_ticket_notification,
    get_notification_channels_status,
    send_test_notification,
)
from app.rag import (
    BASE_KNOWLEDGE_DIR,
    STORAGE_KNOWLEDGE_DIR,
    KNOWLEDGE_DIR,
    build_retrieval_index,
    generate_answer,
    load_knowledge_base,
    save_knowledge_document,
)

logger = logging.getLogger(__name__)

DUMMY_PASSWORD_HASH = store._password_hash("dummy_fallback_timing_attack_mitigation")
FAILED_LOGIN_LIMIT = 5
FAILED_LOGIN_LIMIT = 5
FAILED_LOGIN_WINDOW_SECONDS = 900
_failed_logins: dict[str, list[float]] = {}

FORGOT_PASSWORD_LIMIT = 5
FORGOT_PASSWORD_WINDOW_SECONDS = 900
_forgot_password_attempts: dict[str, list[float]] = {}
_forgot_password_target_cooldown: dict[str, float] = {}

CHANGE_PASSWORD_LIMIT = 5
CHANGE_PASSWORD_WINDOW_SECONDS = 900
_change_password_attempts: dict[str, list[float]] = {}


def _cleanup_rate_limits(store_dict: dict[str, list[float]], window_seconds: float) -> None:
    now = datetime.now(timezone.utc).timestamp()
    expired = [k for k, timestamps in store_dict.items() if not timestamps or (now - timestamps[-1] >= window_seconds)]
    for k in expired:
        store_dict.pop(k, None)


def _check_rate_limit(
    store_dict: dict[str, list[float]],
    key: str,
    limit: int,
    window_seconds: float,
    error_message: str,
) -> None:
    _cleanup_rate_limits(store_dict, window_seconds)
    now = datetime.now(timezone.utc).timestamp()
    attempts = [t for t in store_dict.get(key, []) if now - t < window_seconds]
    store_dict[key] = attempts
    if len(attempts) >= limit:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=error_message,
        )


def _record_attempt(
    store_dict: dict[str, list[float]],
    key: str,
    window_seconds: float,
) -> None:
    now = datetime.now(timezone.utc).timestamp()
    attempts = [t for t in store_dict.get(key, []) if now - t < window_seconds]
    attempts.append(now)
    store_dict[key] = attempts


def _check_login_rate_limit(key: str, limit: int = FAILED_LOGIN_LIMIT) -> None:
    _check_rate_limit(
        _failed_logins,
        key,
        limit,
        FAILED_LOGIN_WINDOW_SECONDS,
        "Đã thử đăng nhập sai quá nhiều lần. Vui lòng thử lại sau 15 phút.",
    )


def _record_failed_login(key: str) -> None:
    _record_attempt(_failed_logins, key, FAILED_LOGIN_WINDOW_SECONDS)


def _clear_failed_login(key: str) -> None:
    _failed_logins.pop(key, None)


def _check_forgot_password_rate_limit(key: str) -> None:
    _check_rate_limit(
        _forgot_password_attempts,
        key,
        FORGOT_PASSWORD_LIMIT,
        FORGOT_PASSWORD_WINDOW_SECONDS,
        "Bạn đã yêu cầu đặt lại mật khẩu quá nhiều lần. Vui lòng thử lại sau 15 phút.",
    )


def _record_forgot_password_attempt(key: str) -> None:
    _record_attempt(_forgot_password_attempts, key, FORGOT_PASSWORD_WINDOW_SECONDS)


def _check_change_password_rate_limit(key: str) -> None:
    _check_rate_limit(
        _change_password_attempts,
        key,
        CHANGE_PASSWORD_LIMIT,
        CHANGE_PASSWORD_WINDOW_SECONDS,
        "Bạn đã nhập sai mật khẩu hiện tại quá nhiều lần. Vui lòng thử lại sau 15 phút.",
    )


def _record_change_password_attempt(key: str) -> None:
    _record_attempt(_change_password_attempts, key, CHANGE_PASSWORD_WINDOW_SECONDS)


def _clear_change_password_attempts(key: str) -> None:
    _change_password_attempts.pop(key, None)

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


class ProfileUpdate(BaseModel):
    full_name: str | None = Field(default=None, max_length=120)
    email: str | None = Field(default=None, max_length=254)
    department: str | None = Field(default=None, max_length=120)
    phone: str | None = Field(default=None, max_length=40)
    current_password: str | None = Field(default=None, max_length=128)

    @field_validator("email")
    @classmethod
    def validate_email(cls, value: str | None) -> str | None:
        return _validated_email(value)

    @field_validator("full_name", "department", "phone", mode="before")
    @classmethod
    def trim_text(cls, value: object) -> object:
        return value.strip() if isinstance(value, str) else value

    @model_validator(mode="after")
    def require_update_field(self) -> "ProfileUpdate":
        fields = [f for f in type(self).model_fields if f != "current_password"]
        if not any(getattr(self, field_name) is not None for field_name in fields):
            raise ValueError("Cần cung cấp ít nhất một trường để cập nhật.")
        return self


class ChangePasswordRequest(BaseModel):
    old_password: str = Field(min_length=1, max_length=200)
    new_password: str = Field(min_length=12, max_length=200)


class AdminResetPasswordRequest(BaseModel):
    new_password: str = Field(min_length=12, max_length=200)
    force_change: bool = True


class ForgotPasswordRequest(BaseModel):
    identifier: str = Field(min_length=3, max_length=254)

    @field_validator("identifier", mode="before")
    @classmethod
    def trim_identifier(cls, value: object) -> object:
        return value.strip() if isinstance(value, str) else value


class ResetPasswordRequest(BaseModel):
    token: str = Field(min_length=16, max_length=128)
    new_password: str = Field(min_length=12, max_length=200)

    @field_validator("token", "new_password", mode="before")
    @classmethod
    def trim_fields(cls, value: object) -> object:
        return value.strip() if isinstance(value, str) else value


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


class KnowledgeDocumentCreate(BaseModel):
    title: str = Field(min_length=3, max_length=150)
    category: Literal["network", "hardware", "software", "security", "general"]
    tags: str = Field(default="", max_length=200)
    content: str = Field(min_length=10)
    status: Literal["draft", "pending_review", "published"] = "draft"

    @field_validator("title", "content", "tags", mode="before")
    @classmethod
    def trim_text(cls, value: object) -> object:
        return value.strip() if isinstance(value, str) else value


class KnowledgeDocumentUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=3, max_length=150)
    category: Literal["network", "hardware", "software", "security", "general"] | None = None
    tags: str | None = Field(default=None, max_length=200)
    content: str | None = Field(default=None, min_length=10)
    status: Literal["draft", "pending_review", "published", "archived"] | None = None
    change_summary: str | None = Field(default="Cập nhật tài liệu", max_length=300)

    @field_validator("title", "content", "tags", "change_summary", mode="before")
    @classmethod
    def trim_optional_text(cls, value: object) -> object:
        if isinstance(value, str):
            return value.strip() or None
        return value


class KnowledgeReviewRequest(BaseModel):
    action: Literal["approve", "reject"]
    feedback: str | None = Field(default=None, max_length=1000)


class NotificationTestRequest(BaseModel):
    channel: Literal["telegram", "discord"]


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

    if user.get("password_changed_at"):
        if payload.get("pwd_at") != user.get("password_changed_at"):
            raise HTTPException(
                status_code=401,
                detail="Mật khẩu đã được thay đổi. Vui lòng đăng nhập lại.",
            )

    if user.get("force_password_change"):
        allowed_paths = {"/auth/change-password", "/auth/me", "/auth/logout"}
        if request.url.path not in allowed_paths:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Quản trị viên yêu cầu bạn đổi mật khẩu trước khi tiếp tục.",
            )

    return {"username": username, "role": user["role"], "force_password_change": bool(user.get("force_password_change"))}


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


@app.api_route("/", methods=["GET", "HEAD"], include_in_schema=False)
async def serve_index() -> FileResponse:
    return FileResponse(STATIC_DIR / "index.html")


@app.api_route("/config", methods=["GET", "HEAD"], tags=["system"])
async def public_config() -> dict[str, bool]:
    return {"demo_mode": DEMO_MODE}


@app.api_route("/health", methods=["GET", "HEAD"], tags=["system"])
async def health() -> dict[str, str]:
    try:
        store.check_database()
    except store.DatabaseError as exc:
        raise HTTPException(status_code=503, detail="Cơ sở dữ liệu hiện không sẵn sàng.") from exc
    return {"status": "ok", "service": "helpdesk-rag"}


@app.post("/auth/login", tags=["auth"])
async def login(request: Request, payload: LoginRequest) -> dict[str, Any]:
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

    issued_at = datetime.now(timezone.utc)
    token = jwt.encode(
        {
            "sub": payload.username,
            "role": user["role"],
            "iat": int(issued_at.timestamp()),
            "exp": issued_at + timedelta(minutes=TOKEN_EXPIRE_MINUTES),
            "pwd_at": user.get("password_changed_at"),
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


@app.post("/auth/change-password", tags=["auth"])
async def change_password(request: Request, payload: ChangePasswordRequest) -> dict[str, str]:
    actor = await current_user(request)
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
        raise HTTPException(status_code=400, detail="Mật khẩu mới không được trùng với tên đăng nhập.")

    if payload.new_password == payload.old_password:
        raise HTTPException(status_code=400, detail="Mật khẩu mới không được trùng với mật khẩu hiện tại.")

    _clear_change_password_attempts(user_key)
    store.update_user_password(actor["username"], payload.new_password, force_password_change=0)
    return {"message": "Đổi mật khẩu thành công. Vui lòng sử dụng mật khẩu mới cho các lần đăng nhập tiếp theo."}


@app.get("/auth/me", tags=["auth"])
async def who_am_i(request: Request) -> dict[str, Any]:
    user = await current_user(request)
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


@app.patch("/auth/profile", tags=["auth"])
async def update_my_profile(request: Request, payload: ProfileUpdate) -> dict[str, Any]:
    actor = await current_user(request)
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
        if not payload.current_password:
            raise HTTPException(
                status_code=400,
                detail="Cần nhập mật khẩu hiện tại để thay đổi địa chỉ email bảo mật.",
            )
        if not store.verify_password(payload.current_password, user["password_hash"]):
            raise HTTPException(
                status_code=403,
                detail="Mật khẩu hiện tại không chính xác. Không thể đổi email.",
            )

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


@app.post("/auth/forgot-password", tags=["auth"])
async def forgot_password(
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
        "đã được gửi đến email đăng ký của bạn."
    )

    user = store.find_user_for_password_reset(payload.identifier)
    if user is None or not user.get("is_active"):
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
        logger.info("Password reset request for user %s is throttled by cooldown.", user["username"])
        return {"status": "success", "message": uniform_message}

    _forgot_password_target_cooldown[target_key] = now
    if len(_forgot_password_target_cooldown) > 1000:
        _forgot_password_target_cooldown.clear()

    token = store.create_password_reset_token(
        user["username"],
        expires_minutes=config.RESET_TOKEN_EXPIRE_MINUTES,
    )

    base_url = config.PUBLIC_BASE_URL or str(request.base_url).rstrip("/")
    background_tasks.add_task(
        email_sender.send_password_reset_email,
        to_email=user_email,
        username=user["username"],
        reset_token=token,
        base_url=base_url,
    )

    return {"status": "success", "message": uniform_message}


@app.post("/auth/reset-password", tags=["auth"])
async def reset_password(payload: ResetPasswordRequest) -> dict[str, str]:
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
    }


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


@app.post("/admin/users/{username}/reset-password", tags=["admin"])
async def admin_reset_user_password(
    request: Request,
    username: str,
    payload: AdminResetPasswordRequest,
) -> dict[str, str]:
    actor = await current_user(request)
    if actor["role"] != "admin":
        raise HTTPException(status_code=403, detail="Chỉ Admin mới được quản lý tài khoản.")
    existing = store.get_user_credentials(username)
    if existing is None:
        raise HTTPException(status_code=404, detail="Không tìm thấy tài khoản.")
    if len(payload.new_password) < 12:
        raise HTTPException(status_code=422, detail="Mật khẩu mới phải có ít nhất 12 ký tự.")
    if payload.new_password.lower() == username.lower():
        raise HTTPException(status_code=400, detail="Mật khẩu mới không được trùng với tên đăng nhập.")
    store.admin_reset_password(
        username,
        payload.new_password,
        force_password_change=1 if payload.force_change else 0,
    )
    return {"message": f"Đã đặt lại mật khẩu cho tài khoản {username}."}


@app.get("/admin/notifications/status", tags=["admin"])
async def get_notifications_status(request: Request) -> dict:
    actor = await current_user(request)
    if actor["role"] != "admin":
        raise HTTPException(status_code=403, detail="Chỉ Admin mới được xem cấu hình thông báo.")
    return get_notification_channels_status()


@app.post("/admin/notifications/test", tags=["admin"])
async def test_notification_channel(request: Request, payload: NotificationTestRequest) -> dict:
    actor = await current_user(request)
    if actor["role"] != "admin":
        raise HTTPException(status_code=403, detail="Chỉ Admin mới được gửi thông báo thử nghiệm.")
    ok = send_test_notification(payload.channel)
    if not ok:
        raise HTTPException(
            status_code=400,
            detail=f"Không thể gửi thông báo tới kênh {payload.channel}. Vui lòng kiểm tra lại token/webhook và biến môi trường.",
        )
    return {
        "success": True,
        "channel": payload.channel,
        "message": f"Đã gửi thông báo thử nghiệm thành công tới {payload.channel}.",
    }


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
async def create_new_ticket(request: Request, payload: TicketCreate, background_tasks: BackgroundTasks) -> dict:
    user = await current_user(request)
    ticket = store.create_ticket(
        title=payload.title.strip(),
        description=payload.description.strip(),
        category=payload.category.strip().lower(),
        priority=payload.priority,
        requester=user["username"],
    )
    background_tasks.add_task(dispatch_ticket_notification, dict(ticket))
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
        msg = "Yêu cầu này đã được đánh giá trước đó." if "already been rated" in str(exc) else "Chỉ đánh giá được ticket đã giải quyết."
        raise HTTPException(status_code=409, detail=msg) from exc
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
async def knowledge_documents(
    request: Request,
    status: str | None = Query(default=None),
    category: str | None = Query(default=None),
    search: str | None = Query(default=None),
) -> list[dict[str, Any]]:
    user = await current_user(request)
    is_staff = user["role"] in {"agent", "admin"}
    effective_status = status if is_staff else "published"
    docs = store.list_knowledge_documents(
        status=effective_status,
        category=category,
        query=search,
    )
    if not docs and KNOWLEDGE_DIR.resolve() != BASE_KNOWLEDGE_DIR.resolve():
        return [
            {
                "title": document["title"],
                "source": document["source"],
                "is_builtin": bool(document.get("is_builtin", True)),
                "category": document.get("category", "general"),
                "status": "published",
            }
            for document in load_knowledge_base()
        ]
    return [{**doc, "source": doc["slug"]} for doc in docs]


@app.get("/knowledge/{identifier}", tags=["rag"])
async def get_single_knowledge_document(
    request: Request,
    identifier: str,
) -> dict[str, Any]:
    user = await current_user(request)
    doc = store.get_knowledge_document(identifier)
    if not doc:
        if (KNOWLEDGE_DIR / identifier).is_file():
            content = (KNOWLEDGE_DIR / identifier).read_text(encoding="utf-8")
            heading = re.search(r"(?m)^#\s+(.+?)\s*$", content)
            title = heading.group(1).strip() if heading else identifier
            return {
                "id": None,
                "slug": identifier,
                "source": identifier,
                "title": title,
                "category": store.get_document_category_from_db(identifier),
                "tags": "",
                "content": content,
                "status": "published",
                "author": "admin",
                "reviewer": "admin",
                "approved_at": None,
                "created_at": None,
                "updated_at": None,
                "is_builtin": (BASE_KNOWLEDGE_DIR / identifier).is_file(),
                "version_count": 1,
            }
        raise HTTPException(status_code=404, detail="Không tìm thấy tài liệu.")

    if user["role"] == "user" and doc["status"] != "published":
        raise HTTPException(status_code=404, detail="Không tìm thấy tài liệu.")

    return {**doc, "source": doc["slug"]}


@app.put("/knowledge/{identifier}", tags=["rag"])
async def edit_knowledge_document(
    request: Request,
    identifier: str,
    payload: KnowledgeDocumentUpdate,
) -> dict[str, Any]:
    user = await current_user(request)
    require_staff(user)
    doc = store.get_knowledge_document(identifier)
    if not doc:
        raise HTTPException(status_code=404, detail="Không tìm thấy tài liệu.")

    if user["role"] == "agent":
        if doc["author"] != user["username"] and doc["status"] == "draft":
            raise HTTPException(status_code=403, detail="Chỉ tác giả hoặc Admin mới được sửa bản nháp này.")
        if payload.status == "archived":
            raise HTTPException(status_code=403, detail="Chỉ Quản trị viên (Admin) mới có quyền lưu trữ (archive) tài liệu tri thức.")
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
    return {"message": "Đã cập nhật tài liệu tri thức.", **(updated or {}), "source": updated["slug"] if updated else ""}


@app.post("/knowledge/{identifier}/review", tags=["rag"])
async def review_knowledge_document_endpoint(
    request: Request,
    identifier: str,
    payload: KnowledgeReviewRequest,
) -> dict[str, Any]:
    user = await current_user(request)
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
    msg = "Đã duyệt và xuất bản tài liệu." if payload.action == "approve" else "Đã trả về bản nháp."
    return {"message": msg, **(reviewed or {}), "source": reviewed["slug"] if reviewed else ""}


@app.get("/knowledge/{identifier}/versions", tags=["rag"])
async def get_knowledge_versions(
    request: Request,
    identifier: str,
) -> list[dict[str, Any]]:
    user = await current_user(request)
    require_staff(user)
    doc = store.get_knowledge_document(identifier)
    if not doc:
        raise HTTPException(status_code=404, detail="Không tìm thấy tài liệu.")
    return store.list_knowledge_versions(doc["id"])


@app.post("/knowledge/{identifier}/restore/{version_number}", tags=["rag"])
async def restore_knowledge_version_endpoint(
    request: Request,
    identifier: str,
    version_number: int,
) -> dict[str, Any]:
    user = await current_user(request)
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
    return {"message": f"Đã khôi phục về phiên bản #{version_number}.", **restored, "source": restored["slug"]}


@app.delete("/knowledge/{source}", tags=["rag"])
async def delete_knowledge_document(request: Request, source: str) -> dict[str, str]:
    user = await current_user(request)
    if user["role"] != "admin":
        raise HTTPException(status_code=403, detail="Chỉ Admin mới được quản lý tài liệu tri thức.")
    if not re.fullmatch(r"[a-z0-9][a-z0-9_-]{0,63}\.md", source):
        raise HTTPException(status_code=422, detail="Tên nguồn tài liệu không hợp lệ.")

    doc = store.get_knowledge_document(source)
    if doc and doc["is_builtin"]:
        raise HTTPException(status_code=403, detail="Không thể xóa tài liệu mặc định của hệ thống.")

    deleted_any = False
    if doc:
        store.delete_knowledge_document(doc["id"])
        deleted_any = True

    target = (KNOWLEDGE_DIR / source).resolve()
    if target.is_file() and target.parent == KNOWLEDGE_DIR.resolve():
        if KNOWLEDGE_DIR.resolve() == BASE_KNOWLEDGE_DIR.resolve():
            raise HTTPException(status_code=403, detail="Không thể xóa tài liệu mặc định của hệ thống.")
        try:
            target.unlink()
            deleted_any = True
        except OSError as exc:
            raise HTTPException(status_code=500, detail="Không thể xóa tài liệu tri thức.") from exc

    if (STORAGE_KNOWLEDGE_DIR / source).is_file():
        (STORAGE_KNOWLEDGE_DIR / source).unlink(missing_ok=True)
        deleted_any = True

    if (BASE_KNOWLEDGE_DIR / source).is_file():
        raise HTTPException(status_code=403, detail="Không thể xóa tài liệu mặc định của hệ thống.")

    if not deleted_any:
        raise HTTPException(status_code=404, detail="Không tìm thấy tài liệu.")

    load_knowledge_base.cache_clear()
    build_retrieval_index.cache_clear()
    return {"message": "Đã xóa tài liệu khỏi Knowledge Base."}


@app.post("/knowledge/{source}/reindex", tags=["rag"])
async def reindex_knowledge_document(request: Request, source: str) -> dict[str, str]:
    user = await current_user(request)
    if user["role"] != "admin":
        raise HTTPException(status_code=403, detail="Chỉ Admin mới được quản lý tài liệu tri thức.")
    if not re.fullmatch(r"[a-z0-9][a-z0-9_-]{0,63}\.md", source):
        raise HTTPException(status_code=422, detail="Tên nguồn tài liệu không hợp lệ.")
    doc = store.get_knowledge_document(source)
    if not doc and not (KNOWLEDGE_DIR / source).is_file() and not (BASE_KNOWLEDGE_DIR / source).is_file():
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
) -> dict[str, Any]:
    content_type = request.headers.get("content-type", "")
    if "multipart/form-data" in content_type:
        user = await current_user(request)
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

    user = await current_user(request)
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
        raise HTTPException(status_code=403, detail="Chỉ Admin mới có quyền xuất bản tài liệu trực tiếp.")

    target_status = payload.status
    if user["role"] == "agent" and target_status not in ("draft", "pending_review"):
        target_status = "draft"

    doc = store.create_knowledge_document(
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
