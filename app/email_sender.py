from __future__ import annotations

from collections import deque
from email.header import Header
from email.mime.text import MIMEText
from email.utils import formatdate, make_msgid, parseaddr
import html
import logging
import smtplib
import ssl
from typing import Any
from urllib.parse import urlsplit

import httpx

from app import config

logger = logging.getLogger(__name__)

# Bounded outbox buffer for mock/testing inspection (limited to 50 records)
_outbox: deque[dict[str, Any]] = deque(maxlen=50)
_last_send_error: str = ""


def get_last_send_error() -> str:
    """Trả về chi tiết lỗi gửi email gần nhất nếu có."""
    return _last_send_error


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


_VALID_EMAIL_PROVIDERS = frozenset({"smtp", "resend", "brevo", "webhook", "console", "mock"})


def resolve_email_provider() -> str:
    """Xác định email provider đang kích hoạt:
    - Nếu EMAIL_PROVIDER được cấu hình cụ thể: 'smtp', 'resend', 'brevo', 'webhook', 'console'.
    - Nếu không: tự phát hiện theo biến môi trường có sẵn:
        1. resend (nếu có RESEND_API_KEY)
        2. brevo (nếu có BREVO_API_KEY)
        3. smtp (nếu SMTP_ENABLED=True)
        4. console (fallback mặc định cho local dev/test)

    Raises:
        ValueError: Nếu EMAIL_PROVIDER được đặt thành tên không hợp lệ (typo).
            Giá trị hợp lệ: smtp, resend, brevo, webhook, console.
            AUD-16: Validates enum to prevent silent mock fallback on misconfiguration.
    """
    configured = (config.EMAIL_PROVIDER or "").lower()
    if configured:
        # AUD-16: Reject unknown/typo'd provider names — do NOT silently fall back to mock.
        if configured not in _VALID_EMAIL_PROVIDERS:
            raise ValueError(
                f"EMAIL_PROVIDER='{configured}' is not a recognised provider. "
                f"Valid values: {', '.join(sorted(_VALID_EMAIL_PROVIDERS))}. "
                "Check for typos (e.g. 'smpt' instead of 'smtp')."
            )
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
        enabled = bool(config.SMTP_ENABLED and config.SMTP_HOST and 0 < config.SMTP_PORT < 65536)
    elif provider == "resend":
        key = config.RESEND_API_KEY
        target = f"Resend API (...{key[-4:]})" if len(key) >= 4 else "Resend API"
        enabled = bool(key)
    elif provider == "brevo":
        key = config.BREVO_API_KEY
        target = f"Brevo API (...{key[-4:]})" if len(key) >= 4 else "Brevo API"
        enabled = bool(key)
    elif provider == "webhook":
        target = "Webhook (configured)" if config.EMAIL_WEBHOOK_URL else "Not configured"
        enabled = bool(config.EMAIL_WEBHOOK_URL)
    else:
        target = "Mock Outbox (In-Memory)"
        enabled = True

    return {
        "provider": provider,
        "enabled": enabled,
        "from_email": from_email,
        "target": target,
        "is_mock": provider in ("console", "mock"),
    }


class EmailConfigurationError(ValueError):
    """Invalid email configuration; no network call has been attempted."""


def validate_email_configuration() -> dict[str, Any]:
    try:
        status = get_email_status()
    except ValueError as exc:
        raise EmailConfigurationError(str(exc)) from exc
    if not status['enabled']:
        raise EmailConfigurationError('Email provider is not configured')
    if status['is_mock']:
        if not config.DEMO_MODE:
            raise EmailConfigurationError('A real email provider is required outside DEMO_MODE')
        return status
    sender = parseaddr(config.EMAIL_FROM)[1]
    if '@' not in sender or any(c in config.EMAIL_FROM for c in ('\r','\n')):
        raise EmailConfigurationError('EMAIL_FROM must be a valid sender')
    if status['provider']=='webhook':
        try:
            endpoint = urlsplit(config.EMAIL_WEBHOOK_URL)
        except ValueError as exc:
            raise EmailConfigurationError('Invalid email webhook URL') from exc
        if endpoint.scheme!='https' or not endpoint.hostname or endpoint.username or endpoint.password or endpoint.fragment:
            raise EmailConfigurationError('Email webhook requires an HTTPS URL without user info or fragment')
    if not config.DEMO_MODE:
        try:
            base = urlsplit(config.PUBLIC_BASE_URL)
        except ValueError as exc:
            raise EmailConfigurationError('Invalid PUBLIC_BASE_URL') from exc
        if base.scheme!='https' or not base.hostname or base.username or base.password or base.query or base.fragment:
            raise EmailConfigurationError('PUBLIC_BASE_URL requires a trusted HTTPS base URL')
        if status['provider']=='smtp' and (not config.SMTP_SSL_VERIFY or (config.SMTP_PORT!=465 and not config.SMTP_USE_TLS)):
            raise EmailConfigurationError('Production SMTP requires verified TLS')
    return status


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
            refused = server.send_message(msg)
    else:
        with smtp_cls(config.SMTP_HOST, config.SMTP_PORT, timeout=10.0) as server:
            if config.SMTP_USE_TLS:
                server.starttls(context=ssl_context)
            if config.SMTP_USER and config.SMTP_PASSWORD:
                server.login(config.SMTP_USER, config.SMTP_PASSWORD)
            refused = server.send_message(msg)
    return refused == {}


def _send_via_resend(to_email: str, subject: str, body_text: str) -> bool:
    global _last_send_error
    api_key = config.RESEND_API_KEY
    if not api_key:
        _last_send_error = "RESEND_API_KEY chưa được cấu hình."
        logger.error(_last_send_error)
        return False
    from_addr = config.EMAIL_FROM
    if not from_addr or "opsmind.internal" in from_addr:
        from_addr = "onboarding@resend.dev"

    safe_body = html.escape(body_text).replace("\n", "<br>")
    html_content = f"<div style='font-family: sans-serif; font-size: 14px; line-height: 1.6; color: #1e293b;'>{safe_body}</div>"
    try:
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
            _last_send_error = ""
            return True
        _last_send_error = "Resend provider rejected request (HTTP " + str(resp.status_code) + ")"
        logger.error("Resend provider rejected request: HTTP %s", resp.status_code)
        return False
    except Exception as exc:
        _last_send_error = "Resend provider exception: " + type(exc).__name__
        logger.error(_last_send_error)
        return False


def _send_via_brevo(to_email: str, subject: str, body_text: str) -> bool:
    global _last_send_error
    api_key = config.BREVO_API_KEY
    if not api_key:
        _last_send_error = "BREVO_API_KEY chưa được cấu hình."
        logger.error(_last_send_error)
        return False
    from_addr = config.EMAIL_FROM
    sender_name, sender_email = parseaddr(from_addr)
    if not sender_email:
        sender_email = from_addr
    sender_payload: dict[str, str] = {"email": sender_email}
    if sender_name:
        sender_payload["name"] = sender_name

    safe_body = html.escape(body_text).replace("\n", "<br>")
    html_content = f"<div style='font-family: sans-serif; font-size: 14px; line-height: 1.6; color: #1e293b;'>{safe_body}</div>"

    try:
        resp = httpx.post(
            "https://api.brevo.com/v3/smtp/email",
            headers={"api-key": api_key, "Content-Type": "application/json"},
            json={
                "sender": sender_payload,
                "to": [{"email": to_email}],
                "subject": subject,
                "textContent": body_text,
                "htmlContent": html_content,
            },
            timeout=10.0,
        )
        if resp.is_success:
            _last_send_error = ""
            return True
        _last_send_error = "Brevo provider rejected request (HTTP " + str(resp.status_code) + ")"
        logger.error("Brevo provider rejected request: HTTP %s", resp.status_code)
        return False
    except Exception as exc:
        _last_send_error = "Brevo provider exception: " + type(exc).__name__
        logger.error(_last_send_error)
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

    # AUD-16: resolve_email_provider raises ValueError for unknown/typo'd providers.
    # Catch it so dispatch_email returns False (not raises) on misconfiguration.
    global _last_send_error
    try:
        status = validate_email_configuration()
        provider = status["provider"]
        _last_send_error = ""
    except ValueError as cfg_err:
        _last_send_error = str(cfg_err)
        logger.error("Email dispatch aborted — invalid EMAIL_PROVIDER: %s", cfg_err)
        return False

    if provider in ("console", "mock"):
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
            # AUD-16: This branch is unreachable: resolve_email_provider() already
            # raised ValueError for any unknown provider. Guard kept for defense-in-depth.
            _last_send_error = f"EMAIL_PROVIDER='{provider}' is not a recognised provider."
            logger.error(
                "Unknown EMAIL_PROVIDER: %s. Refusing to send — no silent mock fallback.",
                provider,
            )
            return False

        if ok:
            logger.info("Email request accepted by provider %s", provider)
        return ok
    except Exception as exc:
        _last_send_error = "Provider exception: " + type(exc).__name__
        logger.error("Email provider %s failed: %s", provider, type(exc).__name__)
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
    reset_token: str,
    base_url: str = "",
    force_change: bool = True,
) -> bool:
    """Send a one-use password setup link, never an account password."""
    if not to_email or '@' not in to_email:
        return False
    clean_base = config.PUBLIC_BASE_URL or base_url.rstrip('/')
    link = f"{clean_base}/#reset-token={reset_token}"
    note = "Bạn cần đổi mật khẩu ngay trong lần đăng nhập đầu tiên.\n" if force_change else ""
    body = (f"Xin chào {username},\n\nTài khoản OpsMind Helpdesk của bạn đã được tạo.\n"
            f"Tên đăng nhập: {username}\n"
            f"Dùng liên kết một lần để đặt mật khẩu (có hiệu lực tối đa {config.RESET_TOKEN_EXPIRE_MINUTES} phút):\n"
            f"{link}\n\n{note}Không chia sẻ liên kết này. Nếu không mong đợi thư này, hãy liên hệ IT.")
    return dispatch_email(to_email, '[OpsMind Helpdesk] Thiết lập mật khẩu tài khoản', body,
                          extra_record={'type':'account_created','username':username,'token':reset_token,'link':link})


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
        if provider in {'console','mock'}:
            return True, "Đã ghi nhận thư thử trong DEMO outbox; không gửi email thật."
        return True, "Provider đã chấp nhận yêu cầu gửi email; chưa xác nhận phát thư."
    err_detail = _last_send_error or "Vui lòng kiểm tra lại cấu hình biến môi trường và log máy chủ."
    return False, f"Không thể gửi email qua {provider.upper()}: {err_detail}"
