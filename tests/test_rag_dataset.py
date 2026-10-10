import csv
from pathlib import Path

from app.rag import _tokens, generate_answer, retrieve_relevant_context

DATASET = Path(__file__).resolve().parents[1] / "data" / "evaluation" / "rag_questions.csv"


def _rows() -> list[dict[str, str]]:
    with DATASET.open(encoding="utf-8-sig", newline="") as file:
        return list(csv.DictReader(file))


def _passes(row: dict[str, str]) -> bool:
    matches = retrieve_relevant_context(row["question"], top_k=3)
    if row["scope"] == "in_scope":
        expected = {part.strip() for part in row["expected_source"].split(";") if part.strip()}
        return any(match["source"] in expected for match in matches)
    return not matches


def test_evaluation_set_has_seed_dev_and_holdout_splits() -> None:
    rows = _rows()
    counts = {split: sum(row["split"] == split for row in rows) for split in ("seed", "dev", "holdout")}
    assert counts == {"seed": 30, "dev": 36, "holdout": 30}
    assert sum(row["scope"] == "out_of_scope" for row in rows) >= 20


def test_seed_and_dev_questions_retrieve_expected_sources() -> None:
    failures = [row["id"] for row in _rows() if row["split"] in {"seed", "dev"} and not _passes(row)]
    assert not failures, failures


def test_holdout_quality_does_not_regress() -> None:
    # Holdout questions were written before tuning and are never used to tune the lexicon.
    # This is a regression floor, not a target: keep the measured numbers in RAG_BASELINE.md.
    holdout = [row for row in _rows() if row["split"] == "holdout"]
    in_scope = [row for row in holdout if row["scope"] == "in_scope"]
    out_of_scope = [row for row in holdout if row["scope"] == "out_of_scope"]
    assert sum(_passes(row) for row in in_scope) / len(in_scope) >= 0.9
    assert sum(_passes(row) for row in out_of_scope) / len(out_of_scope) >= 0.7


def test_wifi_spelling_variants_share_one_token() -> None:
    assert "wifi" in _tokens("Wi-Fi")
    assert "wifi" in _tokens("wifi")
    assert "wifi" in _tokens("wi fi")


def test_vietnamese_print_phrase_keeps_printer_signal() -> None:
    assert "printer" in _tokens("Tôi không in được tài liệu")


def test_off_topic_question_is_not_marked_grounded() -> None:
    answer = generate_answer("cách nấu phở bò")
    assert answer["grounded"] is False
    assert answer["sources"] == []
