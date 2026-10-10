from collections.abc import Iterator
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app import store
from app.main import app
from app.rag import build_retrieval_index, generate_answer, load_knowledge_base, retrieve_relevant_context

client = TestClient(app)


@pytest.fixture(autouse=True)
def clean_store(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Iterator[None]:
    monkeypatch.setattr(store, "_database_path", tmp_path / "test-helpdesk.sqlite3")
    monkeypatch.setattr(store, "_database_url", "")
    store.initialize_store()
    store.reset_store()
    load_knowledge_base.cache_clear()
    build_retrieval_index.cache_clear()
    yield
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
    assert client.get("/auth/me", headers={"Authorization": f"Bearer {response.json()['token']}"}).json() == {
        "username": "agent",
        "role": "agent",
    }


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
    monkeypatch.setattr("app.rag.KNOWLEDGE_DIR", knowledge_dir)
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
    assert session["messages"][1]["sources"][0]["source"] == "vpn_forticlient.md"
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
    monkeypatch.setattr("app.rag.KNOWLEDGE_DIR", knowledge_dir)
    load_knowledge_base.cache_clear()
    build_retrieval_index.cache_clear()
    assert client.post("/knowledge/vpn.md/reindex", headers=auth("admin")).status_code == 200
    assert client.delete("/knowledge/vpn.md", headers=auth("agent")).status_code == 403
    assert client.delete("/knowledge/..-outside.md", headers=auth("admin")).status_code == 422
    # Seeded runbooks use underscores in their file names and must stay manageable.
    underscored = knowledge_dir / "wifi_network.md"
    underscored.write_text("# Wi-Fi Guide\n\nReconnect to the office SSID.", encoding="utf-8")
    assert client.post("/knowledge/wifi_network.md/reindex", headers=auth("admin")).status_code == 200
    assert client.delete("/knowledge/wifi_network.md", headers=auth("admin")).status_code == 200
    assert not underscored.exists()
    assert client.delete("/knowledge/vpn.md", headers=auth("admin")).status_code == 200
    assert not target.exists()
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
