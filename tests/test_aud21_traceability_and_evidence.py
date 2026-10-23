"""Regression tests for AUD-21: Test traceability, evidence quality, and documentation integrity."""

from pathlib import Path
import ast
import re


def test_traceability_matrix_referenced_symbols_exist() -> None:
    repo = Path(__file__).resolve().parent.parent
    trace_path = repo / "docs/TEST_TRACEABILITY.md"
    assert trace_path.exists(), "docs/TEST_TRACEABILITY.md must exist"
    trace_text = trace_path.read_text(encoding="utf-8")

    # 1. Nonexistent functions must not be referenced in the traceability matrix
    sec2_idx = trace_text.find("## 2. Ma trận truy vết chi tiết")
    assert sec2_idx != -1, "Section 2 must exist in TEST_TRACEABILITY.md"
    sec2_text = trace_text[sec2_idx:]

    assert "search_runbooks" not in sec2_text, (
        "search_runbooks does not exist in app/rag.py; must use retrieve_relevant_context"
    )
    assert "handoffToTicket" not in sec2_text, (
        "handoffToTicket does not exist in app/static/app.js; must use buildHandoffDescription/addTicketHandoff"
    )

    # 2. Referenced replacement symbols must actually exist in the codebase
    rag_text = (repo / "app/rag.py").read_text(encoding="utf-8")
    assert "def retrieve_relevant_context" in rag_text, "retrieve_relevant_context must exist in app/rag.py"

    js_text = (repo / "app/static/app.js").read_text(encoding="utf-8")
    assert "function buildHandoffDescription" in js_text, "buildHandoffDescription must exist in app/static/app.js"
    assert "function addTicketHandoff" in js_text, "addTicketHandoff must exist in app/static/app.js"

    # 3. Router paths must point to modular routers, not obsolete monolithic main.py
    obsolete_main_routes = re.findall(r"`app/main\.py`:\s*`?[A-Z/]", sec2_text)
    assert len(obsolete_main_routes) == 0, (
        f"Found {len(obsolete_main_routes)} route references pointing to obsolete app/main.py: {obsolete_main_routes}"
    )

    # 4. Acceptance status must not claim unverified 100% blanket pass for UI/Cloud in the matrix
    assert "**Đạt 100%**" not in sec2_text, (
        "Section 2 of docs/TEST_TRACEABILITY.md should not use blanket '**Đạt 100%**' without distinguishing API vs UI/E2E/Cloud acceptance"
    )


def test_html_escaping_test_calls_product_code() -> None:
    repo = Path(__file__).resolve().parent.parent
    api_test_path = repo / "tests/test_api.py"
    api_text = api_test_path.read_text(encoding="utf-8")

    tree = ast.parse(api_text, filename=str(api_test_path))
    func_node = None
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef) and node.name == "test_html_escaping_in_email_dispatch":
            func_node = node
            break

    assert func_node is not None, "test_html_escaping_in_email_dispatch must exist in tests/test_api.py"
    func_source = ast.get_source_segment(api_text, func_node)
    assert func_source is not None

    # Must exercise product code in app.email_sender, not just stdlib html.escape
    assert "email_sender" in func_source, (
        "test_html_escaping_in_email_dispatch must call app.email_sender product code"
    )
    assert "_send_via_resend" in func_source or "_send_via_brevo" in func_source or "dispatch_email" in func_source, (
        "test_html_escaping_in_email_dispatch must exercise actual email dispatch methods"
    )
    assert "&lt;script&gt;" in func_source, "Test must assert escaped HTML entities"
    assert "<script>" in func_source, "Test must assert raw <script> is not in outbound HTML"


def test_deployment_demo_mode_documentation_matches_code() -> None:
    repo = Path(__file__).resolve().parent.parent
    config_text = (repo / "app/config.py").read_text(encoding="utf-8")
    deploy_text = (repo / "docs/DEPLOYMENT.md").read_text(encoding="utf-8")

    # Code default is explicitly "false"
    assert 'os.getenv("DEMO_MODE", "false")' in config_text

    # DEPLOYMENT.md must not falsely claim default is true
    assert "`DEMO_MODE` mặc định là `true`" not in deploy_text, (
        "docs/DEPLOYMENT.md must not state that DEMO_MODE default is true"
    )
    assert "| `DEMO_MODE` | `true` |" not in deploy_text, (
        "docs/DEPLOYMENT.md table must not declare default as true"
    )
    assert "| `DEMO_MODE` | `false` |" in deploy_text, (
        "docs/DEPLOYMENT.md table must declare code default as false"
    )


def test_technical_debt_exit_criteria_integrity() -> None:
    repo = Path(__file__).resolve().parent.parent
    debt_text = (repo / "docs/DEFECT_TECH_DEBT_LOG.md").read_text(encoding="utf-8")

    # TD-09 must not be closed prematurely via in-memory TestClient RPS
    assert not re.search(r"\|\s*TD-09\s*\|.*?\|\s*\*\*ĐÃ ĐÓNG \(Closed\)\*\*", debt_text), (
        "TD-09 must not be marked closed while RAG BM25 is only 35 RPS and tested in-memory only"
    )
    assert "Reopened (AUD-21)" in debt_text or "Đang mở" in debt_text

    # TD-04 must clarify ongoing status
    assert not re.search(r"\|\s*TD-04\s*\|.*?\|\s*\*\*ĐÃ ĐÓNG \(Closed\)\*\*", debt_text), (
        "TD-04 must not be marked closed without noting missing centralized user audit log and UX expiry"
    )

    # TD-05 must clarify frozen benchmark gate status
    assert "Frozen Regression Benchmark" in debt_text or "Frozen Benchmark" in debt_text
