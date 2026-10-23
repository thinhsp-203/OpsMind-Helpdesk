"""Khung kênh thông báo đa nền tảng (Telegram) cho OpsMind Helpdesk.

Hỗ trợ:
- Gửi thông báo sự cố mới tới Telegram Bot.
- Cơ chế phòng vệ SSRF: Chỉ cho phép kết nối tới tên miền chính thức của Telegram.
- Bảo mật thông tin xác thực: Không in Bot Token hoặc Webhook Secret trong log khi xảy ra lỗi.
"""

from __future__ import annotations

import contextlib
from datetime import datetime, timezone
import json
import logging
import os
import re
from typing import Any
import urllib.error
from urllib.parse import urlparse
from urllib.request import Request, urlopen

logger = logging.getLogger(__name__)

# Danh sách sự kiện thông báo gần đây (In-memory audit log)
NOTIFICATION_HISTORY: list[dict[str, Any]] = []


def record_notification_event(
    channel: str,
    event_type: str,
    recipient: str,
    status: str,
    status_label: str,
    message: str = "",
) -> None:
    channel_labels = {
        "telegram": "Telegram Bot",
        "discord": "Discord (đã ngừng sử dụng)",
        "email": "Dịch vụ Email",
        "system": "Hệ thống",
    }
    NOTIFICATION_HISTORY.insert(
        0,
        {
            "id": len(NOTIFICATION_HISTORY) + 1,
            "timestamp": datetime.now(timezone.utc).strftime("%H:%M:%S %d/%m/%Y"),
            "channel": channel,
            "channel_label": channel_labels.get(channel, channel.capitalize()),
            "event_type": event_type,
            "recipient": recipient,
            "status": status,
            "status_label": status_label,
            "message": message,
        },
    )
    if len(NOTIFICATION_HISTORY) > 50:
        NOTIFICATION_HISTORY.pop()


def get_notification_history() -> list[dict[str, Any]]:
    from app.notification_outbox import list_deliveries
    labels = {
        'pending': 'Pending retry', 'processing': 'Processing',
        'accepted': 'Provider accepted',
        'failed': 'Failed; review required', 'not_configured': 'Not configured',
        'config_changed': 'Config changed; review required',
    }
    persisted = [{
        'id': row['id'], 'channel': row['channel'], 'channel_label': row['channel'],
        'event_type': f"Ticket #{row['ticket_id']} — {row['event_type']}",
        'recipient': 'Not configured' if row['status'] == 'not_configured' else 'Channel snapshot',
        'timestamp': datetime.fromtimestamp(row['updated_at'], timezone.utc).isoformat(),
        'status': 'success' if row['status'] == 'accepted' else row['status'],
        'status_label': labels[row['status']],
        'message': f"Event {row['event_id']} | attempts {row['attempts']}/{row['max_attempts']} | {row['last_error']} | Staff acknowledgement unknown",
    } for row in list_deliveries()]
    return persisted + list(NOTIFICATION_HISTORY)

# Danh sách tên miền được phép gửi thông báo (phòng vệ SSRF)
ALLOWED_TELEGRAM_DOMAINS = {"api.telegram.org"}

PRIORITY_NAMES_VI = {
    "low": "Thấp",
    "medium": "Trung bình",
    "high": "Cao",
    "urgent": "Khẩn cấp",
}

def _is_safe_url(url: str, allowed_domains: set[str]) -> bool:
    """Kiểm tra URL hợp lệ và chống tấn công SSRF."""
    try:
        parsed = urlparse(url.strip())
        if parsed.scheme.lower() != "https":
            return False
        hostname = (parsed.hostname or "").lower()
        if not hostname:
            return False
        # Chặn localhost và dải IP nội bộ
        if hostname in {"localhost", "127.0.0.1", "0.0.0.0", "::1"}:  # noqa: S104
            return False
        if re.match(r"^(10\.|172\.(1[6-9]|2[0-9]|3[0-1])\.|192\.168\.|169\.254\.)", hostname):
            return False
        return hostname in allowed_domains or any(hostname.endswith("." + d) for d in allowed_domains)
    except Exception:
        return False


def notify_telegram_result(
    ticket: dict, bot_token: str | None = None, chat_id: str | None = None
) -> tuple[bool, str]:
    """Gửi thông báo tạo ticket mới tới nhóm Telegram kèm thông báo chi tiết."""
    token = (bot_token or os.environ.get("TELEGRAM_BOT_TOKEN", "")).strip().strip("'\"")
    target_chat = (chat_id or os.environ.get("TELEGRAM_CHAT_ID", "")).strip().strip("'\"")

    if not token or not target_chat:
        return False, "Chưa cấu hình TELEGRAM_BOT_TOKEN hoặc TELEGRAM_CHAT_ID."

    api_url = f"https://api.telegram.org/bot{token}/sendMessage"
    if not _is_safe_url(api_url, ALLOWED_TELEGRAM_DOMAINS):
        logger.warning("Telegram: URL không an toàn hoặc vi phạm chính sách miền.")
        return False, "URL Telegram Bot không hợp lệ hoặc vi phạm chính sách bảo mật."

    def field(name: str, limit: int = 200) -> str:
        return " ".join(str(ticket.get(name, "—")).split())[:limit]

    prio_raw = str(ticket.get("priority", "medium")).lower()
    prio_vi = PRIORITY_NAMES_VI.get(prio_raw, prio_raw.title())
    is_test = str(ticket.get("id")) == "TEST"

    event_label = "Ticket được chuyển cấp" if ticket.get("notification_event") == "escalated" else "Có yêu cầu hỗ trợ mới"
    if is_test:
        text = (
            "🔔 [OpsMind Helpdesk] Kiểm tra kết nối Telegram Bot\n\n"
            "Hệ thống kiểm tra kết nối cảnh báo tự động thành công.\n"
            f"🕒 Thời gian: {field('created_at', 50)}"
        )
    else:
        text = (
            f"🔔 [OpsMind Helpdesk] {event_label}\n\n"
            f"Sự kiện: {field('notification_event_id', 40)}\n"
            f"🎫 Mã sự cố: #{field('id', 30)}\n"
            f"📌 Tiêu đề: {field('title')}\n"
            f"👤 Người yêu cầu: {field('requester', 80)}\n"
            f"⚡ Mức ưu tiên: {prio_vi}\n"
            f"📂 Danh mục: {field('category', 80)}\n"
            f"🕒 Thời gian tạo: {field('created_at', 50)}\n"
            f"⏳ Hạn xử lý (SLA): {field('sla_deadline', 50)}\n\n"
            "Vui lòng truy cập hệ thống để tiếp nhận và xử lý sự cố."
        )

    try:
        req = Request(  # noqa: S310 -- Đã kiểm tra _is_safe_url
            api_url,
            data=json.dumps({"chat_id": target_chat, "text": text}).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urlopen(req, timeout=10) as response:  # noqa: S310 -- Đã kiểm tra _is_safe_url
            res_data = json.load(response)
        if res_data.get("ok"):
            logger.info("Telegram: Gửi thông báo thành công cho Ticket #%s.", ticket.get("id"))
            return True, "Gửi thông báo tới nhóm Telegram thành công."
        desc = res_data.get("description", "Máy chủ Telegram trả về lỗi.")
        logger.warning("Telegram: Máy chủ trả về lỗi: %s", desc)
        return False, f"Lỗi từ Telegram API: {desc}"
    except urllib.error.HTTPError as exc:
        err_body = ""
        with contextlib.suppress(Exception):
            err_body = exc.read().decode("utf-8", errors="replace")
        logger.warning("Telegram: Máy chủ Telegram trả về lỗi HTTP %s: %s", exc.code, err_body[:200])
        if exc.code == 400:
            return False, "Lỗi HTTP 400: Chat ID không hợp lệ hoặc Bot chưa được thêm vào nhóm."
        if exc.code == 401:
            return False, "Lỗi HTTP 401: Bot Token không hợp lệ."
        return False, f"Lỗi HTTP {exc.code} từ máy chủ Telegram."
    except Exception as exc:
        logger.warning("Telegram: Không thể gửi thông báo tới nhóm (%s).", type(exc).__name__)
        return False, f"Lỗi kết nối mạng: {type(exc).__name__}."


def notify_telegram(ticket: dict, bot_token: str | None = None, chat_id: str | None = None) -> bool:
    """Gửi thông báo tạo ticket mới tới nhóm Telegram."""
    ok, _ = notify_telegram_result(ticket, bot_token, chat_id)
    return ok


def dispatch_ticket_notification(ticket: dict) -> dict[str, bool]:
    """Phát thông báo sự cố mới tới toàn bộ các kênh đã cấu hình."""
    results = {}
    prio = ticket.get("priority", "medium")
    prio_vi = PRIORITY_NAMES_VI.get(prio, prio.upper())
    title = ticket.get("title", "Sự cố CNTT")
    ticket_id = ticket.get("id", "Mới")

    if os.environ.get("TELEGRAM_BOT_TOKEN") and os.environ.get("TELEGRAM_CHAT_ID"):
        ok = notify_telegram(ticket)
        results["telegram"] = ok
        record_notification_event(
            "telegram",
            f"Ticket #{ticket_id} ({prio_vi})",
            "Telegram IT Alert",
            "success" if ok else "error",
            "Đã phát" if ok else "Lỗi gửi",
            title,
        )
    return results


def send_test_notification_result(channel: str, target_email: str = "") -> tuple[bool, str]:
    """Gửi thông báo kiểm tra kết nối tới kênh được chỉ định kèm thông báo chi tiết."""
    test_ticket = {
        "id": "TEST",
        "title": "Kiểm tra kết nối kênh thông báo tự động",
        "description": "Đây là tin nhắn thử nghiệm gửi từ hệ thống OpsMind Helpdesk để xác nhận tích hợp hoạt động bình thường.",
        "category": "system",
        "priority": "low",
        "requester": "system_admin",
        "created_at": "Vừa xong",
        "sla_deadline": "Không áp dụng",
    }
    if channel == "telegram":
        token = os.environ.get("TELEGRAM_BOT_TOKEN", "").strip().strip("'\"")
        chat_id = os.environ.get("TELEGRAM_CHAT_ID", "").strip().strip("'\"")
        if not token:
            record_notification_event(
                "telegram",
                "Thử nghiệm Telegram",
                "Telegram Group",
                "error",
                "Chưa cấu hình",
                "Thiếu biến môi trường TELEGRAM_BOT_TOKEN.",
            )
            return False, "Không thể gửi thông báo: Chưa cấu hình biến môi trường TELEGRAM_BOT_TOKEN trên Render."
        if not chat_id:
            record_notification_event(
                "telegram",
                "Thử nghiệm Telegram",
                "Telegram Group",
                "error",
                "Chưa cấu hình",
                "Thiếu biến môi trường TELEGRAM_CHAT_ID.",
            )
            return False, "Không thể gửi thông báo: Chưa cấu hình biến môi trường TELEGRAM_CHAT_ID trên Render."
        ok, msg = notify_telegram_result(test_ticket, token, chat_id)
        if ok:
            record_notification_event(
                "telegram",
                "Thử nghiệm Telegram",
                f"...{chat_id[-4:]}" if len(chat_id) >= 4 else "Telegram Group",
                "success",
                "Thành công",
                msg,
            )
            return True, msg
        record_notification_event(
            "telegram",
            "Thử nghiệm Telegram",
            "Telegram Group",
            "error",
            "Lỗi kết nối",
            msg,
        )
        return False, f"Không thể gửi thông báo: {msg}"
    if channel == "email":
        from app import email_sender, config
        target = target_email.strip() or config.EMAIL_FROM or "admin@example.com"
        ok, msg = email_sender.send_test_email(target)
        record_notification_event(
            "email",
            "Email thử nghiệm",
            target,
            "success" if ok else "error",
            "Thành công" if ok else "Thất bại",
            msg,
        )
        return ok, msg
    return False, f"Kênh thông báo '{channel}' không được hỗ trợ."


def send_test_notification(channel: str, target_email: str = "") -> bool:
    """Gửi thông báo kiểm tra kết nối tới kênh được chỉ định (Dành cho Admin)."""
    ok, _ = send_test_notification_result(channel, target_email)
    return ok


def get_notification_channels_status() -> dict[str, dict[str, Any]]:
    """Trả về trạng thái bật/tắt của các kênh thông báo (ẩn token nhạy cảm)."""
    from app import email_sender

    tg_token = os.environ.get("TELEGRAM_BOT_TOKEN", "").strip().strip("'\"")
    tg_chat = os.environ.get("TELEGRAM_CHAT_ID", "").strip().strip("'\"")

    masked_chat = f"...{tg_chat[-4:]}" if len(tg_chat) >= 4 else ("Bật" if tg_chat else "Chưa cấu hình")

    return {
        "telegram": {
            "enabled": bool(tg_token and tg_chat),
            "target": masked_chat,
        },
        "email": email_sender.get_email_status(),
        "history": get_notification_history(),
    }
