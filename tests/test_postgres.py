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
    submitted = store.submit_knowledge_document_for_review(new_doc["id"], "agent")
    assert submitted["status"] == "pending_review"
    approved = store.approve_knowledge_document(new_doc["id"], "admin")
    assert approved["status"] == "published"
    versions = store.get_knowledge_document_versions(new_doc["id"])
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
