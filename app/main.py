from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app import config, email_sender, store
from app.config import DEMO_MODE
from app.dependencies import (
    APP_DIR,
    ATTACHMENTS_DIR,
    STATIC_DIR,
    _change_password_attempts,
    _failed_logins,
    _forgot_password_attempts,
    _forgot_password_target_cooldown,
    current_user,
    require_admin,
    require_staff,
    visible_ticket,
)
from app.rag import (
    BASE_KNOWLEDGE_DIR,
    KNOWLEDGE_DIR,
    STORAGE_KNOWLEDGE_DIR,
)
from app.routers import (
    admin_router,
    analytics_router,
    auth_router,
    knowledge_router,
    rag_router,
    tickets_router,
)
from app.schemas import (
    PRIORITY_SLA_MAPPING,
    AdminResetPasswordRequest,
    AssignmentUpdate,
    ChangePasswordRequest,
    CommentCreate,
    ForgotPasswordRequest,
    KnowledgeDocumentCreate,
    KnowledgeDocumentUpdate,
    KnowledgeReviewRequest,
    LoginRequest,
    NotificationTestRequest,
    Priority,
    ProfileUpdate,
    RAGFeedback,
    RAGQuestion,
    ResetPasswordRequest,
    Role,
    StatusUpdate,
    TicketCreate,
    TicketRating,
    TicketStatus,
    TicketUpdate,
    _validated_email,
)

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Khởi động: Kiểm tra cấu hình email và đưa ra cảnh báo nếu chạy production mà thiếu kênh email
    email_status = email_sender.get_email_status()
    if not config.DEMO_MODE:
        if email_status.get("is_mock"):
            logger.warning(
                "CẢNH BÁO MÔI TRƯỜNG PRODUCTION: Dịch vụ gửi email thật chưa được cấu hình "
                "(EMAIL_PROVIDER/SMTP_ENABLED/RESEND_API_KEY/BREVO_API_KEY). "
                "Email khôi phục mật khẩu và thông báo tài khoản mới sẽ chỉ ghi nhận vào mock outbox trong RAM!"
            )
        if not config.PUBLIC_BASE_URL:
            logger.warning(
                "CẢNH BÁO: PUBLIC_BASE_URL chưa được thiết lập. "
                "Liên kết khôi phục mật khẩu và đăng nhập có thể không trỏ đúng tên miền public."
            )
    else:
        logger.info(
            "OpsMind Helpdesk đang chạy ở chế độ DEMO_MODE. Kênh email: %s (%s).",
            email_status["provider"],
            email_status["target"],
        )
    yield


app = FastAPI(
    title="Helpdesk RAG",
    description=(
        "Cổng tự phục vụ CNTT và bảng điều phối ticket có trợ lý tri thức dẫn nguồn.\n\n"
        "### Chuẩn hóa mức độ ưu tiên sự cố (SLA Priority Mapping):\n"
        "- **P1 (urgent)**: Khẩn cấp — Cam kết xử lý trong 2 giờ\n"
        "- **P2 (high)**: Cao — Cam kết xử lý trong 8 giờ\n"
        "- **P3 (medium)**: Tiêu chuẩn / Trung bình — Cam kết xử lý trong 24 giờ\n"
        "- **P4 (low)**: Thấp — Cam kết xử lý trong 48 giờ"
    ),
    version="1.0.0",
    lifespan=lifespan,
)

app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

# Mount Routers
app.include_router(auth_router)
app.include_router(tickets_router)
app.include_router(knowledge_router)
app.include_router(rag_router)
app.include_router(admin_router)
app.include_router(analytics_router)


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
        raise HTTPException(
            status_code=503, detail="Cơ sở dữ liệu hiện không sẵn sàng."
        ) from exc
    return {"status": "ok", "service": "helpdesk-rag"}


__all__ = [
    "APP_DIR",
    "ATTACHMENTS_DIR",
    "AdminResetPasswordRequest",
    "AssignmentUpdate",
    "BASE_KNOWLEDGE_DIR",
    "ChangePasswordRequest",
    "CommentCreate",
    "ForgotPasswordRequest",
    "KNOWLEDGE_DIR",
    "KnowledgeDocumentCreate",
    "KnowledgeDocumentUpdate",
    "KnowledgeReviewRequest",
    "LoginRequest",
    "NotificationTestRequest",
    "PRIORITY_SLA_MAPPING",
    "Priority",
    "ProfileUpdate",
    "RAGFeedback",
    "RAGQuestion",
    "ResetPasswordRequest",
    "Role",
    "STATIC_DIR",
    "STORAGE_KNOWLEDGE_DIR",
    "StatusUpdate",
    "TicketCreate",
    "TicketRating",
    "TicketStatus",
    "TicketUpdate",
    "_change_password_attempts",
    "_failed_logins",
    "_forgot_password_attempts",
    "_forgot_password_target_cooldown",
    "_validated_email",
    "app",
    "current_user",
    "require_admin",
    "require_staff",
    "visible_ticket",
]
