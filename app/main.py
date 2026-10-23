from __future__ import annotations

import asyncio
import logging
from contextlib import suppress
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from starlette.concurrency import run_in_threadpool

from app import email_sender, store
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

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    email_status = email_sender.validate_email_configuration()
    logger.info("Email provider configured: %s; demo capture=%s", email_status['provider'], email_status['is_mock'])
    # OPS-03: Dọn dẹp bản ghi giới hạn tốc độ (rate-limit attempts) hết hạn
    try:
        await run_in_threadpool(store.cleanup_expired_rate_limits)
    except Exception as exc:
        logger.debug("Initial rate-limit cleanup skipped: %s", exc)

    cleanup_task = None

    async def _periodic_rate_limit_cleanup() -> None:
        while True:
            await asyncio.sleep(3600)
            try:
                await run_in_threadpool(store.cleanup_expired_rate_limits)
            except Exception as exc:
                logger.warning("Periodic rate-limit cleanup failed: %s", exc)

    try:
        cleanup_task = asyncio.create_task(_periodic_rate_limit_cleanup())
    except RuntimeError:
        cleanup_task = None

    from app.notification_outbox import process_notification_outbox
    from app.email_outbox import wake_email_worker

    async def _notification_worker():
        while True:
            try:
                await run_in_threadpool(process_notification_outbox)
            except Exception as exc:
                logger.warning("Notification worker failed: %s", type(exc).__name__)
            await asyncio.sleep(5)

    notification_task = asyncio.create_task(_notification_worker())

    async def _email_worker():
        while True:
            await run_in_threadpool(wake_email_worker)
            await asyncio.sleep(5)

    email_task = asyncio.create_task(_email_worker())
    try:
        yield
    finally:
        notification_task.cancel()
        email_task.cancel()
        with suppress(asyncio.CancelledError):
            await notification_task
        with suppress(asyncio.CancelledError):
            await email_task
        if cleanup_task:
            cleanup_task.cancel()
            with suppress(asyncio.CancelledError):
                await cleanup_task


app = FastAPI(
    title="Helpdesk RAG",
    description=(
        "Cổng tự phục vụ CNTT và bảng điều phối ticket có trợ lý tri thức dẫn nguồn.\n\n"
        "### Chuẩn hóa mức độ ưu tiên sự cố (SLA Priority Mapping):\n"
        "- **P1 (urgent)**: Khẩn cấp — Cam kết xử lý trong 2 giờ\n"
        "- **P2 (high)**: Cao — Cam kết xử lý trong 8 giờ\n"
        "- **P3 (medium)**: Tiêu chuẩn / Trung bình — Cam kết xử lý trong 24 giờ\n"
        "- **P4 (low)**: Thấp — Cam kết xử lý trong 48 giờ\n\n"
        "> **Lưu ý kiến trúc SLA:** Hạn chót xử lý (sla_deadline) được tính toán cố định từ thời điểm "
        "tạo ticket dựa trên bảng SLA Priority. Trạng thái chờ người dùng (pending_waiting_user) "
        "hiện được theo dõi minh bạch qua nhật ký audit mà không tự động tạm dừng đồng hồ SLA (không pause)."
    ),
    version="1.0.0",
    lifespan=lifespan,
)

app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

# Mount Routers
app.include_router(auth_router)
app.include_router(auth_router, prefix="/api")
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
    "BASE_KNOWLEDGE_DIR",
    "KNOWLEDGE_DIR",
    "STATIC_DIR",
    "STORAGE_KNOWLEDGE_DIR",
    "_change_password_attempts",
    "_failed_logins",
    "_forgot_password_attempts",
    "_forgot_password_target_cooldown",
    "app",
    "current_user",
    "require_admin",
    "require_staff",
    "visible_ticket",
]
