import csv
from pathlib import Path

from app.rag import retrieve_relevant_context

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
