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
    from app.main import _failed_logins, _forgot_password_attempts, _forgot_password_target_cooldown
    _failed_logins.clear()
    _forgot_password_attempts.clear()
    _forgot_password_target_cooldown.clear()
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
    _forgot_password_target_cooldown.clear()
    email_sender.clear_outbox()
    load_knowledge_base.cache_clear()
    build_retrieval_index.cache_clear()


@pytest.mark.parametrize("failure_phase", ["password_write", "revoke_other_links"])
def test_atomic_reset_rolls_back_token_and_password_on_failure(failure_phase: str) -> None:
    import sqlite3

    token = store.create_password_reset_token("user")
    other = store.create_password_reset_token("user")
    before = store.get_user_credentials("user")
    with store._connect() as connection:
        # Model legacy data with two outstanding links for the same account.
        connection.execute("UPDATE password_reset_tokens SET used = 0 WHERE username = 'user'")
        if failure_phase == "password_write":
            trigger = (
                "CREATE TRIGGER aud07_fail BEFORE UPDATE OF password_hash ON users "
                "BEGIN SELECT RAISE(ABORT, 'AUD07 synthetic failure'); END;"
            )
        else:
            trigger = (
                "CREATE TRIGGER aud07_fail BEFORE UPDATE ON password_reset_tokens "
                "WHEN OLD.id = (SELECT MAX(id) FROM password_reset_tokens WHERE username = 'user') "
                "BEGIN SELECT RAISE(ABORT, 'AUD07 synthetic failure'); END;"
            )
        connection.execute(trigger)
    with pytest.raises(sqlite3.IntegrityError, match="AUD07 synthetic failure"):
        store.reset_password_with_token(token, "AUD07-ResetPassword-2026!")
    assert store.get_user_credentials("user") == before
    with store._connect() as connection:
        flags = connection.execute(
            "SELECT used FROM password_reset_tokens WHERE username = 'user' ORDER BY id"
        ).fetchall()
        assert [row["used"] for row in flags] == [0, 0]
        connection.execute("DROP TRIGGER aud07_fail")
    assert store.reset_password_with_token(token, "AUD07-ResetPassword-2026!") == "user"
    assert store.verify_and_consume_reset_token(token) is None
    assert store.verify_and_consume_reset_token(other) is None


@pytest.mark.parametrize("journal_mode", ["DELETE", "WAL"])
@pytest.mark.parametrize("operation", ["reset", "consume", "issue"])
def test_concurrent_reset_operations_have_one_winner(journal_mode: str, operation: str) -> None:
    from concurrent.futures import ThreadPoolExecutor
    from threading import Barrier

    with store._connect() as connection:
        # Two fixed test modes; no caller-controlled SQL.
        connection.execute("PRAGMA journal_mode = WAL" if journal_mode == "WAL" else "PRAGMA journal_mode = DELETE")
    token = store.create_password_reset_token("user")
    gate = Barrier(3)
    passwords = ["AUD07-FirstPassword-2026!", "AUD07-SecondPassword-2026!"]

    def run(index):
        gate.wait(timeout=10)
        if operation == "consume":
            return store.verify_and_consume_reset_token(token)
        if operation == "issue" and index == 1:
            return store.create_password_reset_token("user")
        return store.reset_password_with_token(token, passwords[index])

    with ThreadPoolExecutor(max_workers=2) as pool:
        futures = [pool.submit(run, index) for index in range(2)]
        gate.wait(timeout=10)
        results = [future.result(timeout=20) for future in futures]
    if operation == "issue":
        assert results[0] in {None, "user"}
        assert store.reset_password_with_token(results[1], passwords[1]) == "user"
    else:
        assert results.count("user") == 1
        assert results.count(None) == 1
        if operation == "reset":
            credentials = store.get_user_credentials("user")
            winner = results.index("user")
            assert store.verify_password(passwords[winner], credentials["password_hash"])
            assert not store.verify_password(passwords[1 - winner], credentials["password_hash"])
    assert store.verify_and_consume_reset_token(token) is None


@pytest.mark.parametrize("change_path", ["self", "admin", "store"])
def test_old_reset_link_is_revoked_after_password_change(change_path: str) -> None:
    login = client.post("/auth/login", json={"username": "user", "password": "user"})
    user_headers = {"Authorization": f"Bearer {login.json()['token']}"}
    old_link = store.create_password_reset_token("user")
    other_link = store.create_password_reset_token("agent")
    new_password = "AUD06-NewPassword-2026!"  # noqa: S105
    if change_path == "self":
        changed = client.post(
            "/auth/change-password", headers=user_headers,
            json={"old_password": "user", "new_password": new_password},
        )
        assert changed.status_code == 200
    elif change_path == "admin":
        admin = client.post("/auth/login", json={"username": "admin", "password": "admin"})
        changed = client.post(
            "/admin/users/user/reset-password",
            headers={"Authorization": f"Bearer {admin.json()['token']}"},
            json={"new_password": new_password, "force_change": False},
        )
        assert changed.status_code == 200
    else:
        store.update_user_password("user", new_password)
    assert client.get("/auth/me", headers=user_headers).status_code == 401
    stale = client.post(
        "/auth/reset-password",
        json={"token": old_link, "new_password": "AUD06-UnwantedPassword-2026!"},
    )
    assert stale.status_code == 400
    assert client.post(
        "/auth/login", json={"username": "user", "password": new_password},
    ).status_code == 200
    assert store.verify_and_consume_reset_token(other_link) == "agent"
    fresh = store.create_password_reset_token("user")
    payload = {"token": fresh, "new_password": "AUD06-RecoveredPassword-2026!"}
    assert client.post("/auth/reset-password", json=payload).status_code == 200
    assert client.post("/auth/reset-password", json=payload).status_code == 400


@pytest.mark.parametrize("change_path", ["profile_email", "admin_email", "disable_enable"])
def test_old_reset_link_is_revoked_after_security_profile_change(change_path: str) -> None:
    store.update_user("user", {"email": "old@example.com"})
    user = client.post("/auth/login", json={"username": "user", "password": "user"})
    admin = client.post("/auth/login", json={"username": "admin", "password": "admin"})
    admin_headers = {"Authorization": f"Bearer {admin.json()['token']}"}
    old_link = store.create_password_reset_token("user")
    if change_path == "profile_email":
        changed = client.patch(
            "/auth/profile", headers={"Authorization": f"Bearer {user.json()['token']}"},
            json={"email": "new@example.com", "current_password": "user"},
        )
        assert changed.status_code == 200
    elif change_path == "admin_email":
        changed = client.patch(
            "/admin/users/user", headers=admin_headers, json={"email": "new@example.com"},
        )
        assert changed.status_code == 200
    else:
        assert client.patch(
            "/admin/users/user", headers=admin_headers, json={"is_active": False},
        ).status_code == 200
        assert client.patch(
            "/admin/users/user", headers=admin_headers, json={"is_active": True},
        ).status_code == 200
    assert client.post(
        "/auth/reset-password",
        json={"token": old_link, "new_password": "AUD06-UnwantedPassword-2026!"},
    ).status_code == 400
    assert client.post(
        "/auth/login", json={"username": "user", "password": "user"},
    ).status_code == 200
    fresh = store.create_password_reset_token("user")
    assert client.post(
        "/auth/reset-password",
        json={"token": fresh, "new_password": "AUD06-RecoveredPassword-2026!"},
    ).status_code == 200


def test_legacy_unused_reset_link_before_password_epoch_is_rejected() -> None:
    token = store.create_password_reset_token("user")
    # Emulate a persisted password change from the old implementation, without revocation.
    with store._connect() as connection:
        connection.execute(
            "UPDATE users SET password_changed_at = ? WHERE username = ?",
            (store._now(), "user"),
        )
    assert store.verify_and_consume_reset_token(token) is None
    fresh = store.create_password_reset_token("user")
    assert store.verify_and_consume_reset_token(fresh) == "user"


@pytest.mark.parametrize("updates", [
    {"full_name": "Updated Display Name"},
    {"email": "USER@EXAMPLE.COM"},
    {"is_active": True},
])
def test_reset_link_remains_valid_after_non_security_profile_update(updates: dict) -> None:
    store.update_user("user", {"email": "user@example.com"})
    token = store.create_password_reset_token("user")
    store.update_user("user", updates)
    assert store.verify_and_consume_reset_token(token) == "user"


@pytest.mark.parametrize("change_path", ["password", "email", "disable"])
def test_security_update_rolls_back_when_reset_link_revocation_fails(change_path: str) -> None:
    import sqlite3

    token = store.create_password_reset_token("user")
    before = store.get_user_credentials("user")
    with store._connect() as connection:
        connection.executescript(
            "CREATE TRIGGER fail_reset_revocation BEFORE UPDATE ON password_reset_tokens "
            "BEGIN SELECT RAISE(ABORT, 'AUD06 revocation failure'); END;"
        )
    with pytest.raises(sqlite3.IntegrityError, match="AUD06 revocation failure"):
        if change_path == "password":
            store.update_user_password("user", "AUD06-NewPassword-2026!")
        elif change_path == "email":
            store.update_user("user", {"email": "changed@example.com"})
        else:
            store.update_user("user", {"is_active": False})
    assert store.get_user_credentials("user") == before
    with store._connect() as connection:
        connection.execute("DROP TRIGGER fail_reset_revocation")
    assert store.verify_and_consume_reset_token(token) == "user"


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


def test_admin_create_user_sends_welcome_email_and_enforces_password_change() -> None:
    # 1. Login as admin
    admin_login = client.post("/auth/login", json={"username": "admin", "password": "admin"})
    assert admin_login.status_code == 200
    admin_token = admin_login.json()["token"]

    # 2. Admin creates a new user with email
    create_resp = client.post(
        "/admin/users",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={
            "username": "new.employee",
            "password": "TempPassword1234!",
            "role": "user",
            "full_name": "New Employee",
            "email": "new.employee@opsmind.internal",
            "department": "Engineering",
        },
    )
    assert create_resp.status_code == 201
    assert create_resp.json()["username"] == "new.employee"

    # 3. Check outbox for welcome email
    outbox = email_sender.get_outbox()
    assert len(outbox) == 1
    welcome_email = outbox[0]
    assert welcome_email["to"] == "new.employee@opsmind.internal"
    assert "TempPassword1234!" not in welcome_email["body"]
    assert "temp_password" not in welcome_email
    assert welcome_email["token"] in welcome_email["link"]
    assert "đổi mật khẩu ngay trong lần đăng nhập đầu tiên" in welcome_email["body"]

    # 4. User logs in with temporary password
    user_login = client.post("/auth/login", json={"username": "new.employee", "password": "TempPassword1234!"})
    assert user_login.status_code == 200
    user_data = user_login.json()
    assert user_data["force_password_change"] is True
    emp_token = user_data["token"]

    # 5. Accessing protected endpoint returns 403 because password must be changed first
    blocked_resp = client.get("/tickets", headers={"Authorization": f"Bearer {emp_token}"})
    assert blocked_resp.status_code == 403
    assert "yêu cầu bạn đổi mật khẩu" in blocked_resp.json()["detail"]

    # 6. Change password succeeds
    change_resp = client.post(
        "/auth/change-password",
        headers={"Authorization": f"Bearer {emp_token}"},
        json={"old_password": "TempPassword1234!", "new_password": "PermanentSecurePass2026!"},
    )
    assert change_resp.status_code == 200

    # 7. Relogin with new password - force_password_change is now False and user can access tickets
    relogin = client.post("/auth/login", json={"username": "new.employee", "password": "PermanentSecurePass2026!"})
    assert relogin.status_code == 200
    assert relogin.json()["force_password_change"] is False
    new_token = relogin.json()["token"]
    assert client.get("/tickets", headers={"Authorization": f"Bearer {new_token}"}).status_code == 200


def test_admin_generate_reset_token_endpoint_and_usage() -> None:
    admin_login = client.post("/auth/login", json={"username": "admin", "password": "admin"})
    admin_token = admin_login.json()["token"]

    # Non-admin cannot generate reset token
    user_login = client.post("/auth/login", json={"username": "user", "password": "user"})
    user_token = user_login.json()["token"]
    forbidden = client.post(
        "/admin/users/user/create-reset-token",
        headers={"Authorization": f"Bearer {user_token}"},
    )
    assert forbidden.status_code == 403

    # Admin generates reset token for 'user'
    token_resp = client.post(
        "/admin/users/user/create-reset-token",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert token_resp.status_code == 200
    data = token_resp.json()
    assert data["status"] == "success"
    assert data["username"] == "user"
    assert len(data["token"]) >= 32
    assert "#reset-token=" in data["reset_link"]

    # Use the token to reset user's password
    reset_resp = client.post(
        "/auth/reset-password",
        json={"token": data["token"], "new_password": "NewAdminIssuedPass2026!"},
    )
    assert reset_resp.status_code == 200

    # Login works with new password
    login_resp = client.post("/auth/login", json={"username": "user", "password": "NewAdminIssuedPass2026!"})
    assert login_resp.status_code == 200


def test_email_sender_smtp_dispatch_and_headers(monkeypatch: pytest.MonkeyPatch) -> None:
    from app import config
    from unittest.mock import MagicMock

    monkeypatch.setattr(config, "EMAIL_PROVIDER", "smtp")
    monkeypatch.setattr(config, "SMTP_ENABLED", True)
    monkeypatch.setattr(config, "SMTP_HOST", "smtp.test.com")
    monkeypatch.setattr(config, "SMTP_PORT", 587)
    monkeypatch.setattr(config, "SMTP_USER", "mailer@test.com")
    monkeypatch.setattr(config, "SMTP_PASSWORD", "secret")
    monkeypatch.setattr(config, "EMAIL_FROM", "mailer@test.com")
    monkeypatch.setattr(config, "SMTP_USE_TLS", True)
    monkeypatch.setattr(config, "SMTP_SSL_VERIFY", True)

    mock_server = MagicMock()
    mock_server.send_message.return_value = {}
    mock_server_cm = MagicMock()
    mock_server_cm.__enter__.return_value = mock_server
    mock_server_cm.__exit__.return_value = None

    import smtplib
    monkeypatch.setattr(smtplib, "SMTP", lambda host, port, timeout: mock_server_cm)

    sent = email_sender.dispatch_email(
        "recipient@example.com",
        "[OpsMind Helpdesk] Hướng dẫn đặt lại mật khẩu tài khoản",
        "Nội dung email thử nghiệm.",
    )
    assert sent is True
    assert mock_server.starttls.called
    assert mock_server.login.called
    assert mock_server.send_message.called

    sent_msg = mock_server.send_message.call_args[0][0]
    assert sent_msg["To"] == "recipient@example.com"
    assert sent_msg["From"] == "mailer@test.com"
    assert sent_msg["Date"] is not None
    assert sent_msg["Message-ID"] is not None
    assert sent_msg["Message-ID"].endswith("test.com>")


def test_email_sender_smtp_ssl_port_465(monkeypatch: pytest.MonkeyPatch) -> None:
    from app import config
    from unittest.mock import MagicMock
    import smtplib

    monkeypatch.setattr(config, "EMAIL_PROVIDER", "smtp")
    monkeypatch.setattr(config, "SMTP_ENABLED", True)
    monkeypatch.setattr(config, "SMTP_PORT", 465)
    monkeypatch.setattr(config, "SMTP_USER", "ssl@test.com")
    monkeypatch.setattr(config, "SMTP_PASSWORD", "secret")

    mock_server = MagicMock()
    mock_server.send_message.return_value = {}
    mock_server_cm = MagicMock()
    mock_server_cm.__enter__.return_value = mock_server
    mock_server_cm.__exit__.return_value = None

    monkeypatch.setattr(smtplib, "SMTP_SSL", lambda host, port, timeout, context: mock_server_cm)

    sent = email_sender.dispatch_email("recipient@example.com", "Test Subject", "Body")
    assert sent is True
    assert mock_server.login.called
    assert mock_server.send_message.called


def test_email_sender_resend_api(monkeypatch: pytest.MonkeyPatch) -> None:
    from app import config
    import httpx

    monkeypatch.setattr(config, "EMAIL_PROVIDER", "resend")
    monkeypatch.setattr(config, "RESEND_API_KEY", "re_test_key_123456789")
    monkeypatch.setattr(config, "EMAIL_FROM", "test@domain.com")

    def mock_post(url, headers, json, timeout):
        assert "api.resend.com" in url
        assert headers["Authorization"] == "Bearer re_test_key_123456789"
        assert json["to"] == ["target@example.com"]
        return httpx.Response(200, json={"id": "email_123"})

    monkeypatch.setattr(httpx, "post", mock_post)

    assert email_sender.dispatch_email("target@example.com", "Subject", "Body") is True

    # Test error response
    monkeypatch.setattr(httpx, "post", lambda url, headers, json, timeout: httpx.Response(400, text="Bad Request"))
    assert email_sender.dispatch_email("target@example.com", "Subject", "Body") is False


def test_email_sender_brevo_api(monkeypatch: pytest.MonkeyPatch) -> None:
    from app import config
    import httpx

    # Verify case-insensitive env resolution
    monkeypatch.setenv("Brevo_API_KEY", "xkeysib-case-test-12345678")
    assert config._get_env_case_insensitive("BREVO_API_KEY") == "xkeysib-case-test-12345678"

    monkeypatch.setattr(config, "EMAIL_PROVIDER", "brevo")
    monkeypatch.setattr(config, "BREVO_API_KEY", "xkeysib-test-12345678")
    monkeypatch.setattr(config, "EMAIL_FROM", "test@domain.com")

    def mock_post(url, headers, json, timeout):
        assert "api.brevo.com" in url
        assert headers["api-key"] == "xkeysib-test-12345678"
        return httpx.Response(201, json={"messageId": "msg_123"})

    monkeypatch.setattr(httpx, "post", mock_post)
    assert email_sender.dispatch_email("target@example.com", "Subject", "Body") is True


def test_email_sender_webhook_api(monkeypatch: pytest.MonkeyPatch) -> None:
    from app import config
    import httpx

    monkeypatch.setattr(config, "EMAIL_PROVIDER", "webhook")
    monkeypatch.setattr(config, "EMAIL_WEBHOOK_URL", "https://hooks.example.com/email")

    monkeypatch.setattr(httpx, "post", lambda url, json, timeout: httpx.Response(200, json={"ok": True}))
    assert email_sender.dispatch_email("target@example.com", "Subject", "Body") is True


def test_email_sender_status_and_admin_test_endpoint() -> None:
    admin_login = client.post("/auth/login", json={"username": "admin", "password": "admin"})
    admin_token = admin_login.json()["token"]

    # Test notification channels status includes email
    status_resp = client.get("/admin/notifications/status", headers={"Authorization": f"Bearer {admin_token}"})
    assert status_resp.status_code == 200
    channels = status_resp.json()
    assert "email" in channels
    assert "provider" in channels["email"]
    assert "target" in channels["email"]

    # Test admin test notification with email channel
    test_resp = client.post(
        "/admin/notifications/test",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={"channel": "email", "target_email": "admin.test@opsmind.internal"},
    )
    assert test_resp.status_code == 200
    assert test_resp.json()["success"] is True
    assert test_resp.json()["channel"] == "email"


def test_email_sender_invalid_email_and_exceptions(monkeypatch: pytest.MonkeyPatch) -> None:
    from app import config
    assert email_sender.dispatch_email("", "Subject", "Body") is False
    assert email_sender.dispatch_email("invalid-email-no-at", "Subject", "Body") is False
    assert email_sender.send_account_created_email("", "user", "pass") is False

    monkeypatch.setattr(config, "EMAIL_PROVIDER", "smtp")
    monkeypatch.setattr(config, "SMTP_ENABLED", True)
    import smtplib
    monkeypatch.setattr(smtplib, "SMTP", lambda *a, **k: (_ for _ in ()).throw(smtplib.SMTPConnectError(421, b"Connection refused")))
    assert email_sender.dispatch_email("user@example.com", "Subject", "Body") is False


def test_email_sender_edge_cases_and_branch_coverage(monkeypatch: pytest.MonkeyPatch) -> None:
    from app import config

    # 1. _mask_token
    assert email_sender._mask_token("abc") == "***"
    assert email_sender._mask_token("1234567890abcdef") == "1234...cdef"

    # 2. resolve_email_provider fallbacks
    monkeypatch.setattr(config, "EMAIL_PROVIDER", "")
    monkeypatch.setattr(config, "RESEND_API_KEY", "resend_key")
    assert email_sender.resolve_email_provider() == "resend"

    monkeypatch.setattr(config, "RESEND_API_KEY", "")
    monkeypatch.setattr(config, "BREVO_API_KEY", "brevo_key")
    assert email_sender.resolve_email_provider() == "brevo"

    monkeypatch.setattr(config, "BREVO_API_KEY", "")
    monkeypatch.setattr(config, "SMTP_ENABLED", True)
    assert email_sender.resolve_email_provider() == "smtp"

    monkeypatch.setattr(config, "SMTP_ENABLED", False)
    assert email_sender.resolve_email_provider() == "console"

    # 3. get_email_status across providers
    monkeypatch.setattr(config, "EMAIL_PROVIDER", "resend")
    monkeypatch.setattr(config, "RESEND_API_KEY", "re_12345")
    st = email_sender.get_email_status()
    assert st["provider"] == "resend"
    assert "Resend API" in st["target"]

    monkeypatch.setattr(config, "EMAIL_PROVIDER", "brevo")
    monkeypatch.setattr(config, "BREVO_API_KEY", "xkeysib_12345")
    st = email_sender.get_email_status()
    assert st["provider"] == "brevo"
    assert "Brevo API" in st["target"]

    monkeypatch.setattr(config, "EMAIL_PROVIDER", "webhook")
    monkeypatch.setattr(config, "EMAIL_WEBHOOK_URL", "https://hook.io/email-target-endpoint")
    st = email_sender.get_email_status()
    assert st["provider"] == "webhook"

    # AUD-16 FIX: unknown/typo'd provider must be rejected, not fall through to mock.
    monkeypatch.setattr(config, "EMAIL_PROVIDER", "unknown_custom")
    assert email_sender.dispatch_email("user@example.com", "Subject", "Body") is False, (
        "dispatch_email must return False for unknown EMAIL_PROVIDER (AUD-16)"
    )
    with pytest.raises(ValueError, match="unknown_custom"):
        email_sender.get_email_status()
    assert email_sender.get_last_send_error() != "", (
        "last_send_error must be set after invalid provider dispatch"
    )

    # 4. Missing API keys for direct helper calls
    monkeypatch.setattr(config, "RESEND_API_KEY", "")
    assert email_sender._send_via_resend("user@example.com", "Subject", "Body") is False

    monkeypatch.setattr(config, "BREVO_API_KEY", "")
    assert email_sender._send_via_brevo("user@example.com", "Subject", "Body") is False

    monkeypatch.setattr(config, "EMAIL_WEBHOOK_URL", "")
    assert email_sender._send_via_webhook("user@example.com", "Subject", "Body") is False

    # 5. Non-demo untrusted host rejection
    monkeypatch.setattr(config, "DEMO_MODE", False)
    monkeypatch.setattr(config, "PUBLIC_BASE_URL", "")
    assert email_sender.send_password_reset_email("user@example.com", "user", "token_123") is False

    # 6. send_test_email edge cases
    assert email_sender.send_test_email("")[0] is False
    monkeypatch.setattr(config, "EMAIL_PROVIDER", "resend")
    monkeypatch.setattr(config, "RESEND_API_KEY", "")
    fail_res, fail_msg = email_sender.send_test_email("admin@example.com")
    assert fail_res is False
    assert "Không thể gửi email" in fail_msg


