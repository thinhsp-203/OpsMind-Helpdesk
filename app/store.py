from __future__ import annotations

import hashlib
import hmac
import secrets
import sqlite3
from collections import Counter
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import psycopg
from psycopg.rows import dict_row

from app.config import (
    DATABASE_URL,
    DATABASE_PATH,
    DEMO_MODE,
    INITIAL_ADMIN_PASSWORD,
    INITIAL_ADMIN_USERNAME,
)

PRIORITY_HOURS = {"low": 48, "medium": 24, "high": 8, "urgent": 2}
TRANSITIONS = {
    "new": {"in_progress"},
    "in_progress": {"pending_waiting_user", "resolved", "escalated"},
    "pending_waiting_user": {"in_progress"},
    "resolved": {"in_progress", "closed"},
    "escalated": {"in_progress"},
    "closed": set(),
}
PASSWORD_ITERATIONS = 180_000
_database_path = Path(DATABASE_PATH)
_database_url = DATABASE_URL
DatabaseError = (sqlite3.Error, psycopg.Error)
DatabaseIntegrityError = (sqlite3.IntegrityError, psycopg.IntegrityError)


class _PostgresConnection:
    def __init__(self, connection: psycopg.Connection) -> None:
        self._connection = connection

    def __enter__(self) -> "_PostgresConnection":
        return self

    def __exit__(self, exc_type: object, exc: object, traceback: object) -> None:
        try:
            if exc_type is None:
                self._connection.commit()
            else:
                self._connection.rollback()
        finally:
            self._connection.close()

    def execute(self, query: str, parameters: tuple[Any, ...] = ()) -> psycopg.Cursor:
        return self._connection.execute(query.replace("?", "%s"), parameters)

    def executemany(
        self, query: str, parameters: list[tuple[Any, ...]]
    ) -> psycopg.Cursor:
        return self._connection.cursor().executemany(query.replace("?", "%s"), parameters)

    def executescript(self, script: str) -> None:
        for statement in script.split(";"):
            if statement.strip():
                self.execute(statement)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _connect() -> sqlite3.Connection | _PostgresConnection:
    if _database_url:
        url = _database_url.replace("postgres://", "postgresql://", 1)
        if "@localhost:" in url:
            url = url.replace("@localhost:", "@127.0.0.1:")
        return _PostgresConnection(psycopg.connect(url, row_factory=dict_row))
    _database_path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(_database_path, timeout=15)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    return connection


def check_database() -> None:
    with _connect() as connection:
        connection.execute("SELECT 1").fetchone()


def _password_hash(password: str, salt: bytes | None = None) -> str:
    salt = salt or secrets.token_bytes(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, PASSWORD_ITERATIONS)
    return f"pbkdf2_sha256${salt.hex()}${digest.hex()}"


def verify_password(password: str, encoded: str) -> bool:
    try:
        algorithm, salt_hex, digest_hex = encoded.split("$", 2)
        if algorithm != "pbkdf2_sha256":
            return False
        candidate = _password_hash(password, bytes.fromhex(salt_hex)).split("$", 2)[2]
    except (ValueError, TypeError):
        return False
    return hmac.compare_digest(candidate, digest_hex)


def initialize_store() -> None:
    with _connect() as connection:
        schema = """
            CREATE TABLE IF NOT EXISTS users (
                username TEXT PRIMARY KEY,
                password_hash TEXT NOT NULL,
                role TEXT NOT NULL CHECK (role IN ('user', 'agent', 'admin')),
                full_name TEXT NOT NULL DEFAULT '',
                email TEXT NOT NULL DEFAULT '',
                department TEXT NOT NULL DEFAULT '',
                phone TEXT NOT NULL DEFAULT '',
                is_active INTEGER NOT NULL DEFAULT 1 CHECK (is_active IN (0, 1))
            );
            CREATE TABLE IF NOT EXISTS tickets (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                description TEXT NOT NULL,
                category TEXT NOT NULL,
                priority TEXT NOT NULL CHECK (priority IN ('low', 'medium', 'high', 'urgent')),
                requester TEXT NOT NULL REFERENCES users(username),
                assignee TEXT REFERENCES users(username),
                status TEXT NOT NULL CHECK (
                    status IN ('new', 'in_progress', 'pending_waiting_user', 'resolved', 'closed', 'escalated')
                ),
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                sla_deadline TEXT NOT NULL,
                archived_at TEXT
            );
            CREATE TABLE IF NOT EXISTS comments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                ticket_id INTEGER NOT NULL REFERENCES tickets(id) ON DELETE CASCADE,
                author TEXT NOT NULL REFERENCES users(username),
                comment TEXT NOT NULL,
                created_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS audit_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                ticket_id INTEGER NOT NULL REFERENCES tickets(id) ON DELETE CASCADE,
                actor TEXT NOT NULL REFERENCES users(username),
                event TEXT NOT NULL,
                from_status TEXT,
                to_status TEXT,
                details TEXT NOT NULL DEFAULT '',
                timestamp TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS ticket_attachments (
                id TEXT PRIMARY KEY,
                ticket_id INTEGER NOT NULL REFERENCES tickets(id) ON DELETE CASCADE,
                original_name TEXT NOT NULL,
                stored_name TEXT NOT NULL UNIQUE,
                content_type TEXT NOT NULL,
                size_bytes INTEGER NOT NULL,
                uploaded_by TEXT NOT NULL REFERENCES users(username),
                created_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS chat_sessions (
                id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL REFERENCES users(username),
                created_at TEXT NOT NULL,
                last_message_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS chat_messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT NOT NULL REFERENCES chat_sessions(id) ON DELETE CASCADE,
                role TEXT NOT NULL CHECK (role IN ('user', 'assistant')),
                content TEXT NOT NULL,
                sources TEXT NOT NULL DEFAULT '[]',
                feedback TEXT CHECK (feedback IN ('up', 'down') OR feedback IS NULL),
                created_at TEXT NOT NULL
            );
            CREATE INDEX IF NOT EXISTS idx_tickets_requester ON tickets(requester);
            CREATE INDEX IF NOT EXISTS idx_tickets_status ON tickets(status);
            CREATE INDEX IF NOT EXISTS idx_comments_ticket ON comments(ticket_id);
            CREATE INDEX IF NOT EXISTS idx_audit_ticket ON audit_logs(ticket_id);
            CREATE INDEX IF NOT EXISTS idx_attachments_ticket ON ticket_attachments(ticket_id);
            CREATE INDEX IF NOT EXISTS idx_chat_sessions_user ON chat_sessions(user_id, last_message_at);
            CREATE INDEX IF NOT EXISTS idx_chat_messages_session ON chat_messages(session_id, id);
            """
        if _database_url:
            schema = schema.replace("INTEGER PRIMARY KEY AUTOINCREMENT", "SERIAL PRIMARY KEY")
        connection.executescript(schema)
        if _database_url:
            for table, column, definition in (
                ("tickets", "archived_at", "TEXT"),
                ("tickets", "resolved_at", "TEXT"),
                ("tickets", "closed_at", "TEXT"),
                ("tickets", "rating", "INTEGER"),
                ("tickets", "rating_comment", "TEXT"),
                ("users", "full_name", "TEXT NOT NULL DEFAULT ''"),
                ("users", "email", "TEXT NOT NULL DEFAULT ''"),
                ("users", "department", "TEXT NOT NULL DEFAULT ''"),
                ("users", "phone", "TEXT NOT NULL DEFAULT ''"),
                ("users", "is_active", "INTEGER NOT NULL DEFAULT 1"),
            ):
                connection.execute(
                    f"ALTER TABLE {table} ADD COLUMN IF NOT EXISTS {column} {definition}"
                )
        else:
            ticket_columns = {
                row["name"] for row in connection.execute("PRAGMA table_info(tickets)").fetchall()
            }
            if "archived_at" not in ticket_columns:
                connection.execute("ALTER TABLE tickets ADD COLUMN archived_at TEXT")
            user_columns = {
                row["name"] for row in connection.execute("PRAGMA table_info(users)").fetchall()
            }
            for column, definition in (
                ("full_name", "TEXT NOT NULL DEFAULT ''"),
                ("email", "TEXT NOT NULL DEFAULT ''"),
                ("department", "TEXT NOT NULL DEFAULT ''"),
                ("phone", "TEXT NOT NULL DEFAULT ''"),
                ("is_active", "INTEGER NOT NULL DEFAULT 1"),
            ):
                if column not in user_columns:
                    connection.execute(
                        f"ALTER TABLE users ADD COLUMN {column} {definition}"  # noqa: S608
                    )
            for column, definition in (
                ("resolved_at", "TEXT"),
                ("closed_at", "TEXT"),
                ("rating", "INTEGER"),
                ("rating_comment", "TEXT"),
            ):
                if column not in ticket_columns:
                    connection.execute(
                        f"ALTER TABLE tickets ADD COLUMN {column} {definition}"  # noqa: S608
                    )
            ticket_schema = connection.execute(
                "SELECT sql FROM sqlite_master WHERE type = 'table' AND name = 'tickets'"
            ).fetchone()[0]
            if "pending_waiting_user" not in ticket_schema:
                connection.execute("PRAGMA foreign_keys = OFF")
                connection.executescript(
                    """
                CREATE TABLE tickets_replacement (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    title TEXT NOT NULL,
                    description TEXT NOT NULL,
                    category TEXT NOT NULL,
                    priority TEXT NOT NULL CHECK (priority IN ('low', 'medium', 'high', 'urgent')),
                    requester TEXT NOT NULL REFERENCES users(username),
                    assignee TEXT REFERENCES users(username),
                    status TEXT NOT NULL CHECK (
                        status IN ('new', 'in_progress', 'pending_waiting_user', 'resolved', 'closed', 'escalated')
                    ),
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    sla_deadline TEXT NOT NULL,
                    archived_at TEXT,
                    resolved_at TEXT,
                    closed_at TEXT,
                    rating INTEGER,
                    rating_comment TEXT
                );
                INSERT INTO tickets_replacement
                    (id, title, description, category, priority, requester, assignee, status,
                     created_at, updated_at, sla_deadline, archived_at, resolved_at, closed_at,
                     rating, rating_comment)
                SELECT id, title, description, category, priority, requester, assignee, status,
                       created_at, updated_at, sla_deadline, archived_at, resolved_at, closed_at,
                       rating, rating_comment
                FROM tickets;
                DROP TABLE tickets;
                ALTER TABLE tickets_replacement RENAME TO tickets;
                CREATE INDEX IF NOT EXISTS idx_tickets_requester ON tickets(requester);
                CREATE INDEX IF NOT EXISTS idx_tickets_status ON tickets(status);
                    """
                )
                connection.execute("PRAGMA foreign_keys = ON")
        if not DEMO_MODE:
            demo_credentials = {"user": "user", "agent": "agent", "admin": "admin"}
            existing_demo_users = connection.execute(
                "SELECT username, password_hash FROM users WHERE username IN (?, ?, ?)",
                tuple(demo_credentials),
            ).fetchall()
            if any(
                verify_password(demo_credentials[row["username"]], row["password_hash"])
                for row in existing_demo_users
            ):
                raise RuntimeError(
                    "Demo credentials are present in this database. Use a fresh non-demo "
                    "database or change the demo passwords before startup."
                )
        if connection.execute("SELECT COUNT(*) AS count FROM users").fetchone()["count"] == 0:
            if DEMO_MODE:
                demo_users = (
                    ("user", "user", "user"),
                    ("agent", "agent", "agent"),
                    ("admin", "admin", "admin"),
                )
                connection.executemany(
                    "INSERT INTO users (username, password_hash, role) VALUES (?, ?, ?)",
                    [(name, _password_hash(password), role) for name, password, role in demo_users],
                )
            elif (
                INITIAL_ADMIN_USERNAME
                and len(INITIAL_ADMIN_PASSWORD) >= 12
                and INITIAL_ADMIN_USERNAME.lower() != INITIAL_ADMIN_PASSWORD.lower()
            ):
                connection.execute(
                    "INSERT INTO users (username, password_hash, role) VALUES (?, ?, 'admin')",
                    (INITIAL_ADMIN_USERNAME, _password_hash(INITIAL_ADMIN_PASSWORD)),
                )
            else:
                raise RuntimeError(
                    "Provision INITIAL_ADMIN_USERNAME and a unique INITIAL_ADMIN_PASSWORD "
                    "of at least 12 characters for the first non-demo startup."
                )


def reset_store() -> None:
    with _connect() as connection:
        if _database_url:
            connection.execute(
                "TRUNCATE TABLE audit_logs, comments, tickets, chat_messages, chat_sessions, "
                "ticket_attachments, users RESTART IDENTITY CASCADE"
            )
            if DEMO_MODE:
                demo_users = (
                    ("user", "user", "user"),
                    ("agent", "agent", "agent"),
                    ("admin", "admin", "admin"),
                )
                connection.executemany(
                    "INSERT INTO users (username, password_hash, role) VALUES (?, ?, ?)",
                    [(name, _password_hash(password), role) for name, password, role in demo_users],
                )
            return
        connection.execute("DELETE FROM audit_logs")
        connection.execute("DELETE FROM comments")
        connection.execute("DELETE FROM tickets")
        connection.execute("DELETE FROM chat_sessions")
        connection.execute("DELETE FROM users")
        connection.execute(
            "DELETE FROM sqlite_sequence WHERE name IN ('tickets', 'comments', 'audit_logs')"
        )
    initialize_store()


def get_user_credentials(username: str) -> dict[str, Any] | None:
    with _connect() as connection:
        row = connection.execute(
            "SELECT username, password_hash, role, full_name, email, department, phone, is_active "
            "FROM users WHERE username = ?",
            (username,),
        ).fetchone()
    return dict(row) if row else None


def count_active_admins() -> int:
    with _connect() as connection:
        return int(
            connection.execute(
                "SELECT COUNT(*) AS count FROM users WHERE role = 'admin' AND is_active = 1"
            ).fetchone()["count"]
        )


def list_users() -> list[dict[str, Any]]:
    with _connect() as connection:
        rows = connection.execute(
            "SELECT username, role, full_name, email, department, phone, is_active "
            "FROM users ORDER BY role, username"
        ).fetchall()
    return [dict(row) for row in rows]


def list_staff() -> list[dict[str, str]]:
    with _connect() as connection:
        rows = connection.execute(
            "SELECT username, role FROM users WHERE role IN ('agent', 'admin') "
            "AND is_active = 1 ORDER BY username"
        ).fetchall()
    return [dict(row) for row in rows]


def create_user(
    username: str,
    password: str,
    role: str,
    full_name: str = "",
    email: str = "",
    department: str = "",
    phone: str = "",
) -> dict[str, str]:
    with _connect() as connection:
        try:
            connection.execute(
                "INSERT INTO users "
                "(username, password_hash, role, full_name, email, department, phone) "
                "VALUES (?, ?, ?, ?, ?, ?, ?)",
                (username, _password_hash(password), role, full_name, email, department, phone),
            )
        except DatabaseIntegrityError as exc:
            raise ValueError("Username already exists.") from exc
    return {"username": username, "role": role}


def update_user(username: str, updates: dict[str, Any]) -> dict[str, Any] | None:
    allowed = {"role", "full_name", "email", "department", "phone", "is_active"}
    if not updates or not set(updates).issubset(allowed):
        raise ValueError("Invalid user update fields")
    normalized = dict(updates)
    if "is_active" in normalized:
        normalized["is_active"] = int(normalized["is_active"])
    with _connect() as connection:
        existing = connection.execute(
            "SELECT username, role, is_active FROM users WHERE username = ?", (username,)
        ).fetchone()
        if existing is None:
            return None
        leaving_active_admin = (
            existing["role"] == "admin"
            and existing["is_active"]
            and (normalized.get("role", "admin") != "admin" or normalized.get("is_active") == 0)
        )
        if leaving_active_admin:
            active_admins = connection.execute(
                "SELECT COUNT(*) AS count FROM users WHERE role = 'admin' AND is_active = 1"
            ).fetchone()["count"]
            if active_admins <= 1:
                raise ValueError("Cannot disable the last active administrator")
        fields = ", ".join(f"{field} = ?" for field in normalized)
        connection.execute(
            f"UPDATE users SET {fields} WHERE username = ?",  # noqa: S608
            (*normalized.values(), username),
        )
        row = connection.execute(
            "SELECT username, role, full_name, email, department, phone, is_active "
            "FROM users WHERE username = ?",
            (username,),
        ).fetchone()
    return dict(row)


def _ticket_dict(connection: sqlite3.Connection, row: sqlite3.Row) -> dict[str, Any]:
    ticket = dict(row)
    ticket["comments"] = [
        dict(comment)
        for comment in connection.execute(
            "SELECT author, comment, created_at AS timestamp FROM comments "
            "WHERE ticket_id = ? ORDER BY id",
            (ticket["id"],),
        )
    ]
    ticket["attachments"] = [
        dict(attachment)
        for attachment in connection.execute(
            "SELECT id, original_name, content_type, size_bytes, uploaded_by, created_at "
            "FROM ticket_attachments WHERE ticket_id = ? ORDER BY created_at",
            (ticket["id"],),
        )
    ]
    return ticket


def _record_audit(
    connection: sqlite3.Connection,
    ticket_id: int,
    actor: str,
    event: str,
    from_status: str | None,
    to_status: str | None,
    details: str = "",
) -> None:
    connection.execute(
        """
        INSERT INTO audit_logs
            (ticket_id, actor, event, from_status, to_status, details, timestamp)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        (ticket_id, actor, event, from_status, to_status, details, _now()),
    )


def create_ticket(
    title: str, description: str, category: str, priority: str, requester: str
) -> dict[str, Any]:
    now = datetime.now(timezone.utc)
    deadline = now + timedelta(hours=PRIORITY_HOURS[priority])
    with _connect() as connection:
        insert_sql = """
            INSERT INTO tickets
                (title, description, category, priority, requester, status, created_at, updated_at, sla_deadline)
            VALUES (?, ?, ?, ?, ?, 'new', ?, ?, ?)
        """
        parameters = (
            title, description, category, priority, requester,
            now.isoformat(), now.isoformat(), deadline.isoformat(),
        )
        if _database_url:
            ticket_id = int(
                connection.execute(insert_sql + " RETURNING id", parameters).fetchone()["id"]
            )
        else:
            cursor = connection.execute(
                insert_sql, parameters
            )
            ticket_id = int(cursor.lastrowid)
        _record_audit(connection, ticket_id, requester, "created", None, "new")
        row = connection.execute("SELECT * FROM tickets WHERE id = ?", (ticket_id,)).fetchone()
        return _ticket_dict(connection, row)


def list_tickets(
    username: str,
    role: str,
    status: str | None = None,
    category: str | None = None,
    query: str | None = None,
    from_date: str | None = None,
    to_date: str | None = None,
) -> list[dict[str, Any]]:
    conditions: list[str] = []
    parameters: list[Any] = []
    if role == "user":
        conditions.append("requester = ?")
        parameters.append(username)
    if status:
        conditions.append("status = ?")
        parameters.append(status)
    if category:
        conditions.append("category = ?")
        parameters.append(category)
    if query:
        conditions.append("(title LIKE ? OR description LIKE ?)")
        parameters.extend([f"%{query}%", f"%{query}%"])
    if from_date:
        conditions.append("substr(created_at, 1, 10) >= ?")
        parameters.append(from_date)
    if to_date:
        conditions.append("substr(created_at, 1, 10) <= ?")
        parameters.append(to_date)
    conditions.insert(0, "archived_at IS NULL")
    where_clause = f"WHERE {' AND '.join(conditions)}"
    with _connect() as connection:
        rows = connection.execute(
            f"SELECT * FROM tickets {where_clause} ORDER BY updated_at DESC, id DESC",  # noqa: S608
            parameters,
        ).fetchall()
        return [_ticket_dict(connection, row) for row in rows]


def get_ticket(ticket_id: int) -> dict[str, Any] | None:
    with _connect() as connection:
        row = connection.execute(
            "SELECT * FROM tickets WHERE id = ? AND archived_at IS NULL", (ticket_id,)
        ).fetchone()
        return _ticket_dict(connection, row) if row else None


def update_ticket_fields(
    ticket_id: int,
    actor: str,
    updates: dict[str, str],
) -> dict[str, Any]:
    allowed = {"title", "description", "category", "priority"}
    if not updates or not set(updates).issubset(allowed):
        raise ValueError("Invalid ticket update fields")
    with _connect() as connection:
        row = connection.execute(
            "SELECT * FROM tickets WHERE id = ? AND archived_at IS NULL", (ticket_id,)
        ).fetchone()
        if row is None:
            raise LookupError("Ticket not found")
        if row["status"] == "closed":
            raise ValueError("Closed tickets cannot be edited")
        timestamp = _now()
        values = dict(updates)
        values["updated_at"] = timestamp
        if "priority" in updates:
            values["sla_deadline"] = (
                datetime.now(timezone.utc) + timedelta(hours=PRIORITY_HOURS[updates["priority"]])
            ).isoformat()
        set_clause = ", ".join(f"{field} = ?" for field in values)
        connection.execute(
            f"UPDATE tickets SET {set_clause} WHERE id = ?",  # noqa: S608
            (*values.values(), ticket_id),
        )
        _record_audit(
            connection,
            ticket_id,
            actor,
            "ticket_updated",
            row["status"],
            row["status"],
            ", ".join(sorted(updates)),
        )
        updated = connection.execute(
            "SELECT * FROM tickets WHERE id = ?", (ticket_id,)
        ).fetchone()
        return _ticket_dict(connection, updated)


def archive_ticket(ticket_id: int, actor: str) -> dict[str, Any]:
    with _connect() as connection:
        row = connection.execute(
            "SELECT * FROM tickets WHERE id = ? AND archived_at IS NULL", (ticket_id,)
        ).fetchone()
        if row is None:
            raise LookupError("Ticket not found")
        timestamp = _now()
        connection.execute(
            "UPDATE tickets SET archived_at = ?, updated_at = ? WHERE id = ?",
            (timestamp, timestamp, ticket_id),
        )
        _record_audit(
            connection,
            ticket_id,
            actor,
            "archived",
            row["status"],
            row["status"],
        )
        archived = connection.execute(
            "SELECT * FROM tickets WHERE id = ?", (ticket_id,)
        ).fetchone()
        return _ticket_dict(connection, archived)


def update_ticket_status(ticket_id: int, new_status: str, actor: str) -> dict[str, Any]:
    with _connect() as connection:
        row = connection.execute(
            "SELECT * FROM tickets WHERE id = ? AND archived_at IS NULL", (ticket_id,)
        ).fetchone()
        if row is None:
            raise LookupError("Ticket not found")
        previous_status = row["status"]
        if new_status not in TRANSITIONS[previous_status]:
            raise ValueError(f"Cannot move ticket from {previous_status} to {new_status}")
        timestamp = _now()
        connection.execute(
            "UPDATE tickets SET status = ?, updated_at = ?, "
            "resolved_at = CASE WHEN ? = 'resolved' THEN ? WHEN ? = 'in_progress' THEN NULL ELSE resolved_at END, "
            "closed_at = CASE WHEN ? = 'closed' THEN ? ELSE closed_at END WHERE id = ?",
            (new_status, timestamp, new_status, timestamp, new_status, new_status, timestamp, ticket_id),
        )
        _record_audit(connection, ticket_id, actor, "status_changed", previous_status, new_status)
        updated = connection.execute("SELECT * FROM tickets WHERE id = ?", (ticket_id,)).fetchone()
        return _ticket_dict(connection, updated)


def assign_ticket(ticket_id: int, assignee: str, actor: str) -> dict[str, Any]:
    with _connect() as connection:
        row = connection.execute(
            "SELECT * FROM tickets WHERE id = ? AND archived_at IS NULL", (ticket_id,)
        ).fetchone()
        if row is None:
            raise LookupError("Ticket not found")
        timestamp = _now()
        connection.execute(
            "UPDATE tickets SET assignee = ?, updated_at = ? WHERE id = ?",
            (assignee, timestamp, ticket_id),
        )
        _record_audit(connection, ticket_id, actor, "assigned", row["status"], row["status"], assignee)
        updated = connection.execute("SELECT * FROM tickets WHERE id = ?", (ticket_id,)).fetchone()
        return _ticket_dict(connection, updated)


def add_comment(ticket_id: int, author: str, comment: str) -> dict[str, Any]:
    with _connect() as connection:
        row = connection.execute(
            "SELECT * FROM tickets WHERE id = ? AND archived_at IS NULL", (ticket_id,)
        ).fetchone()
        if row is None:
            raise LookupError("Ticket not found")
        timestamp = _now()
        connection.execute(
            "INSERT INTO comments (ticket_id, author, comment, created_at) VALUES (?, ?, ?, ?)",
            (ticket_id, author, comment, timestamp),
        )
        next_status = row["status"]
        if author == row["requester"] and row["status"] == "pending_waiting_user":
            next_status = "in_progress"
        connection.execute(
            "UPDATE tickets SET updated_at = ?, status = ?, "
            "resolved_at = CASE WHEN ? = 'in_progress' THEN NULL ELSE resolved_at END WHERE id = ?",
            (timestamp, next_status, next_status, ticket_id),
        )
        if next_status != row["status"]:
            _record_audit(
                connection,
                ticket_id,
                author,
                "status_changed",
                row["status"],
                next_status,
                "Người gửi đã bổ sung thông tin",
            )
        _record_audit(connection, ticket_id, author, "comment_added", row["status"], row["status"])
        updated = connection.execute("SELECT * FROM tickets WHERE id = ?", (ticket_id,)).fetchone()
        return _ticket_dict(connection, updated)


def add_attachment(
    ticket_id: int,
    attachment_id: str,
    original_name: str,
    stored_name: str,
    content_type: str,
    size_bytes: int,
    uploaded_by: str,
) -> dict[str, Any]:
    with _connect() as connection:
        row = connection.execute(
            "SELECT status FROM tickets WHERE id = ? AND archived_at IS NULL", (ticket_id,)
        ).fetchone()
        if row is None:
            raise LookupError("Ticket not found")
        timestamp = _now()
        connection.execute(
            "INSERT INTO ticket_attachments "
            "(id, ticket_id, original_name, stored_name, content_type, size_bytes, uploaded_by, created_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (attachment_id, ticket_id, original_name, stored_name, content_type, size_bytes, uploaded_by, timestamp),
        )
        _record_audit(connection, ticket_id, uploaded_by, "attachment_added", row["status"], row["status"], original_name)
        return {
            "id": attachment_id,
            "ticket_id": ticket_id,
            "original_name": original_name,
            "content_type": content_type,
            "size_bytes": size_bytes,
            "uploaded_by": uploaded_by,
            "created_at": timestamp,
        }


def get_attachment(attachment_id: str) -> dict[str, Any] | None:
    with _connect() as connection:
        row = connection.execute(
            "SELECT id, ticket_id, original_name, stored_name, content_type, size_bytes "
            "FROM ticket_attachments WHERE id = ?",
            (attachment_id,),
        ).fetchone()
    return dict(row) if row else None


def rate_ticket(ticket_id: int, rating: int, comment: str | None, actor: str) -> dict[str, Any]:
    with _connect() as connection:
        row = connection.execute(
            "SELECT status, requester FROM tickets WHERE id = ? AND archived_at IS NULL",
            (ticket_id,),
        ).fetchone()
        if row is None:
            raise LookupError("Ticket not found")
        if row["status"] not in {"resolved", "closed"}:
            raise ValueError("Only resolved tickets can be rated")
        if row["requester"] != actor:
            raise PermissionError("Only the requester can rate this ticket")
        connection.execute(
            "UPDATE tickets SET rating = ?, rating_comment = ?, updated_at = ? WHERE id = ?",
            (rating, comment, _now(), ticket_id),
        )
        _record_audit(connection, ticket_id, actor, "rated", row["status"], row["status"], str(rating))
        updated = connection.execute(
            "SELECT * FROM tickets WHERE id = ?", (ticket_id,)
        ).fetchone()
        return _ticket_dict(connection, updated)


def save_chat_exchange(
    username: str,
    session_id: str | None,
    question: str,
    answer: str,
    sources: list[dict[str, str]],
) -> str:
    import json
    import uuid

    chat_id = session_id or str(uuid.uuid4())
    timestamp = _now()
    with _connect() as connection:
        if session_id:
            existing = connection.execute(
                "SELECT id FROM chat_sessions WHERE id = ? AND user_id = ?",
                (session_id, username),
            ).fetchone()
            if existing is None:
                raise LookupError("Chat session not found")
        else:
            connection.execute(
                "INSERT INTO chat_sessions (id, user_id, created_at, last_message_at) VALUES (?, ?, ?, ?)",
                (chat_id, username, timestamp, timestamp),
            )
        connection.executemany(
            "INSERT INTO chat_messages (session_id, role, content, sources, created_at) VALUES (?, ?, ?, ?, ?)",
            [
                (chat_id, "user", question, "[]", timestamp),
                (chat_id, "assistant", answer, json.dumps(sources, ensure_ascii=False), timestamp),
            ],
        )
        connection.execute(
            "UPDATE chat_sessions SET last_message_at = ? WHERE id = ?", (timestamp, chat_id)
        )
    return chat_id


def list_chat_sessions(username: str) -> list[dict[str, Any]]:
    with _connect() as connection:
        rows = connection.execute(
            "SELECT s.id, s.created_at, s.last_message_at, "
            "(SELECT content FROM chat_messages m WHERE m.session_id = s.id "
            "AND m.role = 'user' ORDER BY m.id LIMIT 1) AS first_question "
            "FROM chat_sessions s WHERE s.user_id = ? ORDER BY s.last_message_at DESC",
            (username,),
        ).fetchall()
    return [dict(row) for row in rows]


def get_chat_session(username: str, session_id: str) -> dict[str, Any] | None:
    import json

    with _connect() as connection:
        session = connection.execute(
            "SELECT id, created_at, last_message_at FROM chat_sessions WHERE id = ? AND user_id = ?",
            (session_id, username),
        ).fetchone()
        if session is None:
            return None
        messages = connection.execute(
            "SELECT id, role, content, sources, feedback, created_at FROM chat_messages "
            "WHERE session_id = ? ORDER BY id",
            (session_id,),
        ).fetchall()
    result = dict(session)
    result["messages"] = []
    for row in messages:
        message = dict(row)
        message["sources"] = json.loads(message["sources"])
        result["messages"].append(message)
    return result


def set_chat_feedback(username: str, message_id: int, feedback: str) -> bool:
    with _connect() as connection:
        cursor = connection.execute(
            "UPDATE chat_messages SET feedback = ? WHERE id = ? AND role = 'assistant' "
            "AND session_id IN (SELECT id FROM chat_sessions WHERE user_id = ?)",
            (feedback, message_id, username),
        )
    return cursor.rowcount == 1


def get_ticket_audit(ticket_id: int) -> list[dict[str, Any]]:
    with _connect() as connection:
        rows = connection.execute(
            "SELECT actor, event, from_status, to_status, details, timestamp "
            "FROM audit_logs WHERE ticket_id = ? ORDER BY id DESC",
            (ticket_id,),
        ).fetchall()
        return [dict(row) for row in rows]


def get_analytics() -> dict[str, Any]:
    now = _now()
    with _connect() as connection:
        total = connection.execute(
            "SELECT COUNT(*) AS count FROM tickets WHERE archived_at IS NULL"
        ).fetchone()["count"]
        statuses = {
            row["status"]: row["count"]
            for row in connection.execute(
                "SELECT status, COUNT(*) AS count FROM tickets "
                "WHERE archived_at IS NULL GROUP BY status"
            )
        }
        categories = {
            row["category"]: row["count"]
            for row in connection.execute(
                "SELECT category, COUNT(*) AS count FROM tickets "
                "WHERE archived_at IS NULL GROUP BY category"
            )
        }
        overdue = connection.execute(
            "SELECT COUNT(*) AS count FROM tickets WHERE archived_at IS NULL "
            "AND status NOT IN ('resolved', 'closed') AND sla_deadline < ?",
            (now,),
        ).fetchone()["count"]
        recent = [
            dict(row)
            for row in connection.execute(
                "SELECT ticket_id, actor, event, from_status, to_status, timestamp "
                "FROM audit_logs JOIN tickets ON tickets.id = audit_logs.ticket_id "
                "WHERE tickets.archived_at IS NULL ORDER BY audit_logs.id DESC LIMIT 8"
            )
        ]
        resolved_rows = connection.execute(
            "SELECT assignee, created_at, resolved_at, sla_deadline FROM tickets "
            "WHERE archived_at IS NULL AND resolved_at IS NOT NULL AND assignee IS NOT NULL"
        ).fetchall()
        rating_row = connection.execute(
            "SELECT AVG(rating) AS average_rating, COUNT(rating) AS rating_count "
            "FROM tickets WHERE archived_at IS NULL"
        ).fetchone()
        cutoff = (datetime.now(timezone.utc).date() - timedelta(days=29)).isoformat()
        created_daily = {
            row["day"]: row["count"]
            for row in connection.execute(
                "SELECT substr(created_at, 1, 10) AS day, COUNT(*) AS count FROM tickets "
                "WHERE archived_at IS NULL AND substr(created_at, 1, 10) >= ? "
                "GROUP BY substr(created_at, 1, 10) ORDER BY day DESC LIMIT 30",
                (cutoff,),
            )
        }

    agent_stats: dict[str, dict[str, Any]] = {}
    resolution_hours: list[float] = []
    for row in resolved_rows:
        created_at = datetime.fromisoformat(row["created_at"])
        resolved_at = datetime.fromisoformat(row["resolved_at"])
        deadline = datetime.fromisoformat(row["sla_deadline"])
        duration = max(0.0, (resolved_at - created_at).total_seconds() / 3600)
        resolution_hours.append(duration)
        stat = agent_stats.setdefault(
            row["assignee"], {"resolved_tickets": 0, "within_sla": 0, "resolution_hours": []}
        )
        stat["resolved_tickets"] += 1
        stat["within_sla"] += int(resolved_at <= deadline)
        stat["resolution_hours"].append(duration)
    agent_performance = [
        {
            "assignee": username,
            "resolved_tickets": values["resolved_tickets"],
            "sla_compliance_percent": round(values["within_sla"] / values["resolved_tickets"] * 100, 1),
            "average_resolution_hours": round(sum(values["resolution_hours"]) / values["resolved_tickets"], 2),
        }
        for username, values in sorted(agent_stats.items())
    ]
    return {
        "total_tickets": total,
        "status_breakdown": statuses,
        "category_breakdown": categories,
        "overdue_tickets": overdue,
        "recent_activity": recent,
        "average_resolution_hours": round(sum(resolution_hours) / len(resolution_hours), 2)
        if resolution_hours
        else None,
        "average_rating": round(rating_row["average_rating"], 2)
        if rating_row["average_rating"] is not None
        else None,
        "rating_count": rating_row["rating_count"],
        "daily_created": created_daily,
        "agent_performance": agent_performance,
    }


def get_agent_analytics(username: str) -> dict[str, Any]:
    now = _now()
    with _connect() as connection:
        rows = connection.execute(
            "SELECT status, created_at, resolved_at, sla_deadline, category "
            "FROM tickets WHERE archived_at IS NULL AND assignee = ?",
            (username,),
        ).fetchall()
    resolved = [row for row in rows if row["resolved_at"]]
    durations = [
        max(
            0.0,
            (
                datetime.fromisoformat(row["resolved_at"])
                - datetime.fromisoformat(row["created_at"])
            ).total_seconds()
            / 3600,
        )
        for row in resolved
    ]
    within_sla = sum(
        datetime.fromisoformat(row["resolved_at"])
        <= datetime.fromisoformat(row["sla_deadline"])
        for row in resolved
    )
    return {
        "assigned_tickets": len(rows),
        "resolved_tickets": len(resolved),
        "average_resolution_hours": round(sum(durations) / len(durations), 2)
        if durations
        else None,
        "sla_compliance_percent": round(within_sla / len(resolved) * 100, 1)
        if resolved
        else None,
        "category_breakdown": dict(Counter(row["category"] for row in rows)),
        "overdue_tickets": sum(
            row["status"] not in {"resolved", "closed"}
            and row["sla_deadline"] < now
            for row in rows
        ),
    }


initialize_store()
