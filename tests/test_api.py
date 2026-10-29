from collections.abc import Iterator
from datetime import datetime, timedelta, timezone
from pathlib import Path
from urllib.parse import quote

import pytest
from fastapi.testclient import TestClient

from app import store
from app.main import app
from app.rag import build_retrieval_index, generate_answer, load_knowledge_base, retrieve_relevant_context

client = TestClient(app)


def test_knowledge_lookup_does_not_read_paths_outside_database(tmp_path, monkeypatch):
    knowledge_dir = tmp_path / "knowledge"
    knowledge_dir.mkdir()
    marker = tmp_path / "outside.md"
    marker.write_text("# Private marker\nAUD02-PRIVATE", encoding="utf-8")
    (knowledge_dir / "safe-runbook.md").write_text("# Untracked file", encoding="utf-8")
    store.create_knowledge_document("Safe runbook", "general", "# Safe runbook",
                                    custom_slug="safe-runbook.md", status="published")
    monkeypatch.setattr("app.main.KNOWLEDGE_DIR", knowledge_dir)
    headers = auth()
    identifiers = [
        str(marker), marker.as_posix(), "../outside.md", "..\\outside.md",
        "C:\\outside.md", "C:outside.md", "\\\\server\\share\\outside.md",
        "/outside.md", "safe-runbook.md:outside.md", "%2e%2e%5coutside.md",
    ]
    for identifier in identifiers:
        response = client.get("/knowledge/" + quote(identifier, safe=""), headers=headers)
        assert response.status_code in {404, 422}, (identifier, response.text)
        assert "AUD02-PRIVATE" not in response.text
    response = client.get("/knowledge/safe-runbook.md", headers=headers)
    assert response.status_code == 200
    assert response.json()["content"] == "# Safe runbook"


def test_knowledge_lookup_ignores_symlink_file(tmp_path, monkeypatch):
    knowledge_dir = tmp_path / "knowledge"
    knowledge_dir.mkdir()
    marker = tmp_path / "outside.md"
    marker.write_text("# Private marker", encoding="utf-8")
    try:
        (knowledge_dir / "linked.md").symlink_to(marker)
    except OSError as exc:
        pytest.skip(f"File symlinks unavailable: {exc}")
    monkeypatch.setattr("app.main.KNOWLEDGE_DIR", knowledge_dir)
    response = client.get("/knowledge/linked.md", headers=auth())
    assert response.status_code == 404


@pytest.fixture(autouse=True)
def clean_store(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Iterator[None]:
    from app.main import _failed_logins, _forgot_password_attempts
    _failed_logins.clear()
    _forgot_password_attempts.clear()
    monkeypatch.setattr(store, "_database_path", tmp_path / "test-helpdesk.sqlite3")
    monkeypatch.setattr(store, "_database_url", "")
    store.initialize_store()
    store.reset_store()
    load_knowledge_base.cache_clear()
    build_retrieval_index.cache_clear()
    yield
    _failed_logins.clear()
    _forgot_password_attempts.clear()
    load_knowledge_base.cache_clear()
    build_retrieval_index.cache_clear()


def token_for(username: str = "user", password: str | None = None) -> str:
    response = client.post(
        "/auth/login",
        json={"username": username, "password": password or username},
    )
    assert response.status_code == 200
    return response.json()["token"]


def auth(username: str = "user") -> dict[str, str]:
    return {"Authorization": f"Bearer {token_for(username)}"}


def make_ticket(headers: dict[str, str], title: str = "VPN connection problem") -> dict:
    response = client.post(
        "/tickets",
        headers=headers,
        json={
            "title": title,
            "description": "Cannot connect to company VPN after the certificate update.",
            "category": "network",
            "priority": "urgent",
        },
    )
    assert response.status_code == 201
    return response.json()["ticket"]


def test_health_and_web_app_are_available() -> None:
    health = client.get("/health")
    assert health.status_code == 200
    assert health.json() == {"status": "ok", "service": "helpdesk-rag"}
    assert client.head("/health").status_code == 200
    assert client.head("/").status_code == 200
    assert client.head("/config").status_code == 200
    page = client.get("/").text
    assert "Helpdesk RAG" in page
    assert 'id="demoCredentials" class="demo-note hidden"' in page
    assert client.get("/config").json() == {"demo_mode": True}


def test_health_reports_database_unavailability(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(store, "_database_path", tmp_path)
    response = client.get("/health")
    assert response.status_code == 503
    assert response.json()["detail"] == "Cơ sở dữ liệu hiện không sẵn sàng."


def test_login_and_token_role() -> None:
    response = client.post("/auth/login", json={"username": "agent", "password": "agent"})
    assert response.status_code == 200
    assert response.json()["role"] == "agent"
    me = client.get("/auth/me", headers={"Authorization": f"Bearer {response.json()['token']}"}).json()
    assert me["username"] == "agent"
    assert me["role"] == "agent"
    assert "activity" in me



def test_invalid_login_and_missing_auth_are_rejected() -> None:
    assert client.post("/auth/login", json={"username": "user", "password": "wrong"}).status_code == 401
    assert client.get("/tickets").status_code == 401


def test_user_only_sees_own_ticket_and_staff_sees_queue() -> None:
    user_headers = auth("user")
    agent_headers = auth("agent")
    own = make_ticket(user_headers)
    other = make_ticket(auth("admin"), "Printer is offline")

    own_tickets = client.get("/tickets", headers=user_headers)
    assert own_tickets.status_code == 200
    assert [ticket["id"] for ticket in own_tickets.json()] == [own["id"]]
    assert client.get(f"/tickets/{other['id']}", headers=user_headers).status_code == 404

    staff_tickets = client.get("/tickets", headers=agent_headers)
    assert {ticket["id"] for ticket in staff_tickets.json()} == {own["id"], other["id"]}


def test_ticket_creation_sets_sla_and_audit_log() -> None:
    before = datetime.now(timezone.utc)
    ticket = make_ticket(auth())
    deadline = datetime.fromisoformat(ticket["sla_deadline"])
    assert ticket["status"] == "new"
    assert timedelta(hours=1, minutes=59) < deadline - before < timedelta(hours=2, minutes=1)
    audit = client.get(f"/tickets/{ticket['id']}/audit", headers=auth()).json()
    assert audit[0]["event"] == "created"
    assert audit[0]["to_status"] == "new"


def test_ticket_fields_are_validated() -> None:
    response = client.post(
        "/tickets",
        headers=auth(),
        json={"title": "VPN", "description": "short", "priority": "critical"},
    )
    assert response.status_code == 422


def test_owner_can_edit_new_ticket_and_priority_recalculates_sla() -> None:
    headers = auth()
    ticket = make_ticket(headers)
    response = client.put(
        f"/tickets/{ticket['id']}",
        headers=headers,
        json={"title": "VPN connection after certificate renewal", "priority": "high"},
    )
    assert response.status_code == 200
    updated = response.json()["ticket"]
    assert updated["title"] == "VPN connection after certificate renewal"
    assert updated["priority"] == "high"
    assert timedelta(hours=7, minutes=59) < (
        datetime.fromisoformat(updated["sla_deadline"]) - datetime.now(timezone.utc)
    ) < timedelta(hours=8, minutes=1)
    assert store.get_ticket_audit(ticket["id"])[0]["event"] == "ticket_updated"


def test_ticket_edit_is_restricted_after_processing_starts() -> None:
    user_headers = auth()
    ticket = make_ticket(user_headers)
    agent_headers = auth("agent")
    assert client.patch(
        f"/tickets/{ticket['id']}",
        headers=agent_headers,
        json={"status": "in_progress"},
    ).status_code == 200
    response = client.put(
        f"/tickets/{ticket['id']}",
        headers=user_headers,
        json={"title": "Changed by requester after processing"},
    )
    assert response.status_code == 409


def test_admin_archives_ticket_without_removing_audit() -> None:
    ticket = make_ticket(auth("user"))
    response = client.delete(f"/tickets/{ticket['id']}", headers=auth("agent"))
    assert response.status_code == 403

    deleted = client.delete(f"/tickets/{ticket['id']}", headers=auth("admin"))
    assert deleted.status_code == 200
    assert client.get(f"/tickets/{ticket['id']}", headers=auth("admin")).status_code == 404
    assert client.get("/analytics", headers=auth("admin")).json()["total_tickets"] == 0
    assert [entry["event"] for entry in store.get_ticket_audit(ticket["id"])] == ["archived", "created"]


def test_admin_can_create_user_without_exposing_password() -> None:
    user_headers = auth()
    assert client.post(
        "/admin/users",
        headers=user_headers,
        json={"username": "new.user", "password": "strong-password-123", "role": "agent"},
    ).status_code == 403

    admin_headers = auth("admin")
    response = client.post(
        "/admin/users",
        headers=admin_headers,
        json={"username": "new.user", "password": "strong-password-123", "role": "agent"},
    )
    assert response.status_code == 201
    assert response.json() == {"username": "new.user", "role": "agent"}
    assert "password" not in client.get("/admin/users", headers=admin_headers).text
    assert client.post(
        "/auth/login",
        json={"username": "new.user", "password": "strong-password-123"},
    ).status_code == 200
    assert client.post(
        "/admin/users",
        headers=admin_headers,
        json={"username": "new.user", "password": "strong-password-123", "role": "agent"},
    ).status_code == 409
    assert client.post(
        "/admin/users",
        headers=admin_headers,
        json={"username": "weak.user", "password": "short", "role": "agent"},
    ).status_code == 422
    staff = client.get("/staff", headers=admin_headers)
    assert staff.status_code == 200
    assert {item["username"] for item in staff.json()} == {"agent", "admin", "new.user"}
    assert client.get("/staff", headers=user_headers).status_code == 403


def test_admin_can_edit_profile_role_and_lock_accounts() -> None:
    admin_headers = auth("admin")
    created = client.post(
        "/admin/users",
        headers=admin_headers,
        json={
            "username": "support.new",
            "password": "strong-password-123",
            "role": "agent",
            "full_name": "Nguyễn IT",
            "email": "it@example.test",
            "department": "IT",
            "phone": "1234",
        },
    )
    assert created.status_code == 201
    listed = client.get("/admin/users", headers=admin_headers).json()
    support_user = next(user for user in listed if user["username"] == "support.new")
    assert support_user["full_name"] == "Nguyễn IT"
    assert support_user["email"] == "it@example.test"
    assert "password_hash" not in support_user

    changed = client.patch(
        "/admin/users/support.new",
        headers=admin_headers,
        json={"role": "user", "department": "Finance"},
    )
    assert changed.status_code == 200
    assert changed.json()["role"] == "user"
    assert changed.json()["department"] == "Finance"
    locked = client.patch(
        "/admin/users/support.new",
        headers=admin_headers,
        json={"is_active": False},
    )
    assert locked.status_code == 200
    assert locked.json()["is_active"] == 0
    assert client.post(
        "/auth/login",
        json={"username": "support.new", "password": "strong-password-123"},
    ).status_code == 401
    assert all(
        user["username"] != "support.new"
        for user in client.get("/staff", headers=admin_headers).json()
    )
    assert client.patch(
        "/admin/users/admin",
        headers=admin_headers,
        json={"is_active": False},
    ).status_code == 409


def test_admin_can_ingest_valid_markdown_and_retriever_refreshes(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    knowledge_dir = tmp_path / "knowledge"
    monkeypatch.setattr("app.main.KNOWLEDGE_DIR", knowledge_dir)
    load_knowledge_base.cache_clear()
    build_retrieval_index.cache_clear()
    files = {
        "document": (
            "secure_remote_access.md",
            "# Secure Remote Access\n\nFor demo query quasar, contact the internal access desk.",
            "text/markdown",
        )
    }
    uploaded = client.post(
        "/knowledge",
        headers=auth("admin"),
        data={"title": "Secure Remote Access"},
        files=files,
    )
    assert uploaded.status_code == 201
    assert uploaded.json()["source"] == "secure-remote-access.md"
    answer = generate_answer("How do I handle quasar access?")
    assert answer["sources"][0]["source"] == "secure-remote-access.md"

    duplicate = client.post(
        "/knowledge",
        headers=auth("admin"),
        data={"title": "Another title"},
        files=files,
    )
    assert duplicate.status_code == 409


def test_non_admin_cannot_ingest_knowledge_and_non_markdown_is_rejected(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr("app.main.KNOWLEDGE_DIR", tmp_path / "knowledge")
    content = {"document": ("notes.txt", "# Notes\n\nText", "text/plain")}
    assert client.post(
        "/knowledge",
        headers=auth("agent"),
        data={"title": "Notes"},
        files=content,
    ).status_code == 403
    assert client.post(
        "/knowledge",
        headers=auth("admin"),
        data={"title": "Notes"},
        files=content,
    ).status_code == 415


@pytest.mark.parametrize(
    ("filename", "content", "expected_status"),
    [
        ("large.md", b"# Large\n\n" + b"x" * 262_145, 413),
        ("invalid.md", b"\xff\xfe", 422),
        ("missing-heading.md", b"Plain text without a Markdown heading.", 422),
        ("\u4e2d\u6587.md", b"# Valid heading\n\nValid body.", 422),
    ],
    ids=["over-limit", "invalid-utf8", "missing-h1", "unusable-filename"],
)
def test_knowledge_upload_rejects_invalid_documents(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    filename: str,
    content: bytes,
    expected_status: int,
) -> None:
    monkeypatch.setattr("app.main.KNOWLEDGE_DIR", tmp_path / "knowledge")
    response = client.post(
        "/knowledge",
        headers=auth("admin"),
        data={"title": "Valid title"},
        files={"document": (filename, content, "text/markdown")},
    )
    assert response.status_code == expected_status


def test_knowledge_multipart_parser_rejects_oversized_text_part(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def unexpected_save(*args, **kwargs):
        pytest.fail("Oversized multipart text must be rejected before document save")

    monkeypatch.setattr("app.routers.knowledge.save_knowledge_document", unexpected_save)
    response = client.post(
        "/knowledge",
        headers=auth("admin"),
        files={
            "title": (None, "x" * (1024 * 1024 + 1)),
            "document": ("bounded-test.md", "# Test\nLocal regression", "text/markdown"),
        },
    )
    assert response.status_code in {400, 422}
    if response.status_code == 400:
        assert "Part exceeded maximum size" in response.json()["detail"]


def test_whitespace_only_ticket_comment_and_rag_input_are_rejected() -> None:
    headers = auth()
    ticket = make_ticket(headers)
    comment = client.post(
        f"/tickets/{ticket['id']}/comments",
        headers=headers,
        json={"comment": "   "},
    )
    question = client.post("/rag/ask", headers=headers, json={"question": "   "})
    assert comment.status_code == 422
    assert question.status_code == 422


def test_ticket_lifecycle_and_invalid_transitions() -> None:
    headers = auth("agent")
    ticket = make_ticket(headers)
    response = client.patch(
        f"/tickets/{ticket['id']}", headers=headers, json={"status": "in_progress"}
    )
    assert response.status_code == 200
    assert response.json()["ticket"]["status"] == "in_progress"

    invalid = client.patch(
        f"/tickets/{ticket['id']}", headers=headers, json={"status": "closed"}
    )
    assert invalid.status_code == 403
    assert client.get(f"/tickets/{ticket['id']}", headers=headers).json()["status"] == "in_progress"


def test_requester_can_confirm_resolution_or_reopen_ticket() -> None:
    requester = auth("user")
    ticket = make_ticket(requester)
    staff = auth("agent")
    assert client.patch(
        f"/tickets/{ticket['id']}", headers=staff, json={"status": "in_progress"}
    ).status_code == 200
    assert client.patch(
        f"/tickets/{ticket['id']}", headers=staff, json={"status": "resolved"}
    ).status_code == 200
    assert client.patch(
        f"/tickets/{ticket['id']}", headers=staff, json={"status": "closed"}
    ).status_code == 403

    reopened = client.patch(
        f"/tickets/{ticket['id']}", headers=requester, json={"status": "in_progress"}
    )
    assert reopened.status_code == 200
    assert reopened.json()["ticket"]["resolved_at"] is None
    client.patch(f"/tickets/{ticket['id']}", headers=staff, json={"status": "resolved"})

    closed = client.patch(
        f"/tickets/{ticket['id']}", headers=requester, json={"status": "closed"}
    )
    assert closed.status_code == 200
    assert closed.json()["ticket"]["closed_at"] is not None
    assert client.patch(
        f"/tickets/{ticket['id']}", headers=requester, json={"status": "in_progress"}
    ).status_code == 403
    assert client.post(
        f"/tickets/{ticket['id']}/comments",
        headers=requester,
        json={"comment": "Ticket đã đóng."},
    ).status_code == 409
    assert client.post(
        f"/tickets/{ticket['id']}/attachments",
        headers=requester,
        files={"file": ("closed.log", b"closed", "text/plain")},
    ).status_code == 409


def test_requester_reply_reopens_waiting_ticket() -> None:
    requester = auth("user")
    ticket = make_ticket(requester)
    staff = auth("agent")
    assert client.patch(
        f"/tickets/{ticket['id']}", headers=staff, json={"status": "in_progress"}
    ).status_code == 200
    assert client.patch(
        f"/tickets/{ticket['id']}",
        headers=staff,
        json={"status": "pending_waiting_user"},
    ).status_code == 200
    reply = client.post(
        f"/tickets/{ticket['id']}/comments",
        headers=requester,
        json={"comment": "Tôi đã gửi ảnh lỗi và thử lại."},
    )
    assert reply.status_code == 200
    assert reply.json()["ticket"]["status"] == "in_progress"
    events = [
        event["event"]
        for event in client.get(f"/tickets/{ticket['id']}/audit", headers=requester).json()
    ]
    assert events.count("status_changed") == 3


def test_ticket_rating_requires_resolved_owned_ticket_and_updates_analytics() -> None:
    requester = auth("user")
    ticket = make_ticket(requester)
    assert client.post(
        f"/tickets/{ticket['id']}/rate",
        headers=requester,
        json={"rating": 5, "comment": "Great"},
    ).status_code == 409
    staff = auth("agent")
    client.patch(f"/tickets/{ticket['id']}", headers=staff, json={"status": "in_progress"})
    client.patch(f"/tickets/{ticket['id']}", headers=staff, json={"status": "resolved"})
    rated = client.post(
        f"/tickets/{ticket['id']}/rate",
        headers=requester,
        json={"rating": 5, "comment": "Đã khắc phục."},
    )
    assert rated.status_code == 200
    assert rated.json()["ticket"]["rating"] == 5
    assert client.get("/analytics", headers=staff).json()["average_rating"] == 5
    assert client.post(
        f"/tickets/{ticket['id']}/rate",
        headers=auth("admin"),
        json={"rating": 4},
    ).status_code == 403


def test_ticket_attachment_upload_download_and_access_control(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr("app.main.ATTACHMENTS_DIR", tmp_path / "attachments")
    requester = auth("user")
    ticket = make_ticket(requester)
    upload = client.post(
        f"/tickets/{ticket['id']}/attachments",
        headers=requester,
        files={"file": ("error log.txt", b"VPN tunnel failed", "text/plain")},
    )
    assert upload.status_code == 201
    attachment = upload.json()
    assert attachment["original_name"] == "error log.txt"
    assert attachment["size_bytes"] == len(b"VPN tunnel failed")
    assert client.get(f"/tickets/{ticket['id']}", headers=requester).json()["attachments"][0]["id"] == attachment["id"]
    download = client.get(
        f"/tickets/{ticket['id']}/attachments/{attachment['id']}",
        headers=requester,
    )
    assert download.status_code == 200
    assert download.content == b"VPN tunnel failed"
    assert client.get(
        f"/tickets/{ticket['id']}/attachments/{attachment['id']}",
        headers=auth("admin"),
    ).status_code == 200
    other_ticket = make_ticket(auth("admin"), "Printer jam")
    assert client.get(
        f"/tickets/{ticket['id']}/attachments/{attachment['id']}",
        headers=auth("agent"),
    ).status_code == 200
    assert client.get(
        f"/tickets/{other_ticket['id']}/attachments/{attachment['id']}",
        headers=auth("admin"),
    ).status_code == 404
    unsupported = client.post(
        f"/tickets/{ticket['id']}/attachments",
        headers=requester,
        files={"file": ("run.exe", b"not safe", "application/octet-stream")},
    )
    assert unsupported.status_code == 415
    invalid_image = client.post(
        f"/tickets/{ticket['id']}/attachments",
        headers=requester,
        files={"file": ("screen.png", b"not a real png", "image/png")},
    )
    assert invalid_image.status_code == 422
    too_large = client.post(
        f"/tickets/{ticket['id']}/attachments",
        headers=requester,
        files={"file": ("large.log", b"x" * (10 * 1024 * 1024 + 1), "text/plain")},
    )
    assert too_large.status_code == 413


def test_rag_chat_history_and_feedback_are_scoped_to_the_user() -> None:
    requester = auth("user")
    response = client.post(
        "/rag/ask",
        headers=requester,
        json={"question": "Tôi không kết nối được VPN FortiClient"},
    )
    assert response.status_code == 200
    result = response.json()
    assert result["session_id"]
    assert result["assistant_message_id"] > 0
    sessions = client.get("/rag/sessions", headers=requester).json()
    assert len(sessions) == 1
    session = client.get(
        f"/rag/sessions/{result['session_id']}", headers=requester
    ).json()
    assert [message["role"] for message in session["messages"]] == ["user", "assistant"]
    assert session["messages"][1]["sources"] == []
    assert session["diagnostic"]["state"] == "IN_SCOPE_NO_SOURCE"
    feedback = client.post(
        "/rag/feedback",
        headers=requester,
        json={"message_id": result["assistant_message_id"], "feedback": "up"},
    )
    assert feedback.status_code == 200
    assert client.get(
        f"/rag/sessions/{result['session_id']}", headers=requester
    ).json()["messages"][1]["feedback"] == "up"
    assert client.get(
        f"/rag/sessions/{result['session_id']}", headers=auth("agent")
    ).status_code == 404
    assert client.post(
        "/rag/feedback",
        headers=auth("agent"),
        json={"message_id": result["assistant_message_id"], "feedback": "down"},
    ).status_code == 404


def test_admin_can_reindex_and_delete_knowledge_document(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    knowledge_dir = tmp_path / "knowledge"
    knowledge_dir.mkdir()
    target = knowledge_dir / "vpn.md"
    target.write_text("# VPN Guide\n\nReset the vpn quasar connector.", encoding="utf-8")
    monkeypatch.setattr("app.main.KNOWLEDGE_DIR", knowledge_dir)
    store.create_knowledge_document("VPN Guide", "network", target.read_text(encoding="utf-8"),
                                    custom_slug="vpn.md", status="published")
    load_knowledge_base.cache_clear()
    build_retrieval_index.cache_clear()
    assert client.post("/knowledge/vpn.md/reindex", headers=auth("admin")).status_code == 200
    assert client.delete("/knowledge/vpn.md", headers=auth("agent")).status_code == 403
    assert client.delete("/knowledge/..-outside.md", headers=auth("admin")).status_code == 422
    assert client.delete("/knowledge/vpn.md", headers=auth("admin")).status_code == 200
    assert target.exists()  # Legacy files are retained for offline reconciliation.
    assert store.get_knowledge_document("vpn.md") is None
    assert client.get("/knowledge/vpn.md", headers=auth("admin")).status_code == 404
    assert client.delete("/knowledge/vpn.md", headers=auth("admin")).status_code == 404
    load_knowledge_base.cache_clear()
    build_retrieval_index.cache_clear()


def test_admin_can_export_ticket_report_only() -> None:
    make_ticket(auth("user"), "VPN access from home")
    malicious = client.post(
        "/tickets",
        headers=auth("user"),
        json={
            "title": "=SUM(1,1) test",
            "description": "Testing CSV spreadsheet safety.",
            "category": "=cmd",
            "priority": "low",
        },
    )
    assert malicious.status_code == 201
    exported = client.get("/analytics/export", headers=auth("admin"))
    assert exported.status_code == 200
    assert "text/csv" in exported.headers["content-type"]
    assert "VPN access from home" in exported.text
    assert "'=SUM(1,1) test" in exported.text
    assert "'=cmd" in exported.text
    assert client.get("/analytics/export", headers=auth("agent")).status_code == 403


def test_agent_personal_analytics_are_scoped_to_assigned_tickets() -> None:
    ticket = make_ticket(auth("user"))
    staff = auth("agent")
    assert client.put(
        f"/tickets/{ticket['id']}/assignment",
        headers=staff,
        json={"assignee": "agent"},
    ).status_code == 200
    assert client.patch(
        f"/tickets/{ticket['id']}", headers=staff, json={"status": "in_progress"}
    ).status_code == 200
    assert client.patch(
        f"/tickets/{ticket['id']}", headers=staff, json={"status": "resolved"}
    ).status_code == 200
    metrics = client.get("/analytics/agents/me", headers=staff)
    assert metrics.status_code == 200
    assert metrics.json()["assigned_tickets"] == 1
    assert metrics.json()["resolved_tickets"] == 1
    assert metrics.json()["sla_compliance_percent"] == 100
    assert metrics.json()["category_breakdown"] == {"network": 1}
    assert client.get("/analytics/agents/me", headers=auth("user")).status_code == 403


def test_end_user_cannot_change_ticket_or_view_staff_analytics() -> None:
    headers = auth()
    ticket = make_ticket(headers)
    response = client.patch(f"/tickets/{ticket['id']}", headers=headers, json={"status": "in_progress"})
    assert response.status_code == 403
    assert client.get("/analytics", headers=headers).status_code == 403


def test_agent_assignment_and_comment_are_recorded() -> None:
    headers = auth("agent")
    ticket = make_ticket(headers)
    assignment = client.put(
        f"/tickets/{ticket['id']}/assignment",
        headers=headers,
        json={"assignee": "admin"},
    )
    assert assignment.status_code == 200
    assert assignment.json()["ticket"]["assignee"] == "admin"

    comment = client.post(
        f"/tickets/{ticket['id']}/comments",
        headers=headers,
        json={"comment": "Đã kiểm tra cấu hình VPN, đang xác minh chứng thư."},
    )
    assert comment.status_code == 200
    assert comment.json()["ticket"]["comments"][0]["author"] == "agent"
    events = [entry["event"] for entry in client.get(f"/tickets/{ticket['id']}/audit", headers=headers).json()]
    assert "assigned" in events
    assert "comment_added" in events


def test_invalid_assignee_is_rejected() -> None:
    headers = auth("agent")
    ticket = make_ticket(headers)
    response = client.put(
        f"/tickets/{ticket['id']}/assignment",
        headers=headers,
        json={"assignee": "missing-user"},
    )
    assert response.status_code == 422


def test_analytics_and_ticket_filters() -> None:
    staff_headers = auth("admin")
    make_ticket(staff_headers, "VPN access")
    printer_ticket = make_ticket(staff_headers, "Printer queue stuck")
    client.put(
        f"/tickets/{printer_ticket['id']}",
        headers=staff_headers,
        json={"category": "hardware"},
    )
    analytics = client.get("/analytics", headers=staff_headers).json()
    assert analytics["total_tickets"] == 2
    assert analytics["status_breakdown"]["new"] == 2
    assert analytics["overdue_tickets"] == 0

    filtered = client.get("/tickets?q=Printer&status=new", headers=staff_headers).json()
    assert len(filtered) == 1
    assert filtered[0]["title"] == "Printer queue stuck"
    today = datetime.now(timezone.utc).date().isoformat()
    by_date = client.get(
        f"/tickets?category=hardware&from={today}&to={today}",
        headers=staff_headers,
    )
    assert by_date.status_code == 200
    assert len(by_date.json()) == 1
    assert client.get(
        f"/tickets?from={today}&to=2020-01-01",
        headers=staff_headers,
    ).status_code == 422


@pytest.mark.parametrize("change", ["edit", "archive", "reject", "restore", "delete", "publish"])
def test_knowledge_changes_reach_an_independent_warm_reader(change: str, knowledge_reader_process) -> None:
    # Setup only touches the isolated fixture DB; keep a single controlled document.
    with store._connect() as connection:
        connection.execute("UPDATE knowledge_documents SET status = 'archived'")
    admin_headers = auth("admin")
    user_headers = auth()
    initial = "# VPN FortiClient\nAUD08-INITIAL FortiClient VPN troubleshooting policy"
    revised = "# VPN FortiClient\nAUD08-REVISED FortiClient VPN troubleshooting policy"
    created = client.post(
        "/knowledge", headers=admin_headers,
        json={"title": "VPN Worker Policy", "category": "network", "content": initial,
              "status": "draft" if change == "publish" else "published"},
    )
    assert created.status_code == 201
    slug = created.json()["slug"]
    if change == "restore":
        assert client.put(
            f"/knowledge/{slug}", headers=admin_headers, json={"content": revised},
        ).status_code == 200
    question = "Tôi không kết nối được VPN FortiClient"
    before = client.post("/rag/ask", headers=user_headers, json={"question": question})
    assert before.status_code == 200
    with knowledge_reader_process() as ask:
        warm = ask(question)
        assert warm["grounded"] is (change != "publish")
        if change in {"edit", "archive"}:
            payload = {"content": revised} if change == "edit" else {"status": "archived"}
            updated = client.put(f"/knowledge/{slug}", headers=admin_headers, json=payload)
        elif change in {"reject", "publish"}:
            updated = client.post(
                f"/knowledge/{slug}/review", headers=admin_headers,
                json={"action": "approve" if change == "publish" else "reject"},
            )
        elif change == "restore":
            updated = client.post(f"/knowledge/{slug}/restore/1", headers=admin_headers)
        else:
            updated = client.delete(f"/knowledge/{slug}", headers=admin_headers)
        assert updated.status_code == 200
        parent = generate_answer(question)  # Compare retrieval caches independently of procedural approval.
        remote = ask(question)
        assert remote["pid"] == warm["pid"]
        assert remote["matches"] == parent["matches"]
        visible = change in {"edit", "restore", "publish"}
        assert remote["grounded"] is visible
        if visible:
            marker = "AUD08-REVISED" if change == "edit" else "AUD08-INITIAL"
            assert marker in remote["matches"][0]["content"]
        else:
            assert remote["matches"] == remote["sources"] == []


def test_warm_retrieval_cache_fails_closed_on_store_error(monkeypatch):
    from sqlite3 import OperationalError

    headers = auth()
    question = {"question": "Tôi không kết nối được VPN FortiClient"}
    warm = client.post("/rag/ask", headers=headers, json=question)
    assert warm.status_code == 200 and warm.json()["grounded"] is False
    session_id = warm.json()["session_id"]

    def unavailable(*args, **kwargs):
        raise OperationalError("AUD08-SYNTHETIC-DB-ERROR")

    with monkeypatch.context() as patch:
        patch.setattr(store, "list_knowledge_documents", unavailable)
        failed = client.post("/rag/ask", headers=headers, json=question)
        assert failed.status_code == 503
        assert "AUD08-SYNTHETIC-DB-ERROR" not in failed.text
        session = client.get(f"/rag/sessions/{session_id}", headers=headers).json()
        assert len(session["messages"]) == 2
    recovered = client.post("/rag/ask", headers=headers, json=question)
    assert recovered.status_code == 200 and recovered.json()["grounded"] is False


def test_rag_does_not_resurrect_files_after_last_document_is_archived() -> None:
    admin_headers = auth("admin")
    user_headers = auth()
    documents = store.list_knowledge_documents(status="published")
    last_slug = "vpn_forticlient.md"
    assert any(doc["slug"] == last_slug for doc in documents)
    for doc in documents:
        if doc["slug"] != last_slug:
            response = client.put(
                f"/knowledge/{doc['slug']}", headers=admin_headers, json={"status": "archived"},
            )
            assert response.status_code == 200
    question = {"question": "Tôi không kết nối được VPN FortiClient"}
    before = client.post("/rag/ask", headers=user_headers, json=question)
    assert before.status_code == 200
    assert before.json()["grounded"] is False
    archived = client.put(
        f"/knowledge/{last_slug}", headers=admin_headers, json={"status": "archived"},
    )
    assert archived.status_code == 200
    assert store.list_knowledge_documents(status="published") == []
    from app.rag import BASE_KNOWLEDGE_DIR
    assert (BASE_KNOWLEDGE_DIR / last_slug).is_file()
    assert client.get("/knowledge", headers=user_headers).json() == []
    assert client.get(f"/knowledge/{last_slug}", headers=user_headers).status_code == 404
    after = client.post("/rag/ask", headers=user_headers, json=question)
    assert after.status_code == 200
    assert after.json()["grounded"] is False
    assert after.json()["matches"] == []
    assert after.json()["sources"] == []
    assert after.json()["llm_generated"] is False
    assert load_knowledge_base() == []
    assert build_retrieval_index() == []

    # Re-publishing invalidates the empty cache and reads the approved DB content.
    published = client.put(
        f"/knowledge/{last_slug}", headers=admin_headers,
        json={"status": "published", "content": "# VPN FortiClient\nAUD05-DB-PUBLISHED VPN access"},
    )
    assert published.status_code == 200
    restored = client.post("/rag/ask", headers=user_headers, json=question)
    assert restored.status_code == 200
    assert restored.json()["grounded"] is False
    assert restored.json()["state"] == "IN_SCOPE_NO_SOURCE"
    retrieved = generate_answer(question["question"])
    assert [doc["source"] for doc in retrieved["sources"]] == [last_slug]
    assert "AUD05-DB-PUBLISHED" in retrieved["matches"][0]["content"]


def test_rag_database_failure_returns_503_and_recovers_without_cache_clear(monkeypatch):
    from sqlite3 import OperationalError

    headers = auth()
    question = {"question": "Tôi không kết nối được VPN FortiClient"}

    def unavailable(*args, **kwargs):
        raise OperationalError("AUD05-SYNTHETIC-PRIVATE-DB-DETAIL")

    with monkeypatch.context() as patch:
        patch.setattr(store, "list_knowledge_documents", unavailable)
        response = client.post("/rag/ask", headers=headers, json=question)
        assert response.status_code == 503
        assert "AUD05-SYNTHETIC-PRIVATE-DB-DETAIL" not in response.text
        assert "matches" not in response.json()
        assert client.get("/rag/sessions", headers=headers).json() == []
    recovered = client.post("/rag/ask", headers=headers, json=question)
    assert recovered.status_code == 200
    assert recovered.json()["grounded"] is False


def test_rag_finds_vietnamese_printer_and_vpn_sources() -> None:
    printer = generate_answer("Máy in bị kẹt lệnh, tôi cần kiểm tra gì?")
    vpn = generate_answer("Tôi không kết nối được VPN FortiClient do chứng thư hết hạn")
    assert printer["grounded"] is True
    assert printer["sources"][0]["source"] == "printer_queue.md"
    assert printer["triage"]["category"] == "hardware"
    assert vpn["grounded"] is True
    assert vpn["sources"][0]["source"] == "vpn_forticlient.md"
    assert vpn["triage"]["category"] == "network"
    assert vpn["triage"]["priority"] == "high"
    assert vpn["triage"]["requires_confirmation"] is True
    assert "Print Spooler" in printer["matches"][0]["content"]


def test_rag_results_do_not_repeat_the_same_runbook() -> None:
    response = generate_answer("Team đang cần kết nối VPN để làm việc tại nhà")
    sources = [source["source"] for source in response["sources"]]
    assert len(sources) == len(set(sources))
    assert sources[0] == "vpn_forticlient.md"


def test_triage_suggests_urgent_for_broad_impact_but_never_auto_confirms() -> None:
    response = generate_answer("Toàn công ty mất kết nối VPN gateway down")
    assert response["triage"]["category"] == "network"
    assert response["triage"]["priority"] == "urgent"
    assert response["triage"]["requires_confirmation"] is True


def test_rag_refuses_questions_without_relevant_knowledge() -> None:
    response = generate_answer("Hãy cho biết dự báo thời tiết ngày mai tại Hà Nội")
    assert response["grounded"] is False
    assert response["sources"] == []
    assert response["triage"]["category"] == "general"
    assert response["triage"]["priority"] == "medium"
    assert response["triage"]["requires_confirmation"] is True
    assert retrieve_relevant_context("unrelated astronomy question") == []


def test_knowledge_endpoint_lists_documents_and_requires_auth() -> None:
    assert client.get("/knowledge").status_code == 401
    documents = client.get("/knowledge", headers=auth()).json()
    assert len(documents) >= 9
    assert any(document["source"] == "folder_access.md" for document in documents)


def test_rag_llm_synthesis_disabled_by_default() -> None:
    response = generate_answer("Tôi không kết nối được VPN FortiClient")
    assert response["grounded"] is True
    assert response["llm_generated"] is False
    assert "Mình tìm thấy hướng dẫn liên quan trong Knowledge Base" in response["answer"]


def test_rag_llm_synthesis_success_when_enabled(monkeypatch: pytest.MonkeyPatch) -> None:
    from app import config
    import httpx

    monkeypatch.setattr(config, "ENABLE_LLM_GENERATION", True)
    monkeypatch.setattr(config, "LLM_API_KEY", "test-key-mock")

    class MockResponse:
        status_code = 200

        def json(self) -> dict:
            return {
                "choices": [
                    {
                        "message": {
                            "content": "Bước 1: Khởi động lại FortiClient. Bước 2: Kiểm tra chứng thư số."
                        }
                    }
                ]
            }

    monkeypatch.setattr(httpx, "post", lambda *args, **kwargs: MockResponse())
    response = generate_answer("Tôi không kết nối được VPN FortiClient")
    assert response["grounded"] is True
    assert response["llm_generated"] is True
    assert "Bước 1: Khởi động lại FortiClient" in response["answer"]


def test_rag_llm_synthesis_falls_back_on_error(monkeypatch: pytest.MonkeyPatch) -> None:
    from app import config
    import httpx

    monkeypatch.setattr(config, "ENABLE_LLM_GENERATION", True)
    monkeypatch.setattr(config, "LLM_API_KEY", "test-key-mock")

    def mock_fail(*args, **kwargs):
        raise httpx.RequestError("Network error timeout")

    monkeypatch.setattr(httpx, "post", mock_fail)
    response = generate_answer("Tôi không kết nối được VPN FortiClient")
    assert response["grounded"] is True
    assert response["llm_generated"] is False
    assert "Mình tìm thấy hướng dẫn liên quan trong Knowledge Base" in response["answer"]


def test_login_rate_limiting_blocks_after_five_failed_attempts() -> None:
    # 5 failed attempts
    for _ in range(5):
        res = client.post("/auth/login", json={"username": "user", "password": "wrong-password"})
        assert res.status_code == 401

    # 6th attempt is throttled with 429
    blocked = client.post("/auth/login", json={"username": "user", "password": "user"})
    assert blocked.status_code == 429
    assert "Đã thử đăng nhập sai quá nhiều lần" in blocked.json()["detail"]


def test_user_change_password_and_token_invalidation() -> None:
    # 1. Login to get token
    login_res = client.post("/auth/login", json={"username": "user", "password": "user"})
    assert login_res.status_code == 200
    token = login_res.json()["token"]
    user_headers = {"Authorization": f"Bearer {token}"}

    # 2. Reject wrong old password
    bad_old = client.post(
        "/auth/change-password",
        headers=user_headers,
        json={"old_password": "incorrect-password", "new_password": "NewSecretPassword123!"},
    )
    assert bad_old.status_code == 400
    assert "Mật khẩu hiện tại không chính xác" in bad_old.json()["detail"]

    # 3. Reject password under 12 characters
    short_pw = client.post(
        "/auth/change-password",
        headers=user_headers,
        json={"old_password": "user", "new_password": "short123"},
    )
    assert short_pw.status_code == 422

    # 6. Successfully change password
    change_res = client.post(
        "/auth/change-password",
        headers=user_headers,
        json={"old_password": "user", "new_password": "BrandNewSecurePassword123!"},
    )
    assert change_res.status_code == 200
    assert "Đổi mật khẩu thành công" in change_res.json()["message"]

    # 7. Old JWT token must be invalidated
    invalidated = client.get("/auth/me", headers=user_headers)
    assert invalidated.status_code == 401
    assert "Mật khẩu đã được thay đổi" in invalidated.json()["detail"]

    # 8. Login with old password fails
    assert client.post("/auth/login", json={"username": "user", "password": "user"}).status_code == 401

    # 9. Login with new password succeeds
    new_login = client.post(
        "/auth/login",
        json={"username": "user", "password": "BrandNewSecurePassword123!"},
    )
    assert new_login.status_code == 200
    assert new_login.json()["force_password_change"] is False


def test_admin_reset_user_password_and_force_change_flag() -> None:
    admin_headers = auth("admin")
    user_headers = auth("user")

    # 1. Non-admin cannot reset
    assert client.post(
        "/admin/users/user/reset-password",
        headers=user_headers,
        json={"new_password": "AdminSetPassword123!", "force_change": True},
    ).status_code == 403

    # 2. Reset with short password fails
    assert client.post(
        "/admin/users/user/reset-password",
        headers=admin_headers,
        json={"new_password": "short", "force_change": True},
    ).status_code == 422

    # 3. Admin successfully resets password with force_change=True
    reset_res = client.post(
        "/admin/users/user/reset-password",
        headers=admin_headers,
        json={"new_password": "AdminSetPassword123!", "force_change": True},
    )
    assert reset_res.status_code == 200
    assert "Đã đặt lại mật khẩu" in reset_res.json()["message"]

    # 4. Login response returns force_password_change=True
    login_res = client.post(
        "/auth/login",
        json={"username": "user", "password": "AdminSetPassword123!"},
    )
    assert login_res.status_code == 200
    assert login_res.json()["force_password_change"] is True

    # 5. User changes password, force_password_change resets to False
    token = login_res.json()["token"]
    chg = client.post(
        "/auth/change-password",
        headers={"Authorization": f"Bearer {token}"},
        json={"old_password": "AdminSetPassword123!", "new_password": "UserChosenPassword123!"},
    )
    assert chg.status_code == 200

    re_login = client.post(
        "/auth/login",
        json={"username": "user", "password": "UserChosenPassword123!"},
    )
    assert re_login.status_code == 200
    assert re_login.json()["force_password_change"] is False


def test_cannot_delete_builtin_knowledge_document() -> None:
    admin_headers = auth("admin")
    # Built-in runbook from repo cannot be deleted
    res = client.delete("/knowledge/printer_offline_status.md", headers=admin_headers)
    assert res.status_code == 403
    assert "Không thể xóa tài liệu mặc định" in res.json()["detail"]

    # But reindexing built-in runbook with underscore succeeds
    reindex_res = client.post("/knowledge/printer_offline_status.md/reindex", headers=admin_headers)
    assert reindex_res.status_code == 200


def test_knowledge_lifecycle_and_review_workflow() -> None:
    agent_headers = auth("agent")
    admin_headers = auth("admin")
    user_headers = auth("user")

    # 1. Regular user cannot create knowledge documents
    user_create = client.post(
        "/knowledge",
        headers=user_headers,
        json={
            "title": "User Attempt Runbook",
            "category": "software",
            "content": "# User Runbook\n\nSome invalid attempt text here.",
            "status": "draft",
        },
    )
    assert user_create.status_code == 403

    # 2. Agent cannot publish directly without review
    agent_direct_publish = client.post(
        "/knowledge",
        headers=agent_headers,
        json={
            "title": "Direct Publish Runbook",
            "category": "software",
            "content": "# Direct Publish\n\nContent for direct publish.",
            "status": "published",
        },
    )
    assert agent_direct_publish.status_code == 403

    # 3. Agent creates a draft runbook
    create_res = client.post(
        "/knowledge",
        headers=agent_headers,
        json={
            "title": "Docker Troubleshooting Guide",
            "category": "software",
            "tags": "docker, container, devops",
            "content": "# Docker Troubleshooting Guide\n\nCheck running containers with `docker ps` and restart daemon.",
            "status": "draft",
        },
    )
    assert create_res.status_code == 201
    doc = create_res.json()
    slug = doc["slug"]
    assert doc["status"] == "draft"
    assert doc["author"] == "agent"

    # 4. Draft is NOT visible in public / user list of knowledge
    user_kb = client.get("/knowledge", headers=user_headers).json()
    assert not any(d["slug"] == slug for d in user_kb)

    # 5. Agent updates content and submits for review
    update_res = client.put(
        f"/knowledge/{slug}",
        headers=agent_headers,
        json={
            "status": "pending_review",
            "change_summary": "Hoàn thiện các bước kiểm tra docker socket",
        },
    )
    assert update_res.status_code == 200
    assert update_res.json()["status"] == "pending_review"

    # 6. Agent cannot approve their own document
    agent_approve = client.post(
        f"/knowledge/{slug}/review",
        headers=agent_headers,
        json={"action": "approve"},
    )
    assert agent_approve.status_code == 403

    # 7. Admin approves and publishes the document
    admin_approve = client.post(
        f"/knowledge/{slug}/review",
        headers=admin_headers,
        json={"action": "approve", "feedback": "Nội dung chuẩn và đầy đủ."},
    )
    assert admin_approve.status_code == 200
    approved_doc = admin_approve.json()
    assert approved_doc["status"] == "published"
    assert approved_doc["reviewer"] == "admin"
    assert approved_doc["approved_at"] is not None

    # 8. Document is now visible to user role
    user_kb_after = client.get("/knowledge", headers=user_headers).json()
    assert any(d["slug"] == slug for d in user_kb_after)

    # 9. Clean up non-builtin document
    del_res = client.delete(f"/knowledge/{slug}", headers=admin_headers)
    assert del_res.status_code == 200


def test_knowledge_version_history_and_restoration() -> None:
    admin_headers = auth("admin")
    agent_headers = auth("agent")

    # 1. Admin creates document (Version 1)
    v1_content = "# K8s Guide\n\nInitial version 1 content: check kubectl get nodes."
    create_res = client.post(
        "/knowledge",
        headers=admin_headers,
        json={
            "title": "Kubernetes Cluster Guide",
            "category": "software",
            "tags": "k8s, kubernetes",
            "content": v1_content,
            "status": "published",
        },
    )
    assert create_res.status_code == 201
    slug = create_res.json()["slug"]

    # 2. Update to Version 2
    v2_content = "# K8s Guide\n\nVersion 2 updated content: use helm upgrade for deployments."
    update_res = client.put(
        f"/knowledge/{slug}",
        headers=admin_headers,
        json={
            "content": v2_content,
            "change_summary": "Bổ sung hướng dẫn helm",
        },
    )
    assert update_res.status_code == 200
    assert update_res.json()["version_count"] == 2

    # 3. List versions
    versions = client.get(f"/knowledge/{slug}/versions", headers=agent_headers).json()
    assert len(versions) == 2
    assert versions[0]["version_number"] == 2
    assert versions[1]["version_number"] == 1
    assert "helm" in versions[0]["content"]
    assert "kubectl get nodes" in versions[1]["content"]

    # 4. Agent cannot restore version
    agent_restore = client.post(f"/knowledge/{slug}/restore/1", headers=agent_headers)
    assert agent_restore.status_code == 403

    # 5. Admin restores version 1
    admin_restore = client.post(f"/knowledge/{slug}/restore/1", headers=admin_headers)
    assert admin_restore.status_code == 200
    restored = admin_restore.json()
    assert restored["version_count"] == 3
    assert "kubectl get nodes" in restored["content"]

    # 6. Verify GET returns restored content
    current = client.get(f"/knowledge/{slug}", headers=admin_headers).json()
    assert "kubectl get nodes" in current["content"]

    # Clean up
    client.delete(f"/knowledge/{slug}", headers=admin_headers)


def test_user_profile_endpoints() -> None:
    user_headers = auth("user")

    # 1. GET /auth/me returns profile & activity
    me = client.get("/auth/me", headers=user_headers).json()
    assert me["username"] == "user"
    assert me["role"] == "user"
    assert "activity" in me
    assert "tickets_created" in me["activity"]
    assert "tickets_assigned" in me["activity"]
    assert "tickets_resolved" in me["activity"]

    # 2. PATCH /auth/profile requires current_password to change email
    no_pwd = client.patch(
        "/auth/profile",
        headers=user_headers,
        json={"email": "user.test@opsmind.internal"},
    )
    assert no_pwd.status_code == 400

    wrong_pwd = client.patch(
        "/auth/profile",
        headers=user_headers,
        json={"email": "user.test@opsmind.internal", "current_password": "wrongpassword123"},
    )
    assert wrong_pwd.status_code == 403

    res = client.patch(
        "/auth/profile",
        headers=user_headers,
        json={
            "full_name": "Nguyễn Văn Người Dùng",
            "email": "user.test@opsmind.internal",
            "department": "Kế toán",
            "phone": "0912345678",
            "current_password": "user",
        },
    )
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "success"
    assert data["profile"]["full_name"] == "Nguyễn Văn Người Dùng"
    assert data["profile"]["email"] == "user.test@opsmind.internal"
    assert data["profile"]["department"] == "Kế toán"
    assert data["profile"]["phone"] == "0912345678"

    # 3. GET /auth/me reflects updated contact info
    me_after = client.get("/auth/me", headers=user_headers).json()
    assert me_after["full_name"] == "Nguyễn Văn Người Dùng"
    assert me_after["email"] == "user.test@opsmind.internal"
    assert me_after["department"] == "Kế toán"
    assert me_after["phone"] == "0912345678"

    # 4. PATCH /auth/profile rejects invalid email
    bad_email = client.patch(
        "/auth/profile",
        headers=user_headers,
        json={"email": "invalid-email-address"},
    )
    assert bad_email.status_code == 422

    # 5. PATCH /auth/profile requires at least one field
    empty_update = client.patch("/auth/profile", headers=user_headers, json={})
    assert empty_update.status_code == 422

    # 6. Unauthenticated requests are rejected
    assert client.patch("/auth/profile", json={"full_name": "Hacker"}).status_code == 401


def test_profile_email_change_rate_limits_after_five_failed_attempts() -> None:
    user_headers = auth("user")
    for _ in range(5):
        resp = client.patch(
            "/auth/profile",
            headers=user_headers,
            json={"email": "new.email@opsmind.internal", "current_password": "badpassword!"},
        )
        assert resp.status_code == 403

    blocked = client.patch(
        "/auth/profile",
        headers=user_headers,
        json={"email": "new.email@opsmind.internal", "current_password": "badpassword!"},
    )
    assert blocked.status_code == 429


def test_cannot_change_priority_on_resolved_or_closed_ticket() -> None:
    admin_headers = auth("admin")
    ticket = make_ticket(auth("user"), title="Test SLA freeze")
    t_id = ticket["id"]

    client.patch(f"/tickets/{t_id}", headers=admin_headers, json={"status": "in_progress"})
    client.patch(f"/tickets/{t_id}", headers=admin_headers, json={"status": "resolved"})

    res = client.put(f"/tickets/{t_id}", headers=admin_headers, json={"priority": "low"})
    assert res.status_code == 409
    assert "Không thể thay đổi mức độ ưu tiên" in res.json()["detail"]





def test_idor_and_ticket_ownership_isolation() -> None:
    # QA-03: Kiểm thử triệt để chống IDOR - Người dùng Alice và Bob bị cách ly hoàn toàn
    store.create_user(
        "user_alice",
        "AlicePass2026!@",
        "user",
        "Alice Nguyen",
        "alice@opsmind.internal",
        "Finance",
        "0911111111",
    )
    store.create_user(
        "user_bob",
        "BobPass2026!@#",
        "user",
        "Bob Tran",
        "bob@opsmind.internal",
        "Sales",
        "0922222222",
    )

    alice_headers = {"Authorization": f"Bearer {token_for('user_alice', 'AlicePass2026!@')}"}
    bob_headers = {"Authorization": f"Bearer {token_for('user_bob', 'BobPass2026!@#')}"}

    # Alice tạo một ticket riêng tư
    ticket_alice = make_ticket(alice_headers, title="Alice confidential financial issue")
    alice_t_id = ticket_alice["id"]

    # 1. Bob liệt kê danh sách ticket -> KHÔNG được nhìn thấy ticket của Alice
    bob_list = client.get("/tickets", headers=bob_headers)
    assert bob_list.status_code == 200
    bob_ticket_ids = [t["id"] for t in bob_list.json()]
    assert alice_t_id not in bob_ticket_ids

    # 2. Bob cố tình truy cập trực tiếp ID của Alice -> Phải bị từ chối 404
    assert client.get(f"/tickets/{alice_t_id}", headers=bob_headers).status_code == 404

    # 3. Bob cố tình chỉnh sửa ticket của Alice -> 404
    assert (
        client.put(
            f"/tickets/{alice_t_id}",
            headers=bob_headers,
            json={"title": "Hacked by Bob"},
        ).status_code
        == 404
    )

    # 4. Bob cố tình gửi bình luận vào ticket của Alice -> 404
    assert (
        client.post(
            f"/tickets/{alice_t_id}/comments",
            headers=bob_headers,
            json={"comment": "Unauthorized comment from Bob"},
        ).status_code
        == 404
    )

    # 5. Bob cố tình đánh giá sao ticket của Alice -> 404
    assert (
        client.post(
            f"/tickets/{alice_t_id}/rate",
            headers=bob_headers,
            json={"rating": 1, "comment": "Malicious rating"},
        ).status_code
        == 404
    )

    # 6. Bob cố tình xem lịch sử audit của Alice -> 404
    assert client.get(f"/tickets/{alice_t_id}/audit", headers=bob_headers).status_code == 404


def test_html_escaping_in_email_dispatch(monkeypatch: pytest.MonkeyPatch) -> None:
    # SEC-06 / OPS-02 / AUD-21: Kiểm tra trực tiếp mã sản phẩm app.email_sender
    # Dữ liệu động chứa ký tự HTML đặc biệt phải được escape an toàn trong payload HTML gửi đi
    from typing import Any
    from app import config, email_sender

    captured_payloads: list[dict[str, Any]] = []

    def mock_post(url: str, **kwargs: Any) -> Any:
        captured_payloads.append(kwargs.get("json", {}))

        class MockResponse:
            status_code = 200
            is_success = True

            def json(self) -> dict[str, Any]:
                return {"id": "msg-mock-123"}

        return MockResponse()

    monkeypatch.setattr(email_sender.httpx, "post", mock_post)

    raw_body = 'Xin chào <script>alert("xss")</script> & "admin"!\nLine 2'

    # 1. Kiểm tra qua Resend provider
    monkeypatch.setattr(config, "RESEND_API_KEY", "re_test_key_12345")
    success_resend = email_sender._send_via_resend("user@example.com", "Thử nghiệm an toàn HTML", raw_body)
    assert success_resend is True
    resend_payload = captured_payloads[-1]

    # Raw text giữ nguyên
    assert resend_payload["text"] == raw_body
    # HTML payload phải được escape an toàn
    assert "<script>" not in resend_payload["html"]
    assert "&lt;script&gt;" in resend_payload["html"]
    assert "&amp;" in resend_payload["html"]
    assert "&quot;" in resend_payload["html"]
    assert "<br>" in resend_payload["html"]

    # 2. Kiểm tra qua Brevo provider
    monkeypatch.setattr(config, "BREVO_API_KEY", "xkeysib-test-key-12345")
    success_brevo = email_sender._send_via_brevo("user@example.com", "Thử nghiệm an toàn HTML Brevo", raw_body)
    assert success_brevo is True
    brevo_payload = captured_payloads[-1]

    # Raw textContent giữ nguyên
    assert brevo_payload["textContent"] == raw_body
    # HTML payload phải được escape an toàn
    assert "<script>" not in brevo_payload["htmlContent"]
    assert "&lt;script&gt;" in brevo_payload["htmlContent"]
    assert "&amp;" in brevo_payload["htmlContent"]
    assert "&quot;" in brevo_payload["htmlContent"]
    assert "<br>" in brevo_payload["htmlContent"]


def test_diagnostic_questions_and_session_context():
    headers = auth()
    first = client.post('/rag/ask', headers=headers, json={'question': 'Máy in Offline dù đã bật nguồn'}).json()
    assert first['state'] == 'CLARIFY'
    assert len(first['questions']) <= 3
    assert first['matches'] == []
    second = client.post('/rag/ask', headers=headers, json={
        'question': 'Tôi không biết loại kết nối', 'session_id': first['session_id'],
    }).json()
    assert second['state'] == 'HANDOFF_PREVIEW'
    assert second['incident_topic'] == 'printer'
    changed = client.post('/rag/ask', headers=headers, json={
        'question': 'Cắm dây mạng không vào Internet', 'session_id': first['session_id'],
    }).json()
    assert changed['state'] == 'CLARIFY'
    assert changed['pending_topic'] == 'network'


def test_diagnostics_do_not_escalate_weather_or_claim_cable_failure():
    headers = auth()
    network = client.post('/rag/ask', headers=headers, json={
        'question': 'Cắm dây mạng nhưng không có Internet',
    }).json()
    assert network['state'] == 'CLARIFY'
    assert network['grounded'] is False
    assert 'đứt dây' not in network['answer']
    weather = client.post('/rag/ask', headers=headers, json={
        'question': 'Thời tiết Hà Nội hôm nay thế nào?', 'session_id': network['session_id'],
    }).json()
    assert weather['state'] == 'OUT_OF_SCOPE'
    assert weather['sources'] == []


def test_diagnostic_session_cannot_be_read_by_another_user():
    first = client.post('/rag/ask', headers=auth('admin'), json={'question': 'Máy in Offline'}).json()
    other = auth('user')
    response = client.post('/rag/ask', headers=other, json={
        'question': 'Tôi không biết', 'session_id': first['session_id'],
    })
    assert response.status_code == 404


def test_ticket_request_key_retries_return_same_ticket():
    headers = auth()
    payload = {'title': 'Máy in Offline demo', 'description': 'Chưa xác minh kết nối máy in',
               'request_key': 'demo-request-00000001'}
    first = client.post('/tickets', headers=headers, json=payload)
    retry = client.post('/tickets', headers=headers, json=payload)
    assert first.status_code == retry.status_code == 201
    assert first.json()['ticket']['id'] == retry.json()['ticket']['id']
    assert len(client.get('/tickets', headers=headers).json()) == 1


def test_ticket_request_key_concurrent_and_scoped_to_account():
    from concurrent.futures import ThreadPoolExecutor
    headers = auth()
    payload = {'title': 'Máy in Offline demo', 'description': 'Chưa xác minh kết nối máy in',
               'request_key': 'demo-concurrent-00000001'}
    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(lambda _: client.post('/tickets', headers=headers, json=payload), range(2)))
    assert all(r.status_code == 201 for r in results)
    assert results[0].json()['ticket']['id'] == results[1].json()['ticket']['id']
    other = client.post('/tickets', headers=auth('admin'), json=payload)
    assert other.status_code == 201
    assert other.json()['ticket']['id'] != results[0].json()['ticket']['id']


def test_negated_or_past_success_never_resolves_incident():
    headers = auth()
    first = client.post('/rag/ask', headers=headers, json={'question': 'Máy in Offline'}).json()
    for question in ('Tôi chưa in được, đừng nói đã in được', 'Trước đây đã in được nhưng giờ vẫn lỗi'):
        result = client.post('/rag/ask', headers=headers, json={'question': question, 'session_id': first['session_id']}).json()
        assert result['state'] != 'RESOLVED'
        assert 'đã xác nhận chức năng' not in result['answer']


def test_pending_topic_switch_does_not_contaminate_active_incident():
    headers = auth()
    first = client.post('/rag/ask', headers=headers, json={'question': 'Máy in Offline'}).json()
    switch = client.post('/rag/ask', headers=headers, json={'question': 'Outlook không đăng nhập được', 'session_id': first['session_id']}).json()
    assert switch['pending_topic'] == 'other_it'
    assert switch['incident_topic'] == 'printer'
    followup = client.post('/rag/ask', headers=headers, json={'question': 'Tôi không biết', 'session_id': first['session_id']}).json()
    assert followup['incident_topic'] == 'printer'
    assert 'Outlook' not in followup['handoff']['description']


def test_approved_printer_guide_requires_explicit_current_result(tmp_path, monkeypatch):
    import json
    from app import assistant_policy
    catalogue = tmp_path / 'synthetic-approved.json'
    catalogue.write_text(json.dumps({'runbooks': [{
        'id': 'fixture-printer', 'topic': 'printer', 'version': 'test-1',
        'status': 'approved', 'reviewer': 'synthetic test reviewer', 'reviewed_at': '2026-10-28',
        'source': 'fixture://printer', 'source_version': '1', 'section': 'Observation',
        'conditions': {'connection': 'usb', 'scope': 'single', 'panel': 'no_error'},
        'steps': [{'id': 'observe', 'instruction': 'Quan sát hàng đợi thử nghiệm.',
                   'expected': 'Ghi lại trạng thái.', 'stop': 'Dừng nếu cần thay đổi cấu hình.', 'roles': ['user']}],
    }]}), encoding='utf8')
    monkeypatch.setattr(assistant_policy, 'CATALOGUE', catalogue)
    headers = auth()
    first = client.post('/rag/ask', headers=headers, json={'question': 'Máy in Offline'}).json()
    body = {'question': 'Dữ kiện kiểm tra', 'session_id': first['session_id'],
            'expected_revision': first['revision'], 'fact_answers': {'connection': 'usb', 'scope': 'single', 'panel': 'no_error'}}
    guide = client.post('/rag/ask', headers=headers, json=body).json()
    assert guide['state'] == 'CHECK_RESULT'
    assert guide['steps'][0]['id'] == 'observe'
    assert guide['policy_sources'][0]['version'] == 'test-1'
    still = client.post('/rag/ask', headers=headers, json={
        'question': 'Trước đây đã in được nhưng vẫn lỗi', 'session_id': first['session_id'],
        'expected_revision': guide['revision'], 'step_results': {'observe': 'attempted_failure'},
    }).json()
    assert still['state'] == 'CHECK_RESULT'
    assert still['attempted_steps'] == [{'id': 'observe', 'result': 'attempted_failure'}]
    assert still['suggested_only_steps'] == []
    resolved = client.post('/rag/ask', headers=headers, json={
        'question': 'Xác nhận chức năng hiện đã hoạt động', 'session_id': first['session_id'],
        'action': 'confirm_resolved', 'expected_revision': still['revision'],
    }).json()
    assert resolved['state'] == 'RESOLVED'
    assert resolved['handoff']['description'].count('đã hoạt động trở lại') == 1


def test_unapproved_guide_and_invalid_fact_fail_closed():
    headers = auth()
    first = client.post('/rag/ask', headers=headers, json={'question': 'Dây mạng không Internet'}).json()
    invalid = client.post('/rag/ask', headers=headers, json={
        'question': 'Dữ kiện', 'session_id': first['session_id'], 'expected_revision': first['revision'], 'fact_answers': {'role': 'admin'},
    })
    assert invalid.status_code == 422
    result = client.post('/rag/ask', headers=headers, json={
        'question': 'Dữ kiện', 'session_id': first['session_id'], 'expected_revision': first['revision'],
        'fact_answers': {'link': 'connected', 'scope': 'single', 'internal': 'works'},
    }).json()
    assert result['state'] == 'HANDOFF_PREVIEW'
    assert result['steps'] == []
    assert result['facts']['internal']['source'] == 'user'
    assert result['facts']['internal']['at']
    assert 'Dữ kiện internal: works' in result['handoff']['description']
    assert client.post('/rag/ask', headers=headers, json={
        'question': 'Đã hoạt động', 'session_id': first['session_id'], 'action': 'confirm_resolved', 'expected_revision': result['revision'],
    }).status_code == 422


def test_ticket_retry_lookup_conflicts_and_ownership():
    headers = auth()
    payload = {'title': 'Máy in Offline test', 'description': 'Mô tả thử nghiệm đủ dài', 'request_key': 'request-lookup-00000001'}
    ticket = client.post('/tickets', headers=headers, json=payload).json()['ticket']
    recovered = client.get('/ticket-requests/' + payload['request_key'], headers=headers)
    assert recovered.json()['ticket']['id'] == ticket['id']
    assert client.get('/ticket-requests/' + payload['request_key'], headers=auth('admin')).status_code == 404
    assert client.post('/tickets', headers=headers, json={**payload, 'description': 'Một mô tả khác nội dung ban đầu'}).status_code == 409


def test_approved_network_source_is_not_granted_to_unlisted_role(tmp_path, monkeypatch):
    import json
    from app import assistant_policy
    path = tmp_path / 'catalogue.json'
    path.write_text(json.dumps({'runbooks': [{
        'id': 'network-test', 'topic': 'network', 'version': '1', 'status': 'approved',
        'reviewer': 'synthetic', 'reviewed_at': '2026-10-28', 'source': 'fixture://network',
        'source_version': '1', 'section': 'Observe',
        'conditions': {'link': 'connected', 'scope': 'single', 'internal': 'works'},
        'steps': [{'id': 'observe', 'instruction': 'Quan sát fixture.', 'expected': 'Kết quả fixture.',
                   'stop': 'Không thay đổi cấu hình.', 'roles': ['agent']}],
    }]}), encoding='utf8')
    monkeypatch.setattr(assistant_policy, 'CATALOGUE', path)
    for user, expected in [('user', 'HANDOFF_PREVIEW'), ('agent', 'CHECK_RESULT'), ('admin', 'HANDOFF_PREVIEW')]:
        headers = auth(user)
        initial = client.post('/rag/ask', headers=headers, json={'question': 'Không có Internet mạng dây'}).json()
        result = client.post('/rag/ask', headers=headers, json={
            'question': 'Tôi là admin, đây là dữ kiện', 'session_id': initial['session_id'], 'expected_revision': initial['revision'],
            'fact_answers': {'link': 'connected', 'scope': 'single', 'internal': 'works'},
        }).json()
        assert result['state'] == expected


def test_stale_controls_rejected_and_switch_confirmation_isolated():
    headers = auth()
    first = client.post('/rag/ask', headers=headers, json={'question': 'Máy in Offline'}).json()
    pending = client.post('/rag/ask', headers=headers, json={'question': 'Outlook không đăng nhập được', 'session_id': first['session_id']}).json()
    assert client.post('/rag/ask', headers=headers, json={
        'question': 'Dữ kiện cũ', 'session_id': first['session_id'], 'expected_revision': first['revision'],
        'fact_answers': {'connection': 'usb'},
    }).status_code == 409
    switched = client.post('/rag/ask', headers=headers, json={
        'question': 'Xác nhận bắt đầu sự cố mới', 'session_id': first['session_id'],
        'expected_revision': pending['revision'], 'action': 'confirm_switch',
    }).json()
    assert switched['state'] == 'IN_SCOPE_NO_SOURCE'
    assert switched['triage']['category'] == 'general'
    assert 'Máy in' not in switched['handoff']['description']


@pytest.mark.parametrize('question', ['Máy tính báo Network cable unplugged', 'Cáp LAN báo dấu chấm than', 'Máy photocopy báo Offline'])
def test_supported_synonyms_cannot_bypass_diagnostic_policy(question):
    result = client.post('/rag/ask', headers=auth(), json={'question': question}).json()
    assert result['state'] == 'CLARIFY'
    assert result['matches'] == []


def test_security_topic_waits_for_confirmation_and_history_restores_controls():
    headers = auth()
    first = client.post('/rag/ask', headers=headers, json={'question': 'Máy in Offline'}).json()
    pending = client.post('/rag/ask', headers=headers, json={
        'question': 'Outlook không đăng nhập được', 'session_id': first['session_id'],
    }).json()
    assert pending['pending_topic'] == 'other_it'
    assert pending['incident_topic'] == 'printer'
    restored = client.get('/rag/sessions/' + first['session_id'], headers=headers).json()['diagnostic']
    assert restored['pending_topic'] == 'other_it'
    assert restored['revision'] == pending['revision']
    continued = client.post('/rag/ask', headers=headers, json={
        'question': 'Tiếp tục sự cố hiện tại', 'action': 'continue_incident',
        'session_id': first['session_id'], 'expected_revision': restored['revision'],
    }).json()
    assert continued['pending_topic'] is None
    assert continued['questions']
    history = client.get('/rag/sessions/' + first['session_id'], headers=headers).json()['diagnostic']
    assert history['questions'] == continued['questions']
    assert history['attempted_steps'] == []


@pytest.mark.parametrize('question', ['Máy in nghi bị mã độc', 'Máy tính nhiễm virus không vào Internet', 'Máy in bị cháy bốc khói', 'Cáp LAN bị cháy'])
def test_safety_signals_stop_new_and_active_guides(question):
    from app import store
    headers = auth()
    initial = client.post('/rag/ask', headers=headers, json={'question': question}).json()
    assert initial['state'] == 'HANDOFF_PREVIEW'
    assert initial['safety_stop'] and not initial['steps']
    # Seed an active guide to verify a danger report invalidates result controls.
    context = {'topic': 'printer', 'initial_question': 'Máy in Offline', 'facts': {},
               'state': 'CHECK_RESULT', 'steps': [{'id': 'observe'}], 'sources': [], 'revision': 1}
    sid = store.save_chat_exchange('user', None, 'Máy in Offline', 'fixture', [], incident_context=context)
    pending = client.post('/rag/ask', headers=headers, json={'question': question, 'session_id': sid}).json()
    assert pending['safety_stop'] and pending['pending_topic'] in ('hazard', 'security')
    assert not pending['steps']
    for action in ('continue_incident', 'confirm_resolved'):
        blocked = client.post('/rag/ask', headers=headers, json={'question': 'Tiếp tục', 'session_id': sid,
            'action': action, 'expected_revision': pending['revision']}).json()
        assert blocked['safety_stop'] and blocked['state'] == 'CLARIFY'
        pending = blocked
    switched = client.post('/rag/ask', headers=headers, json={'question': 'Xác nhận', 'session_id': sid,
        'action': 'confirm_switch', 'expected_revision': pending['revision']}).json()
    assert switched['state'] == 'HANDOFF_PREVIEW' and not switched['steps']
    assert question in switched['handoff']['description']


@pytest.mark.parametrize('question', ['Thiết bị văn phòng gặp trục trặc', 'Windows không in được, hàng đợi báo Offline'])
def test_unrecognized_paraphrase_cannot_expose_legacy_runbook(monkeypatch, question):
    from app.routers import rag
    monkeypatch.setattr(rag, 'generate_answer', lambda _: {
        'answer': 'Unapproved legacy procedure', 'sources': ['fixture'],
        'matches': [{'source': 'custom_windows.md', 'title': 'Xử lý sự cố Windows', 'content': 'Restart Print Spooler'}], 'triage': {'category': 'hardware', 'priority': 'medium'},
    })
    result = client.post('/rag/ask', headers=auth(), json={'question': question}).json()
    assert result['state'] == 'IN_SCOPE_NO_SOURCE'
    assert result['matches'] == [] and result['steps'] == []
    assert 'Unapproved' not in result['answer']


def test_bug_regression_followup_details_survive_handoff_history_and_ticket():
    headers = auth()
    first = client.post('/rag/ask', headers=headers, json={'question': 'Máy in Offline'}).json()
    detail = '5 người phòng kế toán bị từ 9h, đang ngừng xuất hóa đơn'
    follow = client.post('/rag/ask', headers=headers, json={
        'question': detail, 'session_id': first['session_id'],
    }).json()
    ready = client.post('/rag/ask', headers=headers, json={
        'question': 'Dữ kiện kiểm tra', 'session_id': first['session_id'],
        'expected_revision': follow['revision'],
        'fact_answers': {'connection': 'unknown', 'scope': 'multiple', 'panel': 'unknown'},
    }).json()
    assert ready['state'] == 'HANDOFF_PREVIEW'
    assert detail in ready['handoff']['description']
    assert 'người dùng cung cấp, chưa xác minh' in ready['handoff']['description']
    history = client.get('/rag/sessions/' + first['session_id'], headers=headers).json()['diagnostic']
    assert detail in history['handoff']['description']
    ticket = client.post('/tickets', headers=headers, json={
        'title': ready['handoff']['title'], 'description': ready['handoff']['description'],
        'request_key': 'bug-followup-details-0001',
    })
    assert ticket.status_code == 201
    assert detail in ticket.json()['ticket']['description']


@pytest.mark.parametrize('action,terminal', [('still_failing', 'HANDOFF_PREVIEW'), ('confirm_resolved', 'RESOLVED'), (None, 'CHECK_RESULT')])
def test_bug_regression_terminal_incident_does_not_repeat_guide(monkeypatch, action, terminal):
    from app import assistant_policy
    calls = []
    step = {'id': 'observe', 'instruction': 'Quan sát fixture.', 'expected': 'Kết quả fixture.',
            'stop': 'Không thay đổi cấu hình.', 'roles': ['user']}

    def synthetic_approved(*args):
        calls.append(args)
        return [step], []

    monkeypatch.setattr(assistant_policy, 'approved_steps', synthetic_approved)
    headers = auth()
    first = client.post('/rag/ask', headers=headers, json={'question': 'Máy in Offline'}).json()
    guide = client.post('/rag/ask', headers=headers, json={
        'question': 'Dữ kiện kiểm tra', 'session_id': first['session_id'], 'expected_revision': first['revision'],
        'fact_answers': {'connection': 'usb', 'scope': 'single', 'panel': 'no_error'},
    }).json()
    assert guide['state'] == 'CHECK_RESULT'
    ended = guide if action is None else client.post('/rag/ask', headers=headers, json={
        'question': 'Kết quả hiện tại', 'session_id': first['session_id'], 'expected_revision': guide['revision'],
        'action': action, 'step_results': {'observe': 'attempted_failure' if action == 'still_failing' else 'attempted_success'},
    }).json()
    assert ended['state'] == terminal
    after = client.post('/rag/ask', headers=headers, json={'question': 'Cảm ơn', 'session_id': first['session_id']}).json()
    assert after['state'] == terminal
    assert after['attempted_steps'] == ended['attempted_steps']
    assert len(calls) == 1
    # A topic-switch prompt must suspend, then restore the same terminal state.
    pending = client.post('/rag/ask', headers=headers, json={'question': 'Outlook bị lỗi', 'session_id': first['session_id']}).json()
    restored = client.post('/rag/ask', headers=headers, json={
        'question': 'Tiếp tục sự cố hiện tại', 'session_id': first['session_id'],
        'action': 'continue_incident', 'expected_revision': pending['revision'],
    }).json()
    assert restored['state'] == terminal
    assert len(calls) == 1



def test_bug_regression_followup_reports_remain_separate_and_bounded():
    from app import assistant_policy as policy
    first = policy.diagnose('Máy in Offline')
    detail = '5 người phòng kế toán bị từ 9h'
    follow = policy.diagnose(detail, first['context'])
    assert follow['facts'] == {}  # A user report is not a confirmed diagnostic observation.
    assert follow['context']['notes'][0]['source'] == 'user'
    assert follow['context']['notes'][0]['at']
    pending = policy.diagnose('Outlook không gửi được thư', follow['context'])
    switched = policy.diagnose('Xác nhận', pending['context'], action='confirm_switch')
    assert detail not in switched['handoff']['description']
    assert not switched['context'].get('notes')
    long_context = follow['context']
    for index in range(4):
        long_context = policy.diagnose(f'Ghi chú {index}: ' + 'x' * 1900, long_context)['context']
    preview = policy.handoff(long_context)['description']
    assert len(preview) <= 5000 and 'Rút gọn' in preview
    assert detail in str(long_context['notes'])
    assert 'Ghi chú 3:' in preview


@pytest.mark.parametrize('question', ['Máy in bốc khói', 'Máy in nghi nhiễm mã độc'])
def test_bug_regression_safety_handoff_keeps_followup(question):
    headers = auth()
    first = client.post('/rag/ask', headers=headers, json={'question': question}).json()
    detail = '5 người phòng kế toán bị từ 9h'
    after = client.post('/rag/ask', headers=headers, json={'question': detail, 'session_id': first['session_id']}).json()
    assert after['state'] == 'HANDOFF_PREVIEW' and after['safety_stop']
    assert not after['steps'] and detail in after['handoff']['description']


def test_bug_regression_handoff_accepts_fact_correction_without_new_guide():
    headers = auth()
    first = client.post('/rag/ask', headers=headers, json={'question': 'Máy in Offline'}).json()
    ready = client.post('/rag/ask', headers=headers, json={
        'question': 'Không biết', 'session_id': first['session_id'],
    }).json()
    assert ready['state'] == 'HANDOFF_PREVIEW'
    corrected = client.post('/rag/ask', headers=headers, json={
        'question': 'Dữ kiện kiểm tra', 'session_id': first['session_id'],
        'expected_revision': ready['revision'], 'fact_answers': {'connection': 'usb'},
    }).json()
    assert corrected['state'] == 'HANDOFF_PREVIEW' and not corrected['steps']
    assert corrected['facts']['connection']['value'] == 'usb'
    assert 'Dữ kiện connection: usb' in corrected['handoff']['description']
    assert client.post('/rag/ask', headers=headers, json={
        'question': 'Dữ kiện kiểm tra', 'session_id': first['session_id'],
        'expected_revision': corrected['revision'], 'fact_answers': {'connection': 'invented'},
    }).status_code == 422


@pytest.mark.parametrize('previous_state', ['CHECK_RESULT', 'HANDOFF_PREVIEW', 'RESOLVED'])
def test_repeated_switch_prompts_restore_saved_state_after_reload(monkeypatch, previous_state):
    from app import assistant_policy

    def unexpected_guide_selection(*args):
        pytest.fail('Resuming an incident must not select a new guide')

    monkeypatch.setattr(assistant_policy, 'approved_steps', unexpected_guide_selection)
    context = {'topic': 'printer', 'initial_question': 'Máy in Offline', 'facts': {},
               'state': previous_state, 'steps': [{'id': 'observe'}], 'sources': [],
               'step_results': {'observe': 'attempted_failure'}, 'revision': 1}
    session_id = store.save_chat_exchange('user', None, 'Máy in Offline', 'fixture', [], incident_context=context)
    headers = auth()
    for question in ('Outlook bị lỗi', 'VPN không đăng nhập được'):
        pending = client.post('/rag/ask', headers=headers, json={'question': question, 'session_id': session_id}).json()
        assert pending['state'] == 'CLARIFY' and pending['pending_topic'] == 'other_it'
    restored = client.get('/rag/sessions/' + session_id, headers=headers).json()['diagnostic']
    continued = client.post('/rag/ask', headers=headers, json={
        'question': 'Tiếp tục sự cố hiện tại', 'session_id': session_id,
        'action': 'continue_incident', 'expected_revision': restored['revision'],
    }).json()
    assert continued['state'] == previous_state
    assert continued['attempted_steps'] == [{'id': 'observe', 'result': 'attempted_failure'}]
    assert continued['pending_topic'] is None


def test_new_session_keeps_prior_incident_reports_separate():
    headers = auth()
    first = client.post('/rag/ask', headers=headers, json={'question': 'Máy in Offline'}).json()
    report = '5 người kế toán bị từ 9h'
    client.post('/rag/ask', headers=headers, json={'question': report, 'session_id': first['session_id']})
    new = client.post('/rag/ask', headers=headers, json={'question': 'Máy in Offline'}).json()
    assert new['session_id'] != first['session_id']
    assert report not in new['handoff']['description']
    old = client.get('/rag/sessions/' + first['session_id'], headers=headers).json()['diagnostic']
    assert report in old['handoff']['description']


@pytest.mark.parametrize('username', ['user', 'admin'])
def test_monitor_after_weather_does_not_inherit_rejected_runbook_triage(username):
    headers = auth(username)
    first = client.post('/rag/ask', headers=headers, json={'question': 'hôm nay thời tiết thật đẹp'}).json()
    result = client.post('/rag/ask', headers=headers, json={
        'question': 'Hiện màn hình phụ tôi đang bị sọc, yêu cầu khắc phục',
        'session_id': first['session_id'],
    }).json()
    assert result['state'] == 'IN_SCOPE_NO_SOURCE'
    assert result['matches'] == [] and result['sources'] == []
    assert 'bitlocker' not in str(result).lower()
    assert 'navi_category' not in result['triage']
    assert result['triage']['category'] == 'general'
    restored = client.get('/rag/sessions/' + result['session_id'], headers=headers).json()['diagnostic']
    assert result['triage'] == restored['triage']
