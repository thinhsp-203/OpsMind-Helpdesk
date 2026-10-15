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


def test_holdout_evaluation_set_quality_gate() -> None:
    holdout_file = Path(__file__).resolve().parents[1] / "data" / "evaluation" / "rag_holdout.csv"
    with holdout_file.open(encoding="utf-8-sig", newline="") as file:
        questions = list(csv.DictReader(file))

    assert len(questions) == 60
    in_scope = [q for q in questions if q["scope"] == "in_scope"]
    out_of_scope = [q for q in questions if q["scope"] == "out_of_scope"]
    pure_oos = [q for q in out_of_scope if q.get("topic") == "Pure OOS"]
    near_domain_oos = [q for q in out_of_scope if q.get("topic") == "Near-domain OOS"]

    assert len(in_scope) == 30
    assert len(out_of_scope) == 30
    assert len(pure_oos) == 15
    assert len(near_domain_oos) == 15

    hit1 = 0
    hit3 = 0
    rr_scores: list[float] = []
    false_refusals = 0
    for q in in_scope:
        matches = retrieve_relevant_context(q["question"], top_k=3)
        if not matches or is_out_of_scope(q["question"]):
            false_refusals += 1
            rr_scores.append(0.0)
            continue
        sources = [m["source"] for m in matches]
        if q["expected_source"] in sources:
            hit3 += 1
            rank = sources.index(q["expected_source"]) + 1
            rr_scores.append(1.0 / rank)
            if rank == 1:
                hit1 += 1
        else:
            rr_scores.append(0.0)

    near_refusals = sum(1 for q in near_domain_oos if not retrieve_relevant_context(q["question"], top_k=3) and is_out_of_scope(q["question"]))
    pure_refusals = sum(1 for q in pure_oos if not retrieve_relevant_context(q["question"], top_k=3) and is_out_of_scope(q["question"]))

    hit1_rate = hit1 / len(in_scope)
    hit3_rate = hit3 / len(in_scope)
    mrr = sum(rr_scores) / len(rr_scores) if rr_scores else 0.0
    false_refusal_rate = false_refusals / len(in_scope)
    near_rate = near_refusals / len(near_domain_oos)
    pure_rate = pure_refusals / len(pure_oos)

    assert hit1_rate >= 0.60, f"Holdout Hit@1 rate too low: {hit1_rate:.2%}"
    assert hit3_rate >= 0.85, f"Holdout Hit@3 rate too low: {hit3_rate:.2%}"
    assert mrr >= 0.70, f"Holdout MRR@3 too low: {mrr:.3f}"
    assert false_refusal_rate <= 0.05, f"Holdout false in-scope refusal rate too high: {false_refusal_rate:.2%}"
    assert near_rate >= 0.80, f"Holdout near-domain refusal rate too low: {near_rate:.2%}"
    assert pure_rate >= 0.90, f"Holdout pure refusal rate too low: {pure_rate:.2%}"


