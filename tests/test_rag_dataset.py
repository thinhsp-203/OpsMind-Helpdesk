import csv
from pathlib import Path

from app.rag import (
    generate_answer,
    is_out_of_scope,
    load_rag_dictionary,
    reload_rag_dictionary,
    retrieve_relevant_context,
)

DATASET = Path(__file__).resolve().parents[1] / "data" / "evaluation" / "rag_questions.csv"


def test_draft_evaluation_set_has_thirty_questions_and_expected_sources() -> None:
    with DATASET.open(encoding="utf-8-sig", newline="") as file:
        questions = list(csv.DictReader(file))

    assert len(questions) == 30
    for question in questions:
        matches = retrieve_relevant_context(question["question"], top_k=3)
        if question["scope"] == "in_scope":
            assert any(match["source"] == question["expected_source"] for match in matches), question["id"]
        else:
            assert not matches, question["id"]


def test_load_rag_dictionary_from_file_and_fallback(tmp_path: Path) -> None:
    # Test fallback on non-existent path
    non_existent = tmp_path / "missing.json"
    stopwords, synonyms, compounds, category_map, urgent, high, out_of_scope = load_rag_dictionary(non_existent)
    assert "wifi" in synonyms
    assert ("may", "in") in compounds
    assert "thoi tiet" in out_of_scope

    # Test loading actual dictionary
    actual_dict = Path(__file__).resolve().parents[1] / "data" / "rag_dictionary.json"
    s_w, syn, comp, cat, urg, hp, oos = load_rag_dictionary(actual_dict)
    assert len(s_w) > 30
    assert "printer" in syn.values()
    assert ("may", "in") in comp
    assert "ad_account_lockout.md" in cat

    # Reload preserves functionality
    reload_rag_dictionary(actual_dict)


def test_out_of_scope_guardrail_refusal() -> None:
    query = "Dự báo thời tiết hôm nay và ngày mai thế nào?"
    assert is_out_of_scope(query) is True
    assert retrieve_relevant_context(query) == []

    ans = generate_answer(query)
    assert ans["grounded"] is False
    assert ans["triage"]["category"] == "general"
    assert "ngoài phạm vi" in ans["answer"].lower()

