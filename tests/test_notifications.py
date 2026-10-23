from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.notifications import (
    ALLOWED_TELEGRAM_DOMAINS,
    _is_safe_url,
    dispatch_ticket_notification,
    get_notification_channels_status,
    notify_telegram,
    send_test_notification,
)

client = TestClient(app)


def test_safe_url_validation_blocks_ssrf_and_allows_legitimate_domains() -> None:
    # Hợp lệ
    assert _is_safe_url("https://api.telegram.org/bot123/sendMessage", ALLOWED_TELEGRAM_DOMAINS)

    # Chặn giao thức không an toàn (HTTP)
    assert not _is_safe_url("http://api.telegram.org/bot123", ALLOWED_TELEGRAM_DOMAINS)

    # Chặn localhost & IP nội bộ (SSRF vectors)
    assert not _is_safe_url("http://localhost:8000/internal", ALLOWED_TELEGRAM_DOMAINS)
    assert not _is_safe_url("https://127.0.0.1:5432", ALLOWED_TELEGRAM_DOMAINS)
    assert not _is_safe_url("https://192.168.1.100/admin", ALLOWED_TELEGRAM_DOMAINS)
    assert not _is_safe_url("https://10.0.0.1/metadata", ALLOWED_TELEGRAM_DOMAINS)
    assert not _is_safe_url("https://169.254.169.254/latest/meta-data", ALLOWED_TELEGRAM_DOMAINS)

    # Chặn domain bên ngoài không trong allow-list
    assert not _is_safe_url("https://attacker-webhook.com/leak", ALLOWED_TELEGRAM_DOMAINS)
    assert not _is_safe_url("https://malicious.org", ALLOWED_TELEGRAM_DOMAINS)


def test_notifications_return_false_when_unconfigured() -> None:
    dummy_ticket = {"id": 1, "title": "Test Ticket", "requester": "user"}
    with patch.dict("os.environ", {}, clear=True):
        assert not notify_telegram(dummy_ticket)
        assert not send_test_notification("telegram")
        assert not send_test_notification("discord")


def test_notification_channels_status_masks_credentials(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "123456:ABC-DEF1234ghIkl-zyx57W2v1u123ew11")
    monkeypatch.setenv("TELEGRAM_CHAT_ID", "-1001987654321")
    monkeypatch.setenv("DISCORD_WEBHOOK_URL", "https://discord.com/api/webhooks/123456/abcdefgh12345678")

    status = get_notification_channels_status()
    assert status["telegram"]["enabled"] is True
    assert status["telegram"]["target"] == "...4321"  # Masked
    assert "123456:ABC" not in status["telegram"]["target"]

    assert "discord" not in status


def test_admin_notification_endpoints(monkeypatch: pytest.MonkeyPatch) -> None:
    # Đăng nhập lấy token admin & user
    admin_res = client.post("/auth/login", json={"username": "admin", "password": "admin"})
    admin_token = admin_res.json()["token"]
    user_res = client.post("/auth/login", json={"username": "user", "password": "user"})
    user_token = user_res.json()["token"]

    # User bị cấm truy cập (403)
    assert client.get("/admin/notifications/status", headers={"Authorization": f"Bearer {user_token}"}).status_code == 403
    assert client.post("/admin/notifications/test", headers={"Authorization": f"Bearer {user_token}"}, json={"channel": "telegram"}).status_code == 403

    # Admin truy cập status thành công (200)
    status_res = client.get("/admin/notifications/status", headers={"Authorization": f"Bearer {admin_token}"})
    assert status_res.status_code == 200
    assert "telegram" in status_res.json()
    assert "discord" not in status_res.json()

    # Admin test channel khi chưa cấu hình trả 400
    monkeypatch.delenv("TELEGRAM_BOT_TOKEN", raising=False)
    test_res = client.post("/admin/notifications/test", headers={"Authorization": f"Bearer {admin_token}"}, json={"channel": "telegram"})
    assert test_res.status_code == 400
    assert "Không thể gửi" in test_res.json()["detail"]


def test_dispatch_notifications_calls_active_adapters(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "mock-token")
    monkeypatch.setenv("TELEGRAM_CHAT_ID", "-100123")
    monkeypatch.setenv("DISCORD_WEBHOOK_URL", "https://discord.com/api/webhooks/mock")

    dummy_ticket = {
        "id": 99,
        "title": "Outage",
        "category": "network",
        "priority": "urgent",
        "requester": "user",
        "created_at": "2026-10-14T10:00:00Z",
        "sla_deadline": "2026-10-14T12:00:00Z",
    }

    with patch("app.notifications.notify_telegram", return_value=True) as mock_tg:
        results = dispatch_ticket_notification(dummy_ticket)
        assert results == {"telegram": True}
        assert mock_tg.called
