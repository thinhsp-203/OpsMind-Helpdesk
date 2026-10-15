from __future__ import annotations

import logging
import smtplib
from email.message import EmailMessage
from typing import Any

from app import config

from collections import deque

logger = logging.getLogger(__name__)

# Bounded outbox buffer for mock/testing inspection (limited to 50 records)
_outbox: deque[dict[str, Any]] = deque(maxlen=50)


def get_outbox() -> list[dict[str, Any]]:
    """Return a copy of messages sent in test/mock mode."""
    return list(_outbox)


def clear_outbox() -> None:
    """Clear test/mock messages buffer."""
    _outbox.clear()


def _mask_token(token: str) -> str:
    if len(token) <= 8:
        return "***"
    return f"{token[:4]}...{token[-4:]}"


def send_password_reset_email(
    to_email: str,
    username: str,
    reset_token: str,
    base_url: str = "",
) -> bool:
    """Gửi email chứa liên kết và mã xác thực đặt lại mật khẩu một lần (TTL có hạn).

    Hỗ trợ gửi qua SMTP máy chủ hoặc ghi nhận vào mock outbox (khi tắt SMTP_ENABLED).
    """
    if not to_email or "@" not in to_email:
        logger.warning("Không thể gửi email đặt lại mật khẩu: địa chỉ email không hợp lệ.")
        return False

    minutes = config.RESET_TOKEN_EXPIRE_MINUTES
    clean_base = config.PUBLIC_BASE_URL or (base_url.rstrip("/") if base_url else "http://localhost:8000")
    reset_link = f"{clean_base}/#reset-token={reset_token}"

    subject = "[OpsMind Helpdesk] Hướng dẫn đặt lại mật khẩu tài khoản"
    body_text = (
        f"Xin chào {username},\n\n"
        f"Hệ thống OpsMind Helpdesk nhận được yêu cầu đặt lại mật khẩu cho tài khoản của bạn.\n\n"
        f"Mã xác thực của bạn (có hiệu lực trong {minutes} phút):\n"
        f"{reset_token}\n\n"
        f"Bạn cũng có thể mở liên kết sau để đặt mật khẩu mới trực tiếp:\n"
        f"{reset_link}\n\n"
        f"LƯU Ý BẢO MẬT:\n"
        f"- Không chia sẻ mã xác thực này cho bất kỳ ai, kể cả nhân viên hỗ trợ IT.\n"
        f"- Nếu bạn không gửi yêu cầu này, hãy bỏ qua email này hoặc liên hệ ngay với IT Security.\n\n"
        f"Trân trọng,\n"
        f"Bộ phận Hỗ trợ CNTT (IT Support Team)"
    )

    if not config.SMTP_ENABLED:
        msg_record = {
            "to": to_email,
            "username": username,
            "subject": subject,
            "body": body_text,
            "token": reset_token,
            "link": reset_link,
        }
        _outbox.append(msg_record)
        logger.info(
            "Mock email dispatched to %s for user %s (token: %s)",
            to_email,
            username,
            _mask_token(reset_token),
        )
        return True

    try:
        msg = EmailMessage()
        msg["Subject"] = subject
        msg["From"] = config.SMTP_FROM_EMAIL
        msg["To"] = to_email
        msg.set_content(body_text)

        smtp_cls = smtplib.SMTP_SSL if config.SMTP_PORT == 465 else smtplib.SMTP
        with smtp_cls(config.SMTP_HOST, config.SMTP_PORT, timeout=10.0) as server:
            if config.SMTP_USE_TLS and config.SMTP_PORT != 465:
                server.starttls()
            if config.SMTP_USER and config.SMTP_PASSWORD:
                server.login(config.SMTP_USER, config.SMTP_PASSWORD)
            server.send_message(msg)

        logger.info(
            "Password reset email sent successfully via SMTP to %s (user: %s)",
            to_email,
            username,
        )
        return True
    except Exception as exc:
        logger.error(
            "Failed to send password reset email via SMTP to %s: %s",
            to_email,
            exc,
        )
        return False
