"""Khung kênh thông báo đa nền tảng (Telegram & Discord Webhook) cho OpsMind Helpdesk.

Hỗ trợ:
- Gửi thông báo sự cố mới tới Telegram Bot và Discord Webhook.
- Cơ chế phòng vệ SSRF: Chỉ cho phép kết nối tới tên miền chính thức của Telegram và Discord.
- Bảo mật thông tin xác thực: Không in Bot Token hoặc Webhook Secret trong log khi xảy ra lỗi.
"""

from __future__ import annotations

import json
import logging
import os
import re
from urllib.parse import urlparse
from urllib.request import Request, urlopen

logger = logging.getLogger(__name__)

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
    if os.environ.get("TELEGRAM_BOT_TOKEN") and os.environ.get("TELEGRAM_CHAT_ID"):
        results["telegram"] = notify_telegram(ticket)
    if os.environ.get("DISCORD_WEBHOOK_URL"):
        results["discord"] = notify_discord(ticket)
    return results


def send_test_notification(channel: str) -> bool:
    """Gửi thông báo kiểm tra kết nối tới kênh được chỉ định (Dành cho Admin)."""
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
        return notify_telegram(test_ticket)
    if channel == "discord":
        return notify_discord(test_ticket)
    return False


def get_notification_channels_status() -> dict[str, dict[str, str | bool]]:
    """Trả về trạng thái bật/tắt của các kênh thông báo (ẩn token nhạy cảm)."""
    tg_token = os.environ.get("TELEGRAM_BOT_TOKEN", "").strip()
    tg_chat = os.environ.get("TELEGRAM_CHAT_ID", "").strip()
    discord_url = os.environ.get("DISCORD_WEBHOOK_URL", "").strip()

    masked_chat = f"...{tg_chat[-4:]}" if len(tg_chat) >= 4 else ("Bật" if tg_chat else "Chưa cấu hình")
    masked_discord = (
        f"...{discord_url[-8:]}" if len(discord_url) >= 8 else ("Bật" if discord_url else "Chưa cấu hình")
    )

    return {
        "telegram": {
            "enabled": bool(tg_token and tg_chat),
            "target": masked_chat,
        },
        "discord": {
            "enabled": bool(discord_url),
            "target": masked_discord,
        },
    }
