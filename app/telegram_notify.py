"""Optional, best-effort Telegram notifications; no secrets in logs."""
import json
import logging
import os
from urllib.request import Request, urlopen

logger = logging.getLogger(__name__)


def notify_ticket_created(ticket: dict) -> None:
    token = os.environ.get("TELEGRAM_BOT_TOKEN", "").strip()
    chat_id = os.environ.get("TELEGRAM_CHAT_ID", "").strip()
    if not token or not chat_id:
        return
    try:
        def field(name, limit=200):
            return " ".join(str(ticket.get(name, "—")).split())[:limit]

        priority = {"low": "Thấp", "medium": "Trung bình", "high": "Cao", "urgent": "Khẩn cấp"}
        text = (
            "🔔 Có yêu cầu hỗ trợ mới\n\n"
            f"🎫 Ticket: #{field('id', 30)}\n"
            f"📌 Tiêu đề: {field('title')}\n"
            f"👤 Người gửi: {field('requester', 80)}\n"
            f"⚡ Ưu tiên: {priority.get(ticket.get('priority'), field('priority', 30))}\n"
            f"📂 Danh mục: {field('category', 80)}\n"
            f"🕒 Thời gian (ISO): {field('created_at', 50)}\n"
            "Trạng thái: Mới\n\nMở Helpdesk để xem và xử lý yêu cầu."
        )
        request = Request(
            f"https://api.telegram.org/bot{token}/sendMessage",
            data=json.dumps({"chat_id": chat_id, "text": text}).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urlopen(request, timeout=8) as response:
            result = json.load(response)
        if not result.get("ok"):
            logger.warning("Telegram: notification rejected; ticket remains saved.")
    except Exception:
        # Exception text can contain the URL and bot token: never log it.
        logger.warning("Telegram: notification failed; ticket remains saved.")

