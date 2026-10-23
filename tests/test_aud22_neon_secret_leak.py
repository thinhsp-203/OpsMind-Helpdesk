"""Regression tests for AUD-22: Secret masking and read-only safety in verify_neon.py."""

from pathlib import Path
import io
import os
import sys
from unittest.mock import MagicMock, patch


def test_verify_neon_masks_password_in_all_output() -> None:
    repo = Path(__file__).resolve().parent.parent
    script_path = repo / "scripts/verify_neon.py"

    sentinel_password = "AUD22_SUPER_SECRET_P@SSW0RD_CHECK"  # noqa: S105
    sentinel_url = (
        f"postgresql://ops_user:{sentinel_password}@ep-xyz-pooler.us-east-2.aws.neon.tech/neondb?sslmode=require"
    )

    mock_cursor = MagicMock()
    mock_cursor.fetchone.return_value = {"version": "PostgreSQL 16.2 on x86_64", "count": 10}
    mock_cursor.fetchall.return_value = [
        {"table_name": "users"},
        {"table_name": "tickets"},
        {"table_name": "comments"},
        {"table_name": "audit_logs"},
        {"table_name": "ticket_attachments"},
        {"table_name": "chat_sessions"},
        {"table_name": "chat_messages"},
        {"table_name": "knowledge_documents"},
        {"table_name": "knowledge_versions"},
    ]
    mock_cursor.__enter__.return_value = mock_cursor

    mock_conn = MagicMock()
    mock_conn.cursor.return_value = mock_cursor
    mock_conn.__enter__.return_value = mock_conn
    mock_conn.execute.return_value.fetchone.return_value = {"count": 10}

    captured_stdout = io.StringIO()
    captured_stderr = io.StringIO()
    old_stdout, old_stderr = sys.stdout, sys.stderr
    old_argv = sys.argv

    try:
        sys.stdout = captured_stdout
        sys.stderr = captured_stderr
        sys.argv = ["scripts/verify_neon.py", sentinel_url]

        import importlib.util
        spec = importlib.util.spec_from_file_location("scripts.verify_neon", str(script_path))
        mod = importlib.util.module_from_spec(spec)

        with patch("psycopg.connect", return_value=mock_conn), \
             patch("app.store.initialize_store", return_value=None), \
             patch("app.store.list_knowledge_documents", return_value=[{}] * 30), \
             patch("app.store.list_users", return_value=[{"username": "admin"}]), \
             patch("app.store.create_ticket", return_value={"id": 1, "title": "t"}), \
             patch("app.store.get_ticket", return_value={"id": 1, "title": "t"}), \
             patch("app.store.add_comment", return_value=None), \
             patch("app.store._connect", return_value=mock_conn):
            spec.loader.exec_module(mod)
            exit_code = mod.main()
    finally:
        sys.stdout = old_stdout
        sys.stderr = old_stderr
        sys.argv = old_argv

    stdout_val = captured_stdout.getvalue()
    stderr_val = captured_stderr.getvalue()

    assert exit_code == 0, f"Expected successful run, got exit_code={exit_code}\nOutput:\n{stdout_val}"
    # Sentinel password must never appear in stdout or stderr
    assert sentinel_password not in stdout_val, f"Sentinel password leaked in stdout:\n{stdout_val}"
    assert sentinel_password not in stderr_val, f"Sentinel password leaked in stderr:\n{stderr_val}"
    assert ":***@" in stdout_val, "Masked placeholder ':***@' must appear in output"


def test_verify_neon_safe_check_is_read_only() -> None:
    repo = Path(__file__).resolve().parent.parent
    script_path = repo / "scripts/verify_neon.py"
    sentinel_url = "postgresql://ops_user:pass123@ep-xyz-pooler.us-east-2.aws.neon.tech/neondb?sslmode=require"

    executed_queries: list[str] = []

    mock_cursor = MagicMock()
    def record_execute(query: str, *args: any, **kwargs: any) -> None:
        executed_queries.append(str(query).strip())

    mock_cursor.execute.side_effect = record_execute
    mock_cursor.fetchone.return_value = {"version": "PostgreSQL 16.2 on x86_64", "count": 10}
    mock_cursor.fetchall.return_value = [
        {"table_name": "users"},
        {"table_name": "tickets"},
        {"table_name": "comments"},
        {"table_name": "audit_logs"},
        {"table_name": "ticket_attachments"},
        {"table_name": "chat_sessions"},
        {"table_name": "chat_messages"},
        {"table_name": "knowledge_documents"},
        {"table_name": "knowledge_versions"},
    ]
    mock_cursor.__enter__.return_value = mock_cursor

    mock_conn = MagicMock()
    mock_conn.cursor.return_value = mock_cursor
    mock_conn.execute.side_effect = record_execute
    mock_conn.__enter__.return_value = mock_conn

    captured_stdout = io.StringIO()
    old_stdout = sys.stdout
    old_argv = sys.argv

    try:
        sys.stdout = captured_stdout
        sys.argv = ["scripts/verify_neon.py", sentinel_url]

        import importlib.util
        spec = importlib.util.spec_from_file_location("scripts.verify_neon", str(script_path))
        mod = importlib.util.module_from_spec(spec)

        with patch("psycopg.connect", return_value=mock_conn):
            spec.loader.exec_module(mod)
            exit_code = mod.main()
    finally:
        sys.stdout = old_stdout
        sys.argv = old_argv

    assert exit_code == 0, f"Expected returncode 0 in safe check, got {exit_code}"

    # Verify no DDL or DML write operations in default safe mode
    disallowed_keywords = ("CREATE ", "ALTER ", "DROP ", "INSERT ", "UPDATE ", "DELETE ", "TRUNCATE ")
    for q in executed_queries:
        q_upper = q.upper()
        for kw in disallowed_keywords:
            assert not q_upper.startswith(kw), f"Safe check executed disallowed mutating query: {q}"


def test_importing_verify_neon_does_not_mutate_env_or_trigger_store_init() -> None:
    repo = Path(__file__).resolve().parent.parent
    script_path = repo / "scripts/verify_neon.py"

    original_env = os.environ.get("DATABASE_URL")
    old_argv = sys.argv
    sys.argv = ["scripts/verify_neon.py", "postgresql://fake_user:fake_pass@fake_host/fake_db"]

    try:
        import importlib.util
        spec = importlib.util.spec_from_file_location("scripts.verify_neon_test_import", str(script_path))
        mod = importlib.util.module_from_spec(spec)

        with patch("app.store.initialize_store") as mock_init:
            spec.loader.exec_module(mod)
            assert not mock_init.called, "Importing verify_neon must not invoke store.initialize_store()"

        # os.environ['DATABASE_URL'] should not be modified at import time
        assert os.environ.get("DATABASE_URL") == original_env, (
            "Importing verify_neon must not mutate os.environ['DATABASE_URL']"
        )
    finally:
        sys.argv = old_argv
        if original_env is None:
            os.environ.pop("DATABASE_URL", None)
        else:
            os.environ["DATABASE_URL"] = original_env


def test_sanitize_database_url_helper() -> None:
    repo = Path(__file__).resolve().parent.parent
    import importlib.util
    spec = importlib.util.spec_from_file_location("scripts.verify_neon", str(repo / "scripts/verify_neon.py"))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)

    sanitize = getattr(mod, "sanitize_database_url", None)
    assert sanitize is not None, "sanitize_database_url function must exist in scripts/verify_neon.py"

    raw1 = "postgresql://user:mypassword@ep-xyz.neon.tech/neondb?sslmode=require"
    s1 = sanitize(raw1)
    assert "mypassword" not in s1
    assert "user:***@ep-xyz.neon.tech" in s1
    assert "?sslmode=require" in s1

    raw2 = "postgres://admin:p%40ssw%3Ard@127.0.0.1:5432/helpdesk"
    s2 = sanitize(raw2)
    assert "p%40ssw%3Ard" not in s2
    assert "admin:***@127.0.0.1" in s2

    assert sanitize("") == ""
    assert sanitize("invalid-url") == "invalid-url"
