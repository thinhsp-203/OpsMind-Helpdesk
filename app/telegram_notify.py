"""Adapter tương thích ngược cho thông báo sự cố OpsMind Helpdesk."""
from __future__ import annotations

from app.notifications import (
    dispatch_ticket_notification,
    notify_discord,
    notify_telegram,
)


def notify_ticket_created(ticket: dict) -> None:
    """Gửi thông báo tạo ticket mới tới các kênh đã bật (Telegram, Discord)."""
    dispatch_ticket_notification(ticket)


__all__ = ["notify_ticket_created", "notify_telegram", "notify_discord", "dispatch_ticket_notification"]
