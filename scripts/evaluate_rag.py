from __future__ import annotations

import csv
import hashlib
import math
import os
import re
import statistics
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

os.environ.setdefault("DEMO_MODE", "true")
os.environ.setdefault("SECRET_KEY", "evaluate-rag-offline-secret-key-safe")

from app.rag import generate_answer, is_out_of_scope, retrieve_relevant_context  # noqa: E402

DEV_DATASET = ROOT / "data" / "evaluation" / "rag_questions.csv"
HOLDOUT_DATASET = ROOT / "data" / "evaluation" / "rag_holdout.csv"

FROZEN_DATASET_HASHES = {
    "rag_questions.csv": "9a0fc80667527170c7dad3476a26374a5183a7b8374795b6ec35d1482ae5ad4d",
    "rag_holdout.csv": "aaaf9673ed6d886ff5faa46f2a0bbcff92629cb024acd0cefb9e763706fad872",
}


def score_evidence_rubric(required_evidence: str, text: str) -> tuple[float, list[str], list[str]]:
    items = [item.strip() for item in required_evidence.split(";") if item.strip()]
    if not items:
        return 1.0, [], []
    covered: list[str] = []
    missing: list[str] = []
    text_lower = text.lower()
    for item in items:
        item_lower = item.lower()
        tokens = [t for t in re.split(r"[\s/,]+", item_lower) if len(t) > 2]
        if item_lower in text_lower:
            covered.append(item)
        elif tokens and all(t in text_lower for t in tokens):
            covered.append(item)
        elif tokens and any(t in text_lower for t in tokens):
            covered.append(item)
        else:
            missing.append(item)
    score = len(covered) / len(items) if items else 1.0
    return score, covered, missing


def evaluate_dataset(dataset_path: Path) -> dict[str, float | list[str]]:
    if not dataset_path.is_file():
        raise FileNotFoundError(f"Dataset not found: {dataset_path}")

    raw_bytes = dataset_path.read_bytes()
    file_sha256 = hashlib.sha256(raw_bytes).hexdigest()
    expected_hash = FROZEN_DATASET_HASHES.get(dataset_path.name)
    hash_status = "MATCH (VERIFIED)" if expected_hash and expected_hash == file_sha256 else "UNVERIFIED"

    with dataset_path.open(encoding="utf-8-sig", newline="") as file:
        rows = list(csv.DictReader(file))

    if not rows:
        raise ValueError(f"The RAG evaluation dataset {dataset_path.name} is empty.")

    in_scope = [row for row in rows if row["scope"] == "in_scope"]
    out_of_scope = [row for row in rows if row["scope"] == "out_of_scope"]
    pure_oos = [row for row in out_of_scope if row.get("topic") == "Pure OOS"]
    near_domain_oos = [row for row in out_of_scope if row.get("topic") == "Near-domain OOS"]

    latencies: list[float] = []
    hit1 = 0
    hit3 = 0
    reciprocal_ranks: list[float] = []
    false_in_scope_refusals = 0
    refusals = 0
    pure_refusals = 0
    near_refusals = 0
    misses: list[str] = []

    evidence_scores: list[float] = []
    evidence_hits = 0
    refusal_justifications = 0
    rubric_misses: list[str] = []

    for row in rows:
        started = time.perf_counter()
        matches = retrieve_relevant_context(row["question"], top_k=3)
        latencies.append((time.perf_counter() - started) * 1000)

        if row["scope"] == "in_scope":
            if not matches or is_out_of_scope(row["question"]):
                false_in_scope_refusals += 1
                misses.append(f"{row['id']} (false-refusal: marked out_of_scope)")
                reciprocal_ranks.append(0.0)
                evidence_scores.append(0.0)
                rubric_misses.append(f"{row['id']} (evidence: retrieval empty)")
                continue

            expected = row["expected_source"]
            matched_sources = [m["source"] for m in matches]
            if expected in matched_sources:
                hit3 += 1
                rank = matched_sources.index(expected) + 1
                reciprocal_ranks.append(1.0 / rank)
                if rank == 1:
                    hit1 += 1
            else:
                reciprocal_ranks.append(0.0)
                misses.append(f"{row['id']} (expected {expected}, got {matched_sources})")

            combined_context = " ".join([m.get("title", "") + " " + m.get("content", "") for m in matches])
            req_ev = row.get("required_evidence", "")
            cov_score, cov_items, miss_items = score_evidence_rubric(req_ev, combined_context)
            evidence_scores.append(cov_score)
            if cov_score > 0.0:
                evidence_hits += 1
            else:
                rubric_misses.append(f"{row['id']} (zero evidence matched for {req_ev})")
        else:
            is_refused = (not matches) and is_out_of_scope(row["question"])
            if is_refused:
                refusals += 1
                if row.get("topic") == "Pure OOS":
                    pure_refusals += 1
                elif row.get("topic") == "Near-domain OOS":
                    near_refusals += 1

                ans = generate_answer(row["question"])
                if ans.get("grounded") is False and "ngoài phạm vi" in ans.get("answer", "").lower():
                    refusal_justifications += 1
                else:
                    rubric_misses.append(f"{row['id']} (refused but answer lacking scope explanation)")
            else:
                misses.append(f"{row['id']} (out_of_scope, but retrieved {[m['source'] for m in matches]})")

    ordered = sorted(latencies)
    p95 = ordered[max(0, math.ceil(0.95 * len(ordered)) - 1)]
    mrr = statistics.mean(reciprocal_ranks) if reciprocal_ranks else 0.0
    hit1_rate = hit1 / len(in_scope) if in_scope else 1.0
    hit3_rate = hit3 / len(in_scope) if in_scope else 1.0
    false_refusal_rate = false_in_scope_refusals / len(in_scope) if in_scope else 0.0
    refusal_rate = refusals / len(out_of_scope) if out_of_scope else 1.0
    pure_refusal_rate = pure_refusals / len(pure_oos) if pure_oos else refusal_rate
    near_refusal_rate = near_refusals / len(near_domain_oos) if near_domain_oos else refusal_rate

    evidence_hit_rate = evidence_hits / len(in_scope) if in_scope else 1.0
    evidence_coverage_avg = statistics.mean(evidence_scores) if evidence_scores else 0.0
    refusal_justification_rate = refusal_justifications / len(out_of_scope) if out_of_scope else 1.0

    print(f"\n[{dataset_path.name}] {len(rows)} cau ({len(in_scope)} in-scope, {len(out_of_scope)} out-of-scope)")
    print(f"  • SHA-256: {file_sha256[:16]}... [{hash_status}]")
    print("  --- Section 1: Retrieval CI Gate ---")
    print(f"  • In-scope Hit@1: {hit1}/{len(in_scope)} ({hit1_rate:.1%})")
    print(f"  • In-scope Hit@3: {hit3}/{len(in_scope)} ({hit3_rate:.1%})")
    print(f"  • In-scope MRR@3: {mrr:.3f}")
    print(f"  • False-positive in-scope refusal: {false_in_scope_refusals}/{len(in_scope)} ({false_refusal_rate:.1%})")
    if pure_oos or near_domain_oos:
        print(f"  • Pure OOS refusal: {pure_refusals}/{len(pure_oos)} ({pure_refusal_rate:.1%})")
        print(f"  • Near-domain OOS refusal: {near_refusals}/{len(near_domain_oos)} ({near_refusal_rate:.1%})")
    else:
        print(f"  • Out-of-scope refusal: {refusals}/{len(out_of_scope)} ({refusal_rate:.1%})")
    print(f"  • Retrieval latency: median={statistics.median(latencies):.2f}ms, p95={p95:.2f}ms")

    print("  --- Section 2: Answer & Evidence Rubric (AUD-19) ---")
    print(f"  • In-scope Evidence Hit@3: {evidence_hits}/{len(in_scope)} ({evidence_hit_rate:.1%})")
    print(f"  • In-scope Average Evidence Coverage: {evidence_coverage_avg:.1%}")
    print(f"  • Out-of-scope Refusal Justification: {refusal_justifications}/{len(out_of_scope)} ({refusal_justification_rate:.1%})")

    if misses:
        print("  • Retrieval Misses:")
        for m in misses:
            print(f"    - {m}")
    else:
        print("  • Retrieval Misses: None (100% gate passed)")

    if rubric_misses:
        print("  • Rubric Misses:")
        for rm in rubric_misses:
            print(f"    - {rm}")
    else:
        print("  • Rubric Misses: None (100% rubric passed)")

    return {
        "hit1_rate": hit1_rate,
        "hit3_rate": hit3_rate,
        "mrr": mrr,
        "false_refusal_rate": false_refusal_rate,
        "refusal_rate": refusal_rate,
        "pure_refusal_rate": pure_refusal_rate,
        "near_refusal_rate": near_refusal_rate,
        "p95_latency": p95,
        "evidence_hit_rate": evidence_hit_rate,
        "evidence_coverage_avg": evidence_coverage_avg,
        "refusal_justification_rate": refusal_justification_rate,
        "misses": misses,
        "rubric_misses": rubric_misses,
    }


def main() -> int:
    target = None
    if len(sys.argv) > 1 and not sys.argv[1].startswith("-"):
        target = Path(sys.argv[1])
    elif "--holdout" in sys.argv:
        target = HOLDOUT_DATASET
    elif "--dev" in sys.argv:
        target = DEV_DATASET

    print("=" * 68)
    print("  OpsMind Helpdesk — RAG Retrieval Gate & Answer Rubric Evaluation")
    print("=" * 68)

    if target:
        metrics = evaluate_dataset(target)
        if (
            metrics["hit1_rate"] < 0.60
            or metrics["hit3_rate"] < 0.85
            or metrics["mrr"] < 0.70
            or metrics["refusal_rate"] < 0.80
            or metrics["false_refusal_rate"] > 0.05
            or metrics["evidence_hit_rate"] < 0.90
            or metrics["evidence_coverage_avg"] < 0.75
            or metrics["refusal_justification_rate"] < 0.90
        ):
            print("\n[FAIL] Quality or Rubric below acceptance criteria.")
            return 1
        return 0

    d_metrics = evaluate_dataset(DEV_DATASET)
    h_metrics = evaluate_dataset(HOLDOUT_DATASET)

    print("\n" + "=" * 68)
    print(
        f"Summary: Dev Hit@3={d_metrics['hit3_rate']:.1%}, "
        f"Holdout Hit@1={h_metrics['hit1_rate']:.1%}, "
        f"Holdout Hit@3={h_metrics['hit3_rate']:.1%}, "
        f"Holdout MRR@3={h_metrics['mrr']:.3f}, "
        f"Holdout Evidence Hit={h_metrics['evidence_hit_rate']:.1%}, "
        f"Holdout Coverage={h_metrics['evidence_coverage_avg']:.1%}, "
        f"OOS Refusal Justification={h_metrics['refusal_justification_rate']:.1%}"
    )
    print("=" * 68)

    if (
        d_metrics["hit3_rate"] < 0.90
        or h_metrics["hit1_rate"] < 0.60
        or h_metrics["hit3_rate"] < 0.85
        or h_metrics["mrr"] < 0.70
        or h_metrics["pure_refusal_rate"] < 0.90
        or h_metrics["near_refusal_rate"] < 0.80
        or h_metrics["false_refusal_rate"] > 0.05
        or h_metrics["evidence_hit_rate"] < 0.90
        or h_metrics["evidence_coverage_avg"] < 0.80
        or h_metrics["refusal_justification_rate"] < 0.90
    ):
        print("\n[FAIL] Quality or Rubric below acceptance criteria.")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
