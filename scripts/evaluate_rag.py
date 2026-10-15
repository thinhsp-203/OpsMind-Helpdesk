from __future__ import annotations

import csv
import math
import os
import statistics
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

os.environ.setdefault("DEMO_MODE", "true")
os.environ.setdefault("SECRET_KEY", "evaluate-rag-offline-secret-key-safe")

from app.rag import retrieve_relevant_context  # noqa: E402

DEV_DATASET = ROOT / "data" / "evaluation" / "rag_questions.csv"
HOLDOUT_DATASET = ROOT / "data" / "evaluation" / "rag_holdout.csv"


def evaluate_dataset(dataset_path: Path) -> tuple[float, float, float, list[str]]:
    if not dataset_path.is_file():
        raise FileNotFoundError(f"Dataset not found: {dataset_path}")

    with dataset_path.open(encoding="utf-8-sig", newline="") as file:
        rows = list(csv.DictReader(file))

    if not rows:
        raise ValueError(f"The RAG evaluation dataset {dataset_path.name} is empty.")

    in_scope = [row for row in rows if row["scope"] == "in_scope"]
    out_of_scope = [row for row in rows if row["scope"] == "out_of_scope"]
    latencies: list[float] = []
    hit1 = 0
    hit3 = 0
    reciprocal_ranks: list[float] = []
    refusals = 0
    misses: list[str] = []

    for row in rows:
        started = time.perf_counter()
        matches = retrieve_relevant_context(row["question"], top_k=3)
        latencies.append((time.perf_counter() - started) * 1000)

        if row["scope"] == "in_scope":
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
        else:
            if not matches:
                refusals += 1
            else:
                misses.append(f"{row['id']} (out_of_scope, but retrieved {[m['source'] for m in matches]})")

    ordered = sorted(latencies)
    p95 = ordered[max(0, math.ceil(0.95 * len(ordered)) - 1)]
    mrr = statistics.mean(reciprocal_ranks) if reciprocal_ranks else 0.0
    hit3_rate = hit3 / len(in_scope) if in_scope else 1.0
    hit1_rate = hit1 / len(in_scope) if in_scope else 1.0
    refusal_rate = refusals / len(out_of_scope) if out_of_scope else 1.0

    print(f"\n[{dataset_path.name}] {len(rows)} câu ({len(in_scope)} in-scope, {len(out_of_scope)} out-of-scope)")
    print(f"  • Hit@1: {hit1}/{len(in_scope)} ({hit1_rate:.1%})")
    print(f"  • Hit@3: {hit3}/{len(in_scope)} ({hit3_rate:.1%})")
    print(f"  • MRR@3: {mrr:.3f}")
    print(f"  • Out-of-scope refusal: {refusals}/{len(out_of_scope)} ({refusal_rate:.1%})")
    print(f"  • Retrieval latency: median={statistics.median(latencies):.2f}ms, p95={p95:.2f}ms")
    if misses:
        print("  • Missed/False-retrievals:\n    - " + "\n    - ".join(misses))
    else:
        print("  • Missed/False-retrievals: None (100% matched)")

    return hit3_rate, refusal_rate, mrr, misses


def main() -> int:
    target = None
    if len(sys.argv) > 1 and not sys.argv[1].startswith("-"):
        target = Path(sys.argv[1])
    elif "--holdout" in sys.argv:
        target = HOLDOUT_DATASET
    elif "--dev" in sys.argv:
        target = DEV_DATASET

    print("=" * 65)
    print("  OpsMind Helpdesk — RAG Retrieval & Guardrail Evaluation")
    print("=" * 65)

    if target:
        hit3_rate, refusal_rate, mrr, misses = evaluate_dataset(target)
        if hit3_rate < 0.85 or refusal_rate < 0.80:
            print("\n[FAIL] Quality below acceptance criteria (Hit@3 >= 85%, Refusal >= 80%).")
            return 1
        return 0

    # Evaluate both dev and holdout datasets by default
    d_hit3, d_ref, d_mrr, d_miss = evaluate_dataset(DEV_DATASET)
    h_hit3, h_ref, h_mrr, h_miss = evaluate_dataset(HOLDOUT_DATASET)

    print("\n" + "=" * 65)
    print(f"Summary: Dev Hit@3={d_hit3:.1%}, Holdout Hit@3={h_hit3:.1%}, Holdout Refusal={h_ref:.1%}")
    print("=" * 65)

    if d_hit3 < 0.90 or h_hit3 < 0.85 or h_ref < 0.80:
        print("\n[FAIL] Quality below acceptance criteria.")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
