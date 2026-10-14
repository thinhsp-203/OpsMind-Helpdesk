from collections.abc import Iterator
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app import email_sender, store
from app.main import app
from app.rag import build_retrieval_index, load_knowledge_base

client = TestClient(app)


@pytest.fixture(autouse=True)
def clean_test_env(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Iterator[None]:
    from app.main import _failed_logins, _forgot_password_attempts
    _failed_logins.clear()
    _forgot_password_attempts.clear()
    email_sender.clear_outbox()

    monkeypatch.setattr(store, "_database_path", tmp_path / "test-helpdesk.sqlite3")
    monkeypatch.setattr(store, "_database_url", "")
    store.initialize_store()
    store.reset_store()
    load_knowledge_base.cache_clear()
    build_retrieval_index.cache_clear()

    yield

    _failed_logins.clear()
    _forgot_password_attempts.clear()
    email_sender.clear_outbox()
    load_knowledge_base.cache_clear()
    build_retrieval_index.cache_clear()


def test_forgot_password_nonexistent_user_returns_uniform_success() -> None:
    response = client.post(
        "/auth/forgot-password",
        json={"identifier": "nonexistent_user_999"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert "hướng dẫn đặt lại mật khẩu" in data["message"].lower()
    assert len(email_sender.get_outbox()) == 0


def test_forgot_password_user_without_email_returns_uniform_success() -> None:
    # 'user' exists in default seed, but has empty email
    response = client.post(
        "/auth/forgot-password",
        json={"identifier": "user"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert len(email_sender.get_outbox()) == 0


def test_forgot_password_valid_user_with_email_dispatches_reset_message() -> None:
    store.update_user("user", {"email": "employee@opsmind.internal"})

    response = client.post(
        "/auth/forgot-password",
        json={"identifier": "user"},
    )
    assert response.status_code == 200
    outbox = email_sender.get_outbox()
    assert len(outbox) == 1
    msg = outbox[0]
    assert msg["to"] == "employee@opsmind.internal"
    assert msg["username"] == "user"
    assert len(msg["token"]) >= 32
    assert msg["token"] in msg["body"]


def test_reset_password_full_lifecycle_and_session_invalidation() -> None:
    store.update_user("user", {"email": "employee@opsmind.internal"})

    # 1. User logs in with default password and obtains a JWT session
    login_resp = client.post("/auth/login", json={"username": "user", "password": "user"})
    assert login_resp.status_code == 200
    old_jwt = login_resp.json()["token"]

    # Session is currently active
    me_resp = client.get("/auth/me", headers={"Authorization": f"Bearer {old_jwt}"})
    assert me_resp.status_code == 200
    assert me_resp.json()["username"] == "user"

    # 2. Trigger forgot password
    client.post("/auth/forgot-password", json={"identifier": "employee@opsmind.internal"})
    outbox = email_sender.get_outbox()
    assert len(outbox) == 1
    token = outbox[0]["token"]

    # 3. Reset password using token
    new_password = "BrandNewSecurePassword2026!"  # noqa: S105
    reset_resp = client.post(
        "/auth/reset-password",
        json={"token": token, "new_password": new_password},
    )
    assert reset_resp.status_code == 200
    assert reset_resp.json()["status"] == "success"

    # 4. Old JWT session must be revoked immediately
    stale_resp = client.get("/auth/me", headers={"Authorization": f"Bearer {old_jwt}"})
    assert stale_resp.status_code == 401
    assert "Mật khẩu đã được thay đổi" in stale_resp.json()["detail"]

    # 5. Old password no longer works
    old_login = client.post("/auth/login", json={"username": "user", "password": "user"})
    assert old_login.status_code == 401

    # 6. New password successfully logs in
    new_login = client.post("/auth/login", json={"username": "user", "password": new_password})
    assert new_login.status_code == 200

    # 7. Reusing the token must fail
    reuse_resp = client.post(
        "/auth/reset-password",
        json={"token": token, "new_password": "AnotherNewPassword123!"},
    )
    assert reuse_resp.status_code == 400


def test_reset_password_rejects_weak_password_and_invalid_token() -> None:
    # Password too short (< 12 chars)
    short_resp = client.post(
        "/auth/reset-password",
        json={"token": "valid_looking_token_1234567890", "new_password": "short"},
    )
    assert short_resp.status_code == 422

    # Bogus token
    fake_resp = client.post(
        "/auth/reset-password",
        json={"token": "non_existent_token_1234567890", "new_password": "ValidLengthPassword123!"},
    )
    assert fake_resp.status_code == 400


def test_reset_password_expired_token(monkeypatch: pytest.MonkeyPatch) -> None:
    store.update_user("user", {"email": "employee@opsmind.internal"})
    raw_token = store.create_password_reset_token("user", expires_minutes=15)

    # Monkeypatch datetime in store to simulate expired token
    future = datetime.now(timezone.utc) + timedelta(minutes=30)

    class MockDatetime:
        @classmethod
        def now(cls, tz=None):
            return future

        @classmethod
        def fromisoformat(cls, val):
            return datetime.fromisoformat(val)

    monkeypatch.setattr(store, "datetime", MockDatetime)

    resp = client.post(
        "/auth/reset-password",
        json={"token": raw_token, "new_password": "ValidLengthPassword123!"},
    )
    assert resp.status_code == 400


def test_forgot_password_rate_limiting() -> None:
    store.update_user("user", {"email": "employee@opsmind.internal"})

    # Send 5 allowed requests
    for _ in range(5):
        resp = client.post("/auth/forgot-password", json={"identifier": "user"})
        assert resp.status_code == 200

    # 6th request triggers rate limit HTTP 429
    blocked = client.post("/auth/forgot-password", json={"identifier": "user"})
    assert blocked.status_code == 429
    assert "quá nhiều lần" in blocked.json()["detail"]
