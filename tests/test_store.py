import sqlite3
from pathlib import Path

import pytest

from app import store


@pytest.fixture
def isolated_database(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    database = tmp_path / "store.sqlite3"
    monkeypatch.setattr(store, "_database_path", database)
    monkeypatch.setattr(store, "_database_url", "")
    return database


def test_initial_non_demo_startup_creates_only_provisioned_admin(
    isolated_database: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(store, "DEMO_MODE", False)
    monkeypatch.setattr(store, "INITIAL_ADMIN_USERNAME", "first.admin")
    monkeypatch.setattr(store, "INITIAL_ADMIN_PASSWORD", "correct-horse-battery-7")

    store.initialize_store()

    users = store.list_users()
    assert users == [
        {
            "username": "first.admin",
            "role": "admin",
            "full_name": "",
            "email": "",
            "department": "",
            "phone": "",
            "is_active": 1,
        }
    ]
    credentials = store.get_user_credentials("first.admin")
    assert credentials is not None
    assert store.verify_password("correct-horse-battery-7", credentials["password_hash"])


def test_non_demo_startup_refuses_unchanged_seeded_demo_credentials(
    isolated_database: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(store, "DEMO_MODE", True)
    store.initialize_store()
    monkeypatch.setattr(store, "DEMO_MODE", False)

    with pytest.raises(RuntimeError, match="Demo credentials are present"):
        store.initialize_store()

    assert {user["username"] for user in store.list_users()} == {"user", "agent", "admin"}


def test_database_migration_adds_archive_timestamp_to_existing_ticket_table(
    isolated_database: Path,
) -> None:
    connection = sqlite3.connect(isolated_database)
    connection.executescript(
        """
        CREATE TABLE users (
            username TEXT PRIMARY KEY,
            password_hash TEXT NOT NULL,
            role TEXT NOT NULL CHECK (role IN ('user', 'agent', 'admin'))
        );
        CREATE TABLE tickets (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            description TEXT NOT NULL,
            category TEXT NOT NULL,
            priority TEXT NOT NULL CHECK (priority IN ('low', 'medium', 'high', 'urgent')),
            requester TEXT NOT NULL REFERENCES users(username),
            assignee TEXT REFERENCES users(username),
            status TEXT NOT NULL CHECK (status IN ('new', 'in_progress', 'resolved', 'closed')),
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            sla_deadline TEXT NOT NULL
        );
        INSERT INTO users (username, password_hash, role)
        VALUES ('user', 'legacy-hash', 'user');
        INSERT INTO tickets
            (title, description, category, priority, requester, status, created_at, updated_at, sla_deadline)
        VALUES
            ('Legacy ticket', 'Old demo ticket description', 'network', 'medium', 'user', 'new',
             '2026-10-01T00:00:00+00:00', '2026-10-01T00:00:00+00:00',
             '2026-10-02T00:00:00+00:00');
        """
    )
    connection.close()

    store.initialize_store()

    with sqlite3.connect(isolated_database) as migrated:
        columns = {row[1] for row in migrated.execute("PRAGMA table_info(tickets)")}
        preserved = migrated.execute(
            "SELECT title, status, archived_at, resolved_at, rating FROM tickets WHERE id = 1"
        ).fetchone()
    assert "archived_at" in columns
    assert {"resolved_at", "closed_at", "rating", "rating_comment"}.issubset(columns)
    assert preserved == ("Legacy ticket", "new", None, None, None)
    ticket = store.create_ticket(
        "New migrated ticket",
        "Ticket created after schema migration for this store test.",
        "network",
        "medium",
        "user",
    )
    assert ticket["id"] == 2


def test_seed_builtin_knowledge_upserts_newly_added_runbooks(
    isolated_database: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(store, "DEMO_MODE", True)
    store.initialize_store()

    initial_docs = store.list_knowledge_documents()
    assert len(initial_docs) >= 30

    # Running seed again is idempotent and doesn't duplicate
    with store._connect() as conn:
        store.seed_builtin_knowledge(conn)
    assert len(store.list_knowledge_documents()) == len(initial_docs)


def test_non_demo_startup_requires_initial_admin_password(
    isolated_database: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(store, "DEMO_MODE", False)
    monkeypatch.setattr(store, "INITIAL_ADMIN_USERNAME", "admin")
    monkeypatch.setattr(store, "INITIAL_ADMIN_PASSWORD", "")

    with pytest.raises(RuntimeError, match="INITIAL_ADMIN_PASSWORD.*must be configured"):
        store.initialize_store()


def test_non_demo_startup_rejects_insecure_placeholder_password(
    isolated_database: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(store, "DEMO_MODE", False)
    monkeypatch.setattr(store, "INITIAL_ADMIN_USERNAME", "admin")
    monkeypatch.setattr(store, "INITIAL_ADMIN_PASSWORD", "AdminSecurePassword123!")

    with pytest.raises(RuntimeError, match="not using known placeholder passwords"):
        store.initialize_store()



def test_database_backed_rate_limiting_persists_across_restart(
    isolated_database: Path,
) -> None:
    store.initialize_store()
    test_key = "login:192.0.2.100"

    # Initially 0 attempts and 0 lockout
    assert store.get_rate_limit_attempts(test_key, 900.0) == []
    assert store.get_lockout_remaining_seconds(test_key) == 0

    # Record 5 failed attempts
    for _ in range(5):
        store.record_rate_limit_attempt(test_key)

    assert len(store.get_rate_limit_attempts(test_key, 900.0)) == 5
    assert store.get_lockout_remaining_seconds(test_key) > 0

    # Simulate application restart: clear volatile in-memory cache
    store._failed_login_attempts.clear()

    # Verify that database persistence retains the lockout and attempts
    attempts_after_restart = store.get_rate_limit_attempts(test_key, 900.0)
    assert len(attempts_after_restart) == 5
    assert store.get_lockout_remaining_seconds(test_key) > 0

    # Reset clears database records
    store.reset_rate_limit(test_key)
    assert store.get_rate_limit_attempts(test_key, 900.0) == []
    assert store.get_lockout_remaining_seconds(test_key) == 0


def test_non_demo_startup_allows_demo_credentials_when_flag_enabled(
    isolated_database: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(store, "DEMO_MODE", True)
    store.initialize_store()
    monkeypatch.setattr(store, "DEMO_MODE", False)
    monkeypatch.setattr(store, "ALLOW_DEMO_CREDENTIALS", True)

    # Should not raise RuntimeError when ALLOW_DEMO_CREDENTIALS is enabled
    store.initialize_store()
    assert {user["username"] for user in store.list_users()} == {"user", "agent", "admin"}


def test_non_demo_startup_allows_demo_credentials_on_empty_db(
    isolated_database: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(store, "DEMO_MODE", False)
    monkeypatch.setattr(store, "ALLOW_DEMO_CREDENTIALS", True)
    monkeypatch.setattr(store, "INITIAL_ADMIN_PASSWORD", "")

    # Should seed demo accounts without error on empty DB
    store.initialize_store()
    assert {user["username"] for user in store.list_users()} == {"user", "agent", "admin"}


def test_non_demo_startup_rejects_admin_password_under_twelve_chars(
    isolated_database: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(store, "DEMO_MODE", False)
    monkeypatch.setattr(store, "INITIAL_ADMIN_USERNAME", "admin")
    monkeypatch.setattr(store, "INITIAL_ADMIN_PASSWORD", "Adm1m@123")  # 9 chars (< 12)

    with pytest.raises(RuntimeError, match="at least 12 characters"):
        store.initialize_store()


def test_non_demo_startup_accepts_custom_admin_password_min_twelve_chars(
    isolated_database: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(store, "DEMO_MODE", False)
    monkeypatch.setattr(store, "INITIAL_ADMIN_USERNAME", "admin")
    monkeypatch.setattr(store, "INITIAL_ADMIN_PASSWORD", "Adm1nPass1234!")  # 14 chars (>= 12)

    store.initialize_store()
    creds = store.get_user_credentials("admin")
    assert creds is not None
    assert store.verify_password("Adm1nPass1234!", creds["password_hash"])


def test_admin_password_preserved_across_restarts_after_user_change(
    isolated_database: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # 1. Khởi động lần đầu với mật khẩu ban đầu từ biến môi trường
    monkeypatch.setattr(store, "DEMO_MODE", False)
    monkeypatch.setattr(store, "INITIAL_ADMIN_USERNAME", "admin")
    monkeypatch.setattr(store, "INITIAL_ADMIN_PASSWORD", "Adm1nInitialPass!")
    store.initialize_store()

    creds = store.get_user_credentials("admin")
    assert creds is not None
    assert store.verify_password("Adm1nInitialPass!", creds["password_hash"])

    # 2. Admin chủ động đổi mật khẩu trong hệ thống (thao tác người dùng)
    store.update_user_password("admin", "AdminChangedSecret999!", force_password_change=0)
    creds_changed = store.get_user_credentials("admin")
    assert creds_changed is not None
    assert store.verify_password("AdminChangedSecret999!", creds_changed["password_hash"])
    assert not store.verify_password("Adm1nInitialPass!", creds_changed["password_hash"])

    # 3. Ứng dụng khởi động lại (restart container) với biến môi trường cũ hoặc mới
    # SEC-04: Mật khẩu mới của Admin PHẢI ĐƯỢC BẢO TOÀN, không bị ghi đè về INITIAL_ADMIN_PASSWORD
    store.initialize_store()
    creds_after_restart = store.get_user_credentials("admin")
    assert creds_after_restart is not None
    assert store.verify_password("AdminChangedSecret999!", creds_after_restart["password_hash"])
    assert not store.verify_password("Adm1nInitialPass!", creds_after_restart["password_hash"])


def test_verify_password_rejects_plaintext_and_malformed_hashes() -> None:
    # SEC-02: Mật khẩu plaintext lưu trong CSDL không bao giờ được chấp nhận xác thực
    assert not store.verify_password("Thinh@321", "Thinh@321")
    assert not store.verify_password("admin", "admin")
    assert not store.verify_password("password", "password")

    # Thuật toán không hỗ trợ, hash dị dạng, salt không hợp lệ hoặc chuỗi rỗng phải bị từ chối an toàn
    assert not store.verify_password("password", "md5$1234$5678")
    assert not store.verify_password("password", "pbkdf2_sha256$invalid_hex$1234")
    assert not store.verify_password("password", "pbkdf2_sha256$short")
    assert not store.verify_password("password", "")
    assert not store.verify_password("password", None)  # type: ignore[arg-type]

    # Mật khẩu băm chuẩn PBKDF2 xác thực chính xác
    hashed = store._password_hash("ValidPass123!")
    assert store.verify_password("ValidPass123!", hashed)
    assert not store.verify_password("WrongPass123!", hashed)


def test_verify_and_consume_reset_token_rejects_inactive_user(isolated_database: Path) -> None:
    # SEC-09: Tài khoản bị vô hiệu hóa (is_active=0) không được phép dùng reset token để đổi mật khẩu
    store.initialize_store()
    store.create_user("locked_user", "OldSecretPass123!", "user", email="locked@opsmind.internal")

    token = store.create_password_reset_token("locked_user", expires_minutes=15)
    assert token is not None

    # Khóa tài khoản
    store.update_user("locked_user", {"is_active": 0})
    creds = store.get_user_credentials("locked_user")
    assert creds is not None and creds["is_active"] == 0

    # Thử dùng token khi tài khoản bị khóa -> phải bị từ chối
    assert store.verify_and_consume_reset_token(token) is None
    assert store.reset_password_with_token(token, "NewSecretPass456!") is None

    # Mật khẩu cũ vẫn không đổi
    creds_unchanged = store.get_user_credentials("locked_user")
    assert creds_unchanged is not None
    assert store.verify_password("OldSecretPass123!", creds_unchanged["password_hash"])


def test_list_tickets_and_knowledge_escape_like_wildcard(isolated_database: Path) -> None:
    # FIX-P1-05: Tìm kiếm với % và _ không bị hiểu lầm thành SQL wildcard
    store.initialize_store()
    store.create_user("alice", "AlicePass123456!", "user")

    # Tạo 2 ticket: một cái có ký tự 50%, một cái có 500
    t1 = store.create_ticket("Resource 50% threshold reached", "System alert 50%", "software", "medium", "alice")
    t2 = store.create_ticket("Resource 500MB exceeded", "System alert 500MB", "software", "medium", "alice")

    # Tìm kiếm chính xác "50%" -> chỉ match t1, không match t2
    matches_50pct = store.list_tickets("admin", "admin", query="50%")
    match_ids = [t["id"] for t in matches_50pct]
    assert t1["id"] in match_ids
    assert t2["id"] not in match_ids

    # Tìm kiếm "99%" -> không match cái nào
    matches_none = store.list_tickets("admin", "admin", query="99%")
    assert len(matches_none) == 0

def test_delete_user_and_anonymize_preserves_ticket_and_comment_history(isolated_database: Path) -> None:
    store.initialize_store()
    store.create_user("bob_anonymize", "BobPass123456!", "user", email="bob@example.com")

    # Bob creates a ticket and writes a comment
    ticket = store.create_ticket("Máy in hỏng cổng USB", "Không nhận cáp USB máy in Canon", "hardware", "medium", "bob_anonymize")
    t_after_comment = store.add_comment(ticket["id"], "bob_anonymize", "Tôi đã thử đổi dây cáp khác nhưng vẫn không nhận.")

    assert ticket["requester"] == "bob_anonymize"
    assert t_after_comment["comments"][0]["author"] == "bob_anonymize"

    # Bob deletes his account
    result = store.delete_user_and_anonymize("bob_anonymize")
    assert result is True

    # User bob is deleted from users table
    assert store.get_user_credentials("bob_anonymize") is None
    assert not any(u["username"] == "bob_anonymize" for u in store.list_users())

    # Tickets and comments are preserved with anonymous authorship
    updated_ticket = store.get_ticket(ticket["id"])
    assert updated_ticket is not None
    assert updated_ticket["title"] == "Máy in hỏng cổng USB"
    assert updated_ticket["requester"] == store.ANONYMIZED_USER

    comments = updated_ticket["comments"]
    assert len(comments) == 1
    assert comments[0]["author"] == store.ANONYMIZED_USER
    assert comments[0]["comment"] == "Tôi đã thử đổi dây cáp khác nhưng vẫn không nhận."

    # Cannot delete sole admin
    with pytest.raises(ValueError, match="Admin"):
        store.delete_user_and_anonymize("admin")

