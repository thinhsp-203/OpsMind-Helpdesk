import os

import pytest

from app import store

DATABASE_URL = os.getenv("DATABASE_URL", "")

pytestmark = pytest.mark.skipif(not DATABASE_URL, reason="DATABASE_URL is not configured")


@pytest.fixture(autouse=True)
def setup_postgres_test(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(store, "_database_url", DATABASE_URL)
    monkeypatch.setattr(store, "DEMO_MODE", True)


def test_postgres_schema_is_idempotent_and_ticket_lifecycle_works() -> None:
    store.initialize_store()
    store.initialize_store()
    store.reset_store()

    assert {user["username"] for user in store.list_users()} == {"user", "agent", "admin"}
    ticket = store.create_ticket(
        "PostgreSQL integration test",
        "Ensure a ticket can be created and read from the PostgreSQL backend.",
        "software",
        "medium",
        "user",
    )
    assert ticket["id"] > 0
    assert ticket["status"] == "new"
    assert store.get_ticket(ticket["id"])["title"] == "PostgreSQL integration test"

    store.assign_ticket(ticket["id"], "agent", "admin")
    store.add_comment(ticket["id"], "agent", "Please confirm whether the app is still failing.")
    store.update_ticket_status(ticket["id"], "in_progress", "agent")
    store.update_ticket_status(ticket["id"], "pending_waiting_user", "agent")
    store.update_ticket_status(ticket["id"], "in_progress", "agent")
    store.update_ticket_status(ticket["id"], "pending_waiting_user", "agent")
    waiting = store.add_comment(ticket["id"], "user", "It is still failing.")
    assert waiting["status"] == "in_progress"
    store.update_ticket_fields(
        ticket["id"],
        "agent",
        {"title": "PostgreSQL ticket updated", "description": "The ticket fields were updated."},
    )
    assert store.update_ticket_status(ticket["id"], "resolved", "agent")["status"] == "resolved"
    assert store.rate_ticket(ticket["id"], 5, "Resolved", "user")["rating"] == 5

    attachment = store.add_attachment(
        ticket["id"],
        "attachment-id",
        "diagnostic.txt",
        "stored-diagnostic.txt",
        "text/plain",
        16,
        "user",
    )
    assert store.get_attachment(attachment["id"])["stored_name"] == "stored-diagnostic.txt"

    session_id = store.save_chat_exchange(
        "user",
        None,
        "How do I troubleshoot this?",
        "Check the cited internal runbook.",
        [{"title": "Network", "source": "network.md"}],
    )
    chat = store.get_chat_session("user", session_id)
    assert chat is not None
    assert chat["messages"][1]["sources"] == [{"title": "Network", "source": "network.md"}]
    assert store.set_chat_feedback("user", chat["messages"][1]["id"], "up")
    assert store.get_chat_session("user", session_id)["messages"][1]["feedback"] == "up"

    analytics = store.get_analytics()
    assert analytics["total_tickets"] == 1
    assert analytics["average_rating"] == 5
    assert analytics["agent_performance"][0]["assignee"] == "agent"
    assert store.get_ticket_audit(ticket["id"])
    assert store.list_chat_sessions("user")[0]["id"] == session_id

    # Knowledge documents on PostgreSQL/Neon
    docs = store.list_knowledge_documents()
    assert len(docs) >= 30
    assert any(doc["slug"] == "wifi_network.md" for doc in docs)

    # Custom KB document lifecycle on PostgreSQL
    new_doc = store.create_knowledge_document(
        title="Neon Database SOP",
        category="software",
        tags="database, neon, postgres",
        content="# Neon Database SOP\n\nInstructions for managing Neon serverless database.",
        author="agent",
    )
    assert new_doc["status"] == "draft"
    submitted = store.update_knowledge_document(
        new_doc["id"],
        {"status": "pending_review"},
        actor="agent",
    )
    assert submitted is not None and submitted["status"] == "pending_review"
    approved = store.review_knowledge_document(
        new_doc["id"],
        action="approve",
        reviewer="admin",
    )
    assert approved is not None and approved["status"] == "published"
    versions = store.list_knowledge_versions(new_doc["id"])
    assert len(versions) >= 1

    # Verify repeated executions work without prepared statement caching errors
    for _ in range(10):
        assert store.get_user_credentials("admin") is not None

    store.archive_ticket(ticket["id"], "admin")
    assert store.get_ticket(ticket["id"]) is None
    assert store.get_analytics()["total_tickets"] == 0
    store.reset_store()
    assert store.get_analytics()["total_tickets"] == 0
    assert {user["username"] for user in store.list_users()} == {"user", "agent", "admin"}
    assert len(store.list_knowledge_documents()) >= 30


def test_postgres_password_reset_tokens_lifecycle(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(store, "_database_url", DATABASE_URL)
    store.initialize_store()
    store.reset_store()

    # 1. Update user email on PostgreSQL
    store.update_user("user", {"email": "postgres.user@opsmind.internal"})
    found = store.find_user_for_password_reset("postgres.user@opsmind.internal")
    assert found is not None
    assert found["username"] == "user"

    # 2. Create password reset token on PostgreSQL
    token = store.create_password_reset_token("user", expires_minutes=15)
    assert len(token) >= 32

    # 3. Reset password using the token
    new_pass = "PostgresNewSecurePass2026!"  # noqa: S105
    reset_username = store.reset_password_with_token(token, new_pass)
    assert reset_username == "user"

    # 4. Verify new password works
    creds = store.get_user_credentials("user")
    assert creds is not None
    assert store.verify_password(new_pass, creds["password_hash"])

    # 5. Token reuse must fail (single-use enforcement)
    reused = store.reset_password_with_token(token, "AnotherPassword123!")
    assert reused is None


def test_postgres_login_lockouts_and_security(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(store, "_database_url", DATABASE_URL)
    store.initialize_store()
    store.reset_store()

    test_ip = "192.0.2.1"
    # Initially no lockout
    assert store.get_lockout_remaining_seconds(test_ip) == 0

    # Record 4 failed attempts
    for _ in range(4):
        store.record_failed_login(test_ip)
    assert store.get_lockout_remaining_seconds(test_ip) == 0

    # 5th failed attempt triggers lockout
    store.record_failed_login(test_ip)
    remaining = store.get_lockout_remaining_seconds(test_ip)
    assert remaining > 0

    # Reset clears lockout
    store.reset_failed_logins(test_ip)
    assert store.get_lockout_remaining_seconds(test_ip) == 0


def test_postgres_knowledge_version_history_and_restore(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(store, "_database_url", DATABASE_URL)
    store.initialize_store()
    store.reset_store()

    # Create document
    doc = store.create_knowledge_document(
        title="PostgreSQL SOP",
        category="software",
        tags="database, postgresql",
        content="Version 1 content for PostgreSQL.",
        author="agent",
    )
    doc_id = doc["id"]

    # Update document creates version 2
    store.update_knowledge_document(
        doc_id,
        {"content": "Version 2 updated content with new guidelines."},
        actor="agent",
        change_summary="Update guidelines",
    )

    versions = store.list_knowledge_versions(doc_id)
    assert len(versions) >= 2

    # Restore version 1
    restored = store.restore_knowledge_version(doc_id, version_number=1, actor="admin")
    assert restored is not None
    updated_doc = store.get_knowledge_document(doc_id)
    assert updated_doc is not None
    assert "Version 1 content" in updated_doc["content"]


@pytest.mark.parametrize("change", ["edit", "archive", "reject", "restore", "delete", "publish"])
def test_postgres_kb_changes_reach_independent_warm_reader(change: str, knowledge_reader_process):
    from app.rag import build_retrieval_index, generate_answer, load_knowledge_base

    store.initialize_store()
    store.reset_store()
    with store._connect() as connection:
        connection.execute("UPDATE knowledge_documents SET status = 'archived'")
    load_knowledge_base.cache_clear()
    build_retrieval_index.cache_clear()
    initial = "# VPN FortiClient\nAUD08-INITIAL FortiClient VPN troubleshooting policy"
    revised = "# VPN FortiClient\nAUD08-REVISED FortiClient VPN troubleshooting policy"
    doc = store.create_knowledge_document(
        "VPN Worker Policy", "network", initial,
        status="draft" if change == "publish" else "published", author="admin",
    )
    if change == "restore":
        store.update_knowledge_document(doc["id"], {"content": revised}, "admin")
    question = "Tôi không kết nối được VPN FortiClient"
    assert generate_answer(question)["grounded"] is (change != "publish")
    with knowledge_reader_process() as ask:
        warm = ask(question)
        assert warm["grounded"] is (change != "publish")
        if change == "edit":
            store.update_knowledge_document(doc["id"], {"content": revised}, "admin")
        elif change == "archive":
            store.update_knowledge_document(doc["id"], {"status": "archived"}, "admin")
        elif change in {"reject", "publish"}:
            store.review_knowledge_document(doc["id"], "approve" if change == "publish" else "reject", "admin")
        elif change == "restore":
            store.restore_knowledge_version(doc["id"], 1, "admin")
        else:
            store.delete_knowledge_document(doc["id"])
        # No local cache clear in either process after the committed mutation.
        parent = generate_answer(question)
        remote = ask(question)
        assert remote["pid"] == warm["pid"]
        assert remote["matches"] == parent["matches"]
        assert remote["grounded"] is (change in {"edit", "restore", "publish"})
        if remote["grounded"]:
            marker = "AUD08-REVISED" if change == "edit" else "AUD08-INITIAL"
            assert marker in remote["matches"][0]["content"]
        else:
            assert remote["matches"] == remote["sources"] == []


@pytest.mark.parametrize("operation", ["reset", "consume", "issue"])
def test_postgres_concurrent_reset_operations_have_one_winner(operation: str) -> None:
    from concurrent.futures import ThreadPoolExecutor
    from threading import Barrier

    store.initialize_store()
    store.reset_store()
    token = store.create_password_reset_token("user")
    passwords = ["AUD07-FirstPassword-2026!", "AUD07-SecondPassword-2026!"]
    gate = Barrier(3)

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


def test_postgres_atomic_reset_rolls_back_token_on_password_write_failure() -> None:
    store.initialize_store()
    store.reset_store()
    token = store.create_password_reset_token("user")
    before = store.get_user_credentials("user")
    with store._connect() as connection:
        connection.execute(
            "CREATE OR REPLACE FUNCTION aud07_fail_password_write() RETURNS trigger "
            "LANGUAGE plpgsql AS $$ BEGIN RAISE EXCEPTION 'AUD07 synthetic failure'; END; $$"
        )
    try:
        with store._connect() as connection:
            connection.execute(
                "CREATE TRIGGER aud07_fail_password BEFORE UPDATE OF password_hash ON users "
                "FOR EACH ROW EXECUTE FUNCTION aud07_fail_password_write()"
            )
        with pytest.raises(store.DatabaseError, match="AUD07 synthetic failure"):
            store.reset_password_with_token(token, "AUD07-ResetPassword-2026!")
        assert store.get_user_credentials("user") == before
        with store._connect() as connection:
            row = connection.execute(
                "SELECT used FROM password_reset_tokens WHERE username = 'user'"
            ).fetchone()
            assert row["used"] == 0
    finally:
        with store._connect() as connection:
            connection.execute("DROP TRIGGER IF EXISTS aud07_fail_password ON users")
            connection.execute("DROP FUNCTION aud07_fail_password_write()")
    assert store.reset_password_with_token(token, "AUD07-ResetPassword-2026!") == "user"


def test_postgres_reset_links_are_revoked_on_security_updates() -> None:
    store.initialize_store()
    store.reset_store()
    store.create_user("pg.reset", "AUD06-InitialPassword-2026!", "user")
    token = store.create_password_reset_token("pg.reset")
    store.update_user_password("pg.reset", "AUD06-NewPassword-2026!")
    assert store.verify_and_consume_reset_token(token) is None
    token = store.create_password_reset_token("pg.reset")
    store.update_user("pg.reset", {"email": "new@example.com"})
    assert store.verify_and_consume_reset_token(token) is None
    token = store.create_password_reset_token("pg.reset")
    store.update_user("pg.reset", {"is_active": False})
    store.update_user("pg.reset", {"is_active": True})
    assert store.verify_and_consume_reset_token(token) is None
    token = store.create_password_reset_token("pg.reset")
    assert store.reset_password_with_token(token, "AUD06-RecoveredPassword-2026!") == "pg.reset"
    assert store.verify_and_consume_reset_token(token) is None


def test_postgres_user_profile_and_force_password_change(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(store, "_database_url", DATABASE_URL)
    store.initialize_store()
    store.reset_store()

    # Create new user with force_password_change=1
    user = store.create_user(
        username="pg.tester",
        password="InitialPassword123!",  # noqa: S106
        role="user",
        full_name="Postgres Tester",
        email="pg.tester@opsmind.internal",
        department="QA",
        phone="0901234567",
        force_password_change=1,
    )
    assert user["username"] == "pg.tester"

    creds = store.get_user_credentials("pg.tester")
    assert creds is not None
    assert creds["force_password_change"] == 1
    assert creds["department"] == "QA"

    # Update password and clear force_password_change
    store.update_user_password("pg.tester", "UpdatedPassword123!", force_password_change=0)
    updated_creds = store.get_user_credentials("pg.tester")
    assert updated_creds is not None
    assert updated_creds["force_password_change"] == 0
    assert store.verify_password("UpdatedPassword123!", updated_creds["password_hash"])

