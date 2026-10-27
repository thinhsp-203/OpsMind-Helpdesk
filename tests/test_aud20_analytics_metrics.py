import pytest
from pathlib import Path
from fastapi.testclient import TestClient
from app import store
from app.main import app

client = TestClient(app)


def test_helpful_feedback_rate_calculation_and_denominators(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """AUD-20: helpful_feedback_rate accurately measures thumbs-up percentage and reports sample sizes."""
    monkeypatch.setattr(store, "_database_url", "")
    monkeypatch.setattr(store, "_database_path", tmp_path / "test_aud20.sqlite3")
    store.initialize_store()

    # Create assistant messages with varied feedback: 4 up, 1 down, 5 unrated
    with store._connect() as conn:
        conn.execute("INSERT INTO chat_sessions (id, user_id, created_at, last_message_at) VALUES ('s1', 'user', '2026-10-21T00:00:00', '2026-10-21T00:00:00')")
        for i in range(10):
            if i < 4:
                fb = 'up'
            elif i == 4:
                fb = 'down'
            else:
                fb = None
            conn.execute(
                "INSERT INTO chat_messages (session_id, role, content, feedback, created_at) VALUES ('s1', 'assistant', 'Ans', ?, '2026-10-21T00:00:00')",
                (fb,)
            )

    analytics = store.get_analytics()
    assert analytics["total_rag_queries"] == 10
    assert analytics["helpful_feedback_count"] == 4
    assert analytics["unhelpful_feedback_count"] == 1
    assert analytics["total_feedback"] == 5
    assert analytics["unrated_queries"] == 5
    assert analytics["helpful_feedback_rate"] == 80.0
    assert analytics["feedback_response_rate"] == 50.0
    # Backward compatibility alias
    assert analytics["self_service_rate"] == 80.0
    assert analytics["self_resolution_verified_rate"] is None


def test_thumbs_up_does_not_falsely_claim_ticket_deflection(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """AUD-20: A thumbs-up on a RAG answer does not falsely equate to a solved ticket or deflection."""
    monkeypatch.setattr(store, "_database_url", "")
    monkeypatch.setattr(store, "_database_path", tmp_path / "test_aud20_deflection.sqlite3")
    store.initialize_store()

    with store._connect() as conn:
        conn.execute("INSERT INTO chat_sessions (id, user_id, created_at, last_message_at) VALUES ('s1', 'user', '2026-10-21T00:00:00', '2026-10-21T00:00:00')")
        conn.execute("INSERT INTO chat_messages (session_id, role, content, feedback, created_at) VALUES ('s1', 'assistant', 'Ans', 'up', '2026-10-21T00:00:00')")

    # User still opened a ticket for the issue
    store.create_ticket("Issue remains", "Need human technician", "general", "medium", "user")

    analytics = store.get_analytics()
    assert analytics["helpful_feedback_count"] == 1
    assert analytics["helpful_feedback_rate"] == 100.0
    assert analytics["total_tickets"] == 1
    # System must transparently report feedback sample size N=1
    assert analytics["feedback_sample_size"] == 1
    assert analytics["total_feedback"] == 1


def test_zero_feedback_returns_none_cleanly(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """AUD-20: If no feedback has been submitted, rate must be None, not 0 or 100."""
    monkeypatch.setattr(store, "_database_url", "")
    monkeypatch.setattr(store, "_database_path", tmp_path / "test_aud20_empty.sqlite3")
    store.initialize_store()

    analytics = store.get_analytics()
    assert analytics["total_rag_queries"] == 0
    assert analytics["helpful_feedback_count"] == 0
    assert analytics["unhelpful_feedback_count"] == 0
    assert analytics["total_feedback"] == 0
    assert analytics["unrated_queries"] == 0
    assert analytics["helpful_feedback_rate"] is None
    assert analytics["self_service_rate"] is None
    assert analytics["feedback_response_rate"] is None


def test_analytics_api_endpoint_schema_and_backward_compatibility() -> None:
    """AUD-20: GET /analytics returns both helpful_feedback_rate and self_service_rate alias."""
    login_res = client.post("/auth/login", json={"username": "admin", "password": "admin"})
    assert login_res.status_code == 200
    token = login_res.json()["token"]

    res = client.get("/analytics", headers={"Authorization": f"Bearer {token}"})
    assert res.status_code == 200
    data = res.json()
    assert "helpful_feedback_rate" in data
    assert "self_service_rate" in data
    assert "total_rag_queries" in data
    assert "helpful_feedback_count" in data
    assert "unhelpful_feedback_count" in data
    assert "total_feedback" in data
    assert "unrated_queries" in data
    assert "feedback_response_rate" in data
