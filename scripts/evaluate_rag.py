from __future__ import annotations

import csv
import math
import statistics
import time
from pathlib import Path

from app.rag import retrieve_relevant_context

ROOT = Path(__file__).resolve().parents[1]
DATASET = ROOT / "data" / "evaluation" / "rag_questions.csv"


def main() -> int:
    with DATASET.open(encoding="utf-8-sig", newline="") as file:
        rows = list(csv.DictReader(file))

    if not rows:
        raise SystemExit("The RAG evaluation dataset is empty.")

    in_scope = [row for row in rows if row["scope"] == "in_scope"]
    out_of_scope = [row for row in rows if row["scope"] == "out_of_scope"]
    latencies: list[float] = []
    hits = 0
    refusals = 0
    misses: list[str] = []

    for row in rows:
        started = time.perf_counter()
        matches = retrieve_relevant_context(row["question"], top_k=3)
        latencies.append((time.perf_counter() - started) * 1000)
        if row["scope"] == "in_scope":
            if any(match["source"] == row["expected_source"] for match in matches):
                hits += 1
            else:
                misses.append(row["id"])
        elif not matches:
            refusals += 1
        else:
            misses.append(row["id"])

    ordered = sorted(latencies)
    p95 = ordered[max(0, math.ceil(0.95 * len(ordered)) - 1)]
    print(f"Dataset: {len(rows)} questions ({len(in_scope)} in-scope, {len(out_of_scope)} out-of-scope)")
    print(f"Context hit@3: {hits}/{len(in_scope)} ({hits / len(in_scope):.1%})")
    print(f"Out-of-scope refusal: {refusals}/{len(out_of_scope)}")
    print(f"Retrieval latency: median={statistics.median(latencies):.2f}ms, p95={p95:.2f}ms")
    print(f"Missed/false-retrieval question IDs: {', '.join(misses) if misses else 'none'}")
    print("This lexical retrieval baseline does not measure answer faithfulness or usability.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
