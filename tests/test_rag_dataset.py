import csv
import hashlib
from pathlib import Path

from app.rag import (
    generate_answer,
    is_out_of_scope,
    load_rag_dictionary,
    reload_rag_dictionary,
    retrieve_relevant_context,
)
from scripts.evaluation_support import FROZEN_DATASET_HASHES

DATASET = Path(__file__).resolve().parents[1] / "data" / "evaluation" / "rag_questions.csv"
HOLDOUT_DATASET = Path(__file__).resolve().parents[1] / "data" / "evaluation" / "rag_holdout.csv"
DATASET_CARD = Path(__file__).resolve().parents[1] / "data" / "evaluation" / "DATASET_CARD.md"


def test_evaluation_datasets_provenance_and_frozen_hash() -> None:
    """AUD-19: Verify dataset integrity, provenance, and frozen SHA-256 hashes."""
    assert DATASET_CARD.is_file(), "DATASET_CARD.md must exist to document provenance and protocol"
    card_text = DATASET_CARD.read_text(encoding="utf-8")
    assert "1.0.0-frozen" in card_text
    assert "Frozen Fixed Regression Benchmark Gate Set" in card_text
    assert FROZEN_DATASET_HASHES["rag_questions.csv"] in card_text
    assert FROZEN_DATASET_HASHES["rag_holdout.csv"] in card_text

    for filename, expected_hash in FROZEN_DATASET_HASHES.items():
        file_path = DATASET.parent / filename
        assert file_path.is_file(), f"Dataset file {filename} must exist"
        actual_hash = hashlib.sha256(file_path.read_bytes()).hexdigest()
        assert actual_hash == expected_hash, (
            f"Dataset {filename} SHA-256 hash mismatch! Expected {expected_hash}, got {actual_hash}. "
            "Evaluation datasets are frozen benchmarks; any changes require audit approval and protocol update."
        )

        with file_path.open(encoding="utf-8-sig", newline="") as f:
            rows = list(csv.DictReader(f))
        for row in rows:
            assert row["id"], f"Missing id in {filename}"
            assert row["question"], f"Missing question in {filename}:{row['id']}"
            assert row["topic"], f"Missing topic in {filename}:{row['id']}"
            assert row["scope"] in {"in_scope", "out_of_scope"}, f"Invalid scope in {filename}:{row['id']}"
            assert row["required_evidence"], f"Missing required_evidence in {filename}:{row['id']}"


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
    non_existent = tmp_path / "missing.json"
    stopwords, synonyms, compounds, category_map, urgent, high, out_of_scope = load_rag_dictionary(non_existent)
    assert "wifi" in synonyms
    assert ("may", "in") in compounds
    assert "thoi tiet" in out_of_scope

    actual_dict = Path(__file__).resolve().parents[1] / "data" / "rag_dictionary.json"
    s_w, syn, comp, cat, urg, hp, oos = load_rag_dictionary(actual_dict)
    assert len(s_w) > 30
    assert "printer" in syn.values()
    assert ("may", "in") in comp
    assert "ad_account_lockout.md" in cat

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
    with HOLDOUT_DATASET.open(encoding="utf-8-sig", newline="") as file:
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


def test_out_of_scope_refusal_rubric() -> None:
    """AUD-19: Explicitly score refusal justification on all out-of-scope questions."""
    for path in [DATASET, HOLDOUT_DATASET]:
        with path.open(encoding="utf-8-sig", newline="") as file:
            questions = list(csv.DictReader(file))

        oos = [q for q in questions if q["scope"] == "out_of_scope"]
        for q in oos:
            matches = retrieve_relevant_context(q["question"], top_k=3)
            assert not matches, f"Out of scope question {q['id']} in {path.name} must not retrieve matches"
            assert is_out_of_scope(q["question"]) is True, f"Question {q['id']} must be classified out-of-scope"

            ans = generate_answer(q["question"])
            assert ans["grounded"] is False, f"Refusal for {q['id']} must not be grounded in KB"
            assert "ngoài phạm vi" in ans["answer"].lower(), (
                f"Refusal answer for {q['id']} must explain out-of-scope reason"
            )
