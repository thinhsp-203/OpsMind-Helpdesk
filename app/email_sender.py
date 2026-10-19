from __future__ import annotations

from collections import deque
from email.header import Header
from email.mime.text import MIMEText
from email.utils import formatdate, make_msgid
import logging
import smtplib
import ssl
from typing import Any

import httpx

from app import config

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


def resolve_email_provider() -> str:
    """Xác định email provider đang kích hoạt:
    - Nếu EMAIL_PROVIDER được cấu hình cụ thể: 'smtp', 'resend', 'brevo', 'webhook', 'console'.
    - Nếu không: tự phát hiện theo biến môi trường có sẵn:
        1. resend (nếu có RESEND_API_KEY)
        2. brevo (nếu có BREVO_API_KEY)
        3. smtp (nếu SMTP_ENABLED=True)
        4. console (fallback mặc định cho local dev/test)
    """
    configured = (config.EMAIL_PROVIDER or "").lower()
    if configured:
        return configured
    if config.RESEND_API_KEY:
        return "resend"
    if config.BREVO_API_KEY:
        return "brevo"
    if config.SMTP_ENABLED:
        return "smtp"
    return "console"


def get_email_status() -> dict[str, Any]:
    """Trả về trạng thái cấu hình dịch vụ email (đã che thông tin nhạy cảm)."""
    provider = resolve_email_provider()
    from_email = config.EMAIL_FROM

    if provider == "smtp":
        target = f"{config.SMTP_HOST}:{config.SMTP_PORT}"
        enabled = config.SMTP_ENABLED
    elif provider == "resend":
        key = config.RESEND_API_KEY
        target = f"Resend API (...{key[-4:]})" if len(key) >= 4 else "Resend API"
        enabled = bool(key)
    elif provider == "brevo":
        key = config.BREVO_API_KEY
        target = f"Brevo API (...{key[-4:]})" if len(key) >= 4 else "Brevo API"
        enabled = bool(key)
    elif provider == "webhook":
        target = (
            f"...{config.EMAIL_WEBHOOK_URL[-12:]}"
            if len(config.EMAIL_WEBHOOK_URL) >= 12
            else (config.EMAIL_WEBHOOK_URL or "Chưa cấu hình")
        )
        enabled = bool(config.EMAIL_WEBHOOK_URL)
    else:
        target = "Mock Outbox (In-Memory)"
        enabled = True

    return {
        "provider": provider,
        "enabled": enabled,
        "from_email": from_email,
        "target": target,
        "is_mock": provider == "console" or (provider == "smtp" and not config.SMTP_ENABLED),
    }


def _send_via_smtp(to_email: str, subject: str, body_text: str) -> bool:
    from_addr = config.EMAIL_FROM
    domain = from_addr.split("@")[-1] if "@" in from_addr else "opsmind.internal"

    msg = MIMEText(body_text, "plain", "utf-8")
    msg["Subject"] = Header(subject, "utf-8")
    msg["From"] = from_addr
    msg["To"] = to_email
    msg["Date"] = formatdate(localtime=True)
    msg["Message-ID"] = make_msgid(domain=domain)

    smtp_cls = smtplib.SMTP_SSL if config.SMTP_PORT == 465 else smtplib.SMTP
    ssl_context = ssl.create_default_context()
    if not config.SMTP_SSL_VERIFY:
        ssl_context.check_hostname = False
        ssl_context.verify_mode = ssl.CERT_NONE

    if config.SMTP_PORT == 465:
        with smtp_cls(config.SMTP_HOST, config.SMTP_PORT, timeout=10.0, context=ssl_context) as server:
            if config.SMTP_USER and config.SMTP_PASSWORD:
                server.login(config.SMTP_USER, config.SMTP_PASSWORD)
            server.send_message(msg)
    else:
        with smtp_cls(config.SMTP_HOST, config.SMTP_PORT, timeout=10.0) as server:
            if config.SMTP_USE_TLS:
                server.starttls(context=ssl_context)
            if config.SMTP_USER and config.SMTP_PASSWORD:
                server.login(config.SMTP_USER, config.SMTP_PASSWORD)
            server.send_message(msg)
    return True


def _send_via_resend(to_email: str, subject: str, body_text: str) -> bool:
    api_key = config.RESEND_API_KEY
    if not api_key:
        logger.error("RESEND_API_KEY is not configured.")
        return False
    from_addr = config.EMAIL_FROM
    if not from_addr or "opsmind.internal" in from_addr:
        from_addr = "onboarding@resend.dev"

    html_content = f"<div style='font-family: sans-serif; font-size: 14px; line-height: 1.6; color: #1e293b;'>{body_text.replace(chr(10), '<br>')}</div>"
    resp = httpx.post(
        "https://api.resend.com/emails",
        headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
        json={
            "from": from_addr,
            "to": [to_email],
            "subject": subject,
            "text": body_text,
            "html": html_content,
        },
        timeout=10.0,
    )
    if resp.is_success:
        return True
    logger.error("Resend API failed: %s - %s", resp.status_code, resp.text)
    return False


def _send_via_brevo(to_email: str, subject: str, body_text: str) -> bool:
    api_key = config.BREVO_API_KEY
    if not api_key:
        logger.error("BREVO_API_KEY is not configured.")
        return False
    from_addr = config.EMAIL_FROM
    resp = httpx.post(
        "https://api.brevo.com/v3/smtp/email",
        headers={"api-key": api_key, "Content-Type": "application/json"},
        json={
            "sender": {"email": from_addr},
            "to": [{"email": to_email}],
            "subject": subject,
            "textContent": body_text,
        },
        timeout=10.0,
    )
    if resp.is_success:
        return True
    logger.error("Brevo API failed: %s - %s", resp.status_code, resp.text)
    return False


def _send_via_webhook(to_email: str, subject: str, body_text: str) -> bool:
    url = config.EMAIL_WEBHOOK_URL
    if not url:
        logger.error("EMAIL_WEBHOOK_URL is not configured.")
        return False
    resp = httpx.post(
        url,
        json={"to": to_email, "subject": subject, "text": body_text, "from": config.EMAIL_FROM},
        timeout=10.0,
    )
    return resp.is_success


def dispatch_email(
    to_email: str,
    subject: str,
    body_text: str,
    extra_record: dict[str, Any] | None = None,
) -> bool:
    """Gửi email cốt lõi theo provider đã cấu hình hoặc ghi nhận vào mock outbox."""
    if not to_email or "@" not in to_email:
        logger.warning("Không thể gửi email: địa chỉ email không hợp lệ: %s", to_email)
        return False

    provider = resolve_email_provider()

    if provider == "console" or (provider == "smtp" and not config.SMTP_ENABLED):
        rec = {
            "to": to_email,
            "subject": subject,
            "body": body_text,
            "provider": provider,
        }
        if extra_record:
            rec.update(extra_record)
        _outbox.append(rec)
        logger.info("Mock email dispatched to %s with subject: %s", to_email, subject)
        return True

    try:
        if provider == "smtp":
            ok = _send_via_smtp(to_email, subject, body_text)
        elif provider == "resend":
            ok = _send_via_resend(to_email, subject, body_text)
        elif provider == "brevo":
            ok = _send_via_brevo(to_email, subject, body_text)
        elif provider == "webhook":
            ok = _send_via_webhook(to_email, subject, body_text)
        else:
            logger.warning("Unknown EMAIL_PROVIDER: %s. Falling back to mock outbox.", provider)
            _outbox.append({"to": to_email, "subject": subject, "body": body_text})
            return True

        if ok:
            logger.info("Email sent successfully via %s to %s", provider, to_email)
        return ok
    except Exception as exc:
        logger.error("Failed to send email via %s to %s: %s", provider, to_email, exc)
        return False


def send_password_reset_email(
    to_email: str,
    username: str,
    reset_token: str,
    base_url: str = "",
) -> bool:
    """Gửi email chứa liên kết và mã xác thực đặt lại mật khẩu một lần (TTL có hạn)."""
    if not to_email or "@" not in to_email:
        logger.warning("Không thể gửi email đặt lại mật khẩu: địa chỉ email không hợp lệ.")
        return False

    if not config.DEMO_MODE and not config.PUBLIC_BASE_URL:
        logger.error(
            "PUBLIC_BASE_URL is not configured in non-demo environment. Refusing to send reset email with untrusted host."
        )
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

    extra = {
        "type": "password_reset",
        "username": username,
        "token": reset_token,
        "link": reset_link,
    }
    return dispatch_email(to_email, subject, body_text, extra_record=extra)


def send_account_created_email(
    to_email: str,
    username: str,
    temp_password: str,
    base_url: str = "",
    force_change: bool = True,
) -> bool:
    """Gửi email thông báo tài khoản mới được tạo và mật khẩu tạm kèm yêu cầu đổi mật khẩu."""
    if not to_email or "@" not in to_email:
        logger.warning("Không thể gửi email tài khoản mới: địa chỉ email không hợp lệ.")
        return False

    clean_base = config.PUBLIC_BASE_URL or (base_url.rstrip("/") if base_url else "http://localhost:8000")
    login_link = f"{clean_base}/"

    subject = "[OpsMind Helpdesk] Thông tin tài khoản cổng hỗ trợ CNTT"
    force_note = (
        "\nLƯU Ý QUAN TRỌNG: Bạn được yêu cầu đổi mật khẩu ngay trong lần đăng nhập đầu tiên để đảm bảo an toàn bảo mật."
        if force_change
        else ""
    )
    body_text = (
        f"Xin chào {username},\n\n"
        f"Tài khoản của bạn trên hệ thống OpsMind Helpdesk đã được khởi tạo thành công.\n\n"
        f"Thông tin đăng nhập:\n"
        f"- Cổng truy cập: {login_link}\n"
        f"- Tên đăng nhập: {username}\n"
        f"- Mật khẩu tạm thời: {temp_password}\n"
        f"{force_note}\n\n"
        f"Trân trọng,\n"
        f"Bộ phận Hỗ trợ CNTT (IT Support Team)"
    )

    extra = {
        "type": "account_created",
        "username": username,
        "temp_password": temp_password,
        "link": login_link,
    }
    return dispatch_email(to_email, subject, body_text, extra_record=extra)


def send_test_email(to_email: str) -> tuple[bool, str]:
    """Gửi email kiểm tra kết nối dành cho Quản trị viên."""
    if not to_email or "@" not in to_email:
        return False, "Địa chỉ email nhận thử nghiệm không hợp lệ."

    provider = resolve_email_provider()
    subject = "[OpsMind Helpdesk] Kiểm tra cấu hình dịch vụ Email"
    body_text = (
        f"Xin chào Quản trị viên,\n\n"
        f"Đây là email thử nghiệm gửi từ hệ thống OpsMind Helpdesk.\n"
        f"- Phương thức gửi (Provider): {provider.upper()}\n"
        f"- Thời gian gửi: {formatdate(localtime=True)}\n\n"
        f"Nếu bạn nhận được email này, kênh gửi email đã được thiết lập thành công và sẵn sàng phục vụ."
    )
    ok = dispatch_email(to_email, subject, body_text)
    if ok:
        return True, f"Đã gửi email thử nghiệm thành công qua {provider.upper()} tới {to_email}."
    return False, f"Không thể gửi email qua {provider.upper()}. Vui lòng kiểm tra lại cấu hình biến môi trường và log máy chủ."
