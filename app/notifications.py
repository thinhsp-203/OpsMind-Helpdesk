"""Khung kênh thông báo đa nền tảng (Telegram & Discord Webhook) cho OpsMind Helpdesk.

Hỗ trợ:
- Gửi thông báo sự cố mới tới Telegram Bot và Discord Webhook.
- Cơ chế phòng vệ SSRF: Chỉ cho phép kết nối tới tên miền chính thức của Telegram và Discord.
- Bảo mật thông tin xác thực: Không in Bot Token hoặc Webhook Secret trong log khi xảy ra lỗi.
"""

from __future__ import annotations

from datetime import datetime, timezone
import json
import logging
import os
import re
from typing import Any
from urllib.parse import urlparse
from urllib.request import Request, urlopen

logger = logging.getLogger(__name__)

# Danh sách sự kiện thông báo gần đây (In-memory audit log)
NOTIFICATION_HISTORY: list[dict[str, Any]] = [
    {
        "id": 1,
        "timestamp": datetime.now(timezone.utc).strftime("%H:%M:%S %d/%m/%Y"),
        "channel": "system",
        "channel_label": "Hệ thống",
        "event_type": "Khởi động trung tâm thông báo",
        "recipient": "Telegram • Discord • Email",
        "status": "active",
        "status_label": "Đang hoạt động",
        "message": "Các kênh thông báo sự cố IT sẵn sàng tiếp nhận sự kiện.",
    },
    {
        "id": 2,
        "timestamp": datetime.now(timezone.utc).strftime("%H:%M:%S %d/%m/%Y"),
        "channel": "email",
        "channel_label": "Dịch vụ Email",
        "event_type": "Hộp thư hệ thống (Mock Outbox)",
        "recipient": "noreply@opsmind.internal",
        "status": "active",
        "status_label": "Sẵn sàng",
        "message": "Hỗ trợ lưu trữ thông báo và đặt lại mật khẩu người dùng.",
    },
]


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
        "discord": "Discord Webhook",
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
    return list(NOTIFICATION_HISTORY)

# Danh sách tên miền được phép gửi thông báo (phòng vệ SSRF)
ALLOWED_TELEGRAM_DOMAINS = {"api.telegram.org"}
ALLOWED_DISCORD_DOMAINS = {"discord.com", "discordapp.com"}

PRIORITY_NAMES_VI = {
    "low": "Thấp",
    "medium": "Trung bình",
    "high": "Cao",
    "urgent": "Khẩn cấp",
}

# Màu sắc Discord Embed theo mức độ ưu tiên
DISCORD_PRIORITY_COLORS = {
    "urgent": 0xE74C3C,  # Đỏ
    "high": 0xE67E22,    # Cam
    "medium": 0xF1C40F,  # Vàng
    "low": 0x2ECC71,     # Xanh lục
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


def notify_telegram(ticket: dict, bot_token: str | None = None, chat_id: str | None = None) -> bool:
    """Gửi thông báo tạo ticket mới tới nhóm Telegram."""
    token = (bot_token or os.environ.get("TELEGRAM_BOT_TOKEN", "")).strip()
    target_chat = (chat_id or os.environ.get("TELEGRAM_CHAT_ID", "")).strip()

    if not token or not target_chat:
        return False

    api_url = f"https://api.telegram.org/bot{token}/sendMessage"
    if not _is_safe_url(api_url, ALLOWED_TELEGRAM_DOMAINS):
        logger.warning("Telegram: URL không an toàn hoặc vi phạm chính sách miền.")
        return False

    def field(name: str, limit: int = 200) -> str:
        return " ".join(str(ticket.get(name, "—")).split())[:limit]

    prio_raw = str(ticket.get("priority", "medium")).lower()
    prio_vi = PRIORITY_NAMES_VI.get(prio_raw, prio_raw.title())

    text = (
        "🔔 [OpsMind Helpdesk] Có yêu cầu hỗ trợ mới\n\n"
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
        with urlopen(req, timeout=8) as response:  # noqa: S310 -- Đã kiểm tra _is_safe_url
            res_data = json.load(response)
        if res_data.get("ok"):
            logger.info("Telegram: Gửi thông báo thành công cho Ticket #%s.", ticket.get("id"))
            return True
        logger.warning("Telegram: Máy chủ trả về lỗi khi gửi thông báo.")
        return False
    except Exception:
        # Không in nội dung exception để tránh lộ bot token trong log
        logger.warning("Telegram: Không thể gửi thông báo tới nhóm (ticket vẫn được lưu an toàn).")
        return False


def notify_discord(ticket: dict, webhook_url: str | None = None) -> bool:
    """Gửi thông báo tạo ticket mới tới kênh Discord qua Webhook."""
    url = (webhook_url or os.environ.get("DISCORD_WEBHOOK_URL", "")).strip()
    if not url:
        return False

    if not _is_safe_url(url, ALLOWED_DISCORD_DOMAINS):
        logger.warning("Discord: Webhook URL không an toàn hoặc vi phạm chính sách miền.")
        return False

    def field(name: str, limit: int = 200) -> str:
        return " ".join(str(ticket.get(name, "—")).split())[:limit]

    prio_raw = str(ticket.get("priority", "medium")).lower()
    prio_vi = PRIORITY_NAMES_VI.get(prio_raw, prio_raw.title())
    color = DISCORD_PRIORITY_COLORS.get(prio_raw, 0x3498DB)

    payload = {
        "content": None,
        "embeds": [
            {
                "title": f"🔔 Yêu cầu hỗ trợ mới: #{field('id', 30)} — {field('title', 100)}",
                "description": field("description", 300),
                "color": color,
                "fields": [
                    {"name": "👤 Người gửi", "value": field("requester", 80), "inline": True},
                    {"name": "⚡ Mức ưu tiên", "value": prio_vi, "inline": True},
                    {"name": "📂 Danh mục", "value": field("category", 80), "inline": True},
                    {"name": "⏳ Hạn SLA", "value": field("sla_deadline", 50), "inline": True},
                    {"name": "🕒 Thời điểm tạo", "value": field("created_at", 50), "inline": True},
                ],
                "footer": {"text": "OpsMind Helpdesk • Thông báo sự cố tự động"},
            }
        ],
    }

    try:
        req = Request(  # noqa: S310 -- Đã kiểm tra _is_safe_url
            url,
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json", "User-Agent": "OpsMind-Helpdesk-Notifier/1.0"},
            method="POST",
        )
        with urlopen(req, timeout=8) as response:  # noqa: S310 -- Đã kiểm tra _is_safe_url
            if response.status in (200, 204):
                logger.info("Discord: Gửi thông báo thành công cho Ticket #%s.", ticket.get("id"))
                return True
        logger.warning("Discord: Máy chủ trả về mã HTTP %s.", response.status)
        return False
    except Exception:
        # Không in chi tiết lỗi để bảo vệ secret token trong webhook url
        logger.warning("Discord: Không thể gửi thông báo tới webhook (ticket vẫn được lưu an toàn).")
        return False


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
    if os.environ.get("DISCORD_WEBHOOK_URL"):
        ok = notify_discord(ticket)
        results["discord"] = ok
        record_notification_event(
            "discord",
            f"Ticket #{ticket_id} ({prio_vi})",
            "Discord IT Alert",
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
        token = os.environ.get("TELEGRAM_BOT_TOKEN", "").strip()
        chat_id = os.environ.get("TELEGRAM_CHAT_ID", "").strip()
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
        ok = notify_telegram(test_ticket)
        if ok:
            record_notification_event(
                "telegram",
                "Thử nghiệm Telegram",
                f"...{chat_id[-4:]}" if len(chat_id) >= 4 else "Telegram Group",
                "success",
                "Thành công",
                "Gửi thông báo thử nghiệm tới Telegram IT thành công.",
            )
            return True, "Gửi thông báo thử nghiệm tới nhóm Telegram thành công."
        record_notification_event(
            "telegram",
            "Thử nghiệm Telegram",
            "Telegram Group",
            "error",
            "Lỗi kết nối",
            "Máy chủ Telegram trả về lỗi kết nối.",
        )
        return False, "Không thể gửi thông báo: Lỗi kết nối Telegram API. Vui lòng kiểm tra lại Bot Token và Chat ID."
    if channel == "discord":
        url = os.environ.get("DISCORD_WEBHOOK_URL", "").strip()
        if not url:
            record_notification_event(
                "discord",
                "Thử nghiệm Discord",
                "Discord Channel",
                "error",
                "Chưa cấu hình",
                "Thiếu biến môi trường DISCORD_WEBHOOK_URL.",
            )
            return False, "Không thể gửi thông báo: Chưa cấu hình biến môi trường DISCORD_WEBHOOK_URL trên Render."
        ok = notify_discord(test_ticket)
        if ok:
            record_notification_event(
                "discord",
                "Thử nghiệm Discord",
                f"...{url[-8:]}" if len(url) >= 8 else "Discord Webhook",
                "success",
                "Thành công",
                "Gửi thông báo thử nghiệm tới Discord Webhook thành công.",
            )
            return True, "Gửi thông báo thử nghiệm tới Discord Webhook thành công."
        record_notification_event(
            "discord",
            "Thử nghiệm Discord",
            "Discord Webhook",
            "error",
            "Lỗi kết nối",
            "Máy chủ Discord trả về lỗi kết nối.",
        )
        return False, "Không thể gửi thông báo: Lỗi kết nối Discord Webhook. Vui lòng kiểm tra lại Webhook URL."
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

    tg_token = os.environ.get("TELEGRAM_BOT_TOKEN", "").strip()
    tg_chat = os.environ.get("TELEGRAM_CHAT_ID", "").strip()
    discord_url = os.environ.get("DISCORD_WEBHOOK_URL", "").strip()

    masked_chat = f"...{tg_chat[-4:]}" if len(tg_chat) >= 4 else ("Bật" if tg_chat else "Chưa cấu hình")
    masked_discord = f"...{discord_url[-8:]}" if len(discord_url) >= 8 else ("Bật" if discord_url else "Chưa cấu hình")

    return {
        "telegram": {
            "enabled": bool(tg_token and tg_chat),
            "target": masked_chat,
        },
        "discord": {
            "enabled": bool(discord_url),
            "target": masked_discord,
        },
        "email": email_sender.get_email_status(),
        "history": get_notification_history(),
    }
