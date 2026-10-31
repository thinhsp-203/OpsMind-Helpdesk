"""Shared, deliberately lexical checks; these do not measure answer faithfulness."""
from __future__ import annotations

import re
import unicodedata

FROZEN_DATASET_HASHES = {
    "rag_questions.csv": "8e1bf0f6a4024e3515ef8f4a8077e3558bd29dcbff426bf3182a5d112781c994",
    "rag_holdout.csv": "d272c6cc0540745dc4b0d2590f1eb208d2968e7d55b0cfca2ebce1e4d53abbaf",
}


def _words(text: str) -> tuple[str, ...]:
    # Preserve accents and negation. Normalize case, whitespace and punctuation only.
    return tuple(re.findall(r"\w+", unicodedata.normalize("NFC", text).casefold()))


def score_evidence_rubric(required_evidence: str, text: str | list[str]) -> tuple[float, list[str], list[str]]:
    """Fraction of complete evidence phrases found, with word boundaries.

    Empty annotations are unscorable (0), not perfect. Even an exact match may
    appear in a negated or unsafe statement: this is a lexical context diagnostic,
    not a semantic/answer quality gate. Human assessment is required separately.
    """
    items = [item.strip() for item in required_evidence.split(";") if item.strip()]
    passages = [_words(passage) for passage in ([text] if isinstance(text, str) else text)]
    covered, missing = [], []
    for item in items:
        phrase = _words(item)
        found = bool(phrase) and any(
            words[i:i + len(phrase)] == phrase
            for words in passages for i in range(len(words) - len(phrase) + 1)
        )
        (covered if found else missing).append(item)
    return len(covered) / len(items) if items else 0.0, covered, missing
