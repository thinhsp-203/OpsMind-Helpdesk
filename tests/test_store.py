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
