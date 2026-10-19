import os

import pytest

from app import store

DATABASE_URL = os.getenv("DATABASE_URL", "")

pytestmark = pytest.mark.skipif(not DATABASE_URL, reason="DATABASE_URL is not configured")


def test_postgres_schema_is_idempotent_and_ticket_lifecycle_works(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(store, "_database_url", DATABASE_URL)
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

