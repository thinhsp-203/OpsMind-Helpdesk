from pathlib import Path
import re
import pytest

KNOWLEDGE_DIR = Path(__file__).resolve().parents[1] / "data" / "knowledge"


def test_all_runbooks_have_standard_sections_and_valid_structure() -> None:
    files = list(KNOWLEDGE_DIR.glob("*.md"))
    assert len(files) == 30, f"Expected 30 knowledge runbooks, found {len(files)}"

    for f in files:
        text = f.read_text(encoding="utf-8")
        assert text.startswith("# "), f"{f.name} must start with H1 title"
        assert "**Từ khóa:**" in text, f"{f.name} missing keywords line"
        headings = re.findall(r"(?m)^##\s+(.+?)\s*$", text)
        assert len(headings) >= 3, f"{f.name} must have at least 3 sections, found {headings}"


def test_runbook_command_syntax_and_escapes() -> None:
    """AUD-18: Verify no dropped letters or broken command prefixes exist in any runbook."""
    for f in KNOWLEDGE_DIR.glob("*.md"):
        text = f.read_text(encoding="utf-8")
        # Check for dropped letter typos: \bslookup\b instead of nslookup, \betsh\b instead of netsh
        assert not re.search(r"\bslookup\b", text), f"{f.name} contains 'slookup' instead of 'nslookup'"
        assert not re.search(r"\betsh\b", text), f"{f.name} contains 'etsh' instead of 'netsh'"
        assert "\\nslookup" not in text, f"{f.name} contains broken escape \\nslookup"
        assert "\\netsh" not in text, f"{f.name} contains broken escape \\netsh"

    # Specifically verify dns_dhcp_conflict has nslookup
    dns_text = (KNOWLEDGE_DIR / "dns_dhcp_conflict.md").read_text(encoding="utf-8")
    assert "nslookup company.internal" in dns_text
    assert "nslookup google.com" in dns_text

    # Specifically verify proxy_pac_bypass has netsh
    proxy_text = (KNOWLEDGE_DIR / "proxy_pac_bypass.md").read_text(encoding="utf-8")
    assert "netsh winhttp reset proxy" in proxy_text


def test_runbook_security_guardrails_and_role_separation() -> None:
    """AUD-18: Ensure runbooks do not instruct ordinary users to perform dangerous admin operations."""
    # 1. email_send_receive_error: must not recommend disabling antivirus
    email_text = (KNOWLEDGE_DIR / "email_send_receive_error.md").read_text(encoding="utf-8")
    assert "tạm tắt tính năng quét email của antivirus" not in email_text.lower()
    assert "tạm tắt" not in email_text.lower()
    assert "temporarily disable third-party antivirus" not in email_text.lower()
    assert "do not disable endpoint antivirus" in email_text.lower()

    # 2. outlook_mailbox_quota: must not recommend permanently purging server items
    quota_text = (KNOWLEDGE_DIR / "outlook_mailbox_quota.md").read_text(encoding="utf-8")
    assert "purge unwanted items" not in quota_text.lower()
    assert "không thực hiện purge" in quota_text.lower()

    # 3. high_cpu_ram_disk: must separate user self-service from IT admin steps
    cpu_text = (KNOWLEDGE_DIR / "high_cpu_ram_disk.md").read_text(encoding="utf-8")
    assert "user self-service actions" in cpu_text.lower()
    assert "it tier 2 administration actions" in cpu_text.lower()
    assert "chỉnh startup type thành disabled" not in cpu_text.lower()

    # 4. outlook_ost_corruption: must include prerequisite sync verification
    ost_text = (KNOWLEDGE_DIR / "outlook_ost_corruption.md").read_text(encoding="utf-8")
    assert "prerequisite & synchronization safety check" in ost_text.lower()
    assert "webmail" in ost_text.lower()
    assert "user@company.com.ost.old" in ost_text


def test_builtin_knowledge_is_not_overwritten_on_startup(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """AUD-18: Packaged safety updates require explicit versioned review, not startup overwrite."""
    from app import store
    monkeypatch.setattr(store, "_database_url", "")
    monkeypatch.setattr(store, "_database_path", tmp_path / "test_sync.sqlite3")
    store.initialize_store()

    # Initial seed check
    doc = store.get_knowledge_document("dns_dhcp_conflict.md")
    assert doc is not None
    assert "nslookup company.internal" in doc["content"]

    # Simulate DB content that differs from the packaged version
    with store._connect() as conn:
        conn.execute("UPDATE knowledge_documents SET content = 'OLD VERSION' WHERE slug = 'dns_dhcp_conflict.md'")
    assert store.get_knowledge_document("dns_dhcp_conflict.md")["content"] == "OLD VERSION"

    # Startup must preserve the authoritative database content
    with store._connect() as conn:
        store.seed_builtin_knowledge(conn)

    updated_doc = store.get_knowledge_document("dns_dhcp_conflict.md")
    assert updated_doc["content"] == "OLD VERSION"
