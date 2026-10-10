"""Evaluate lexical retrieval quality per dataset split.

Splits:
- seed:    original 30 questions written alongside the runbooks.
- dev:     paraphrased / user-style questions used while tuning the retriever.
- holdout: questions written before tuning and never used to tune; report these numbers.
"""
from __future__ import annotations

import csv
import math
import statistics
import time
from pathlib import Path

from app.rag import retrieve_relevant_context

ROOT = Path(__file__).resolve().parents[1]
DATASET = ROOT / "data" / "evaluation" / "rag_questions.csv"
SPLITS = ("seed", "dev", "holdout")


def load_rows() -> list[dict[str, str]]:
    with DATASET.open(encoding="utf-8-sig", newline="") as file:
        return list(csv.DictReader(file))


def expected_sources(row: dict[str, str]) -> set[str]:
    return {part.strip() for part in row["expected_source"].split(";") if part.strip()}


def evaluate(rows: list[dict[str, str]]) -> dict[str, object]:
    in_scope = [row for row in rows if row["scope"] == "in_scope"]
    out_of_scope = [row for row in rows if row["scope"] == "out_of_scope"]
    latencies: list[float] = []
    hits = top1 = refusals = 0
    reciprocal_ranks: list[float] = []
    misses: list[str] = []
    for row in rows:
        started = time.perf_counter()
        matches = retrieve_relevant_context(row["question"], top_k=3)
        latencies.append((time.perf_counter() - started) * 1000)
        sources = [match["source"] for match in matches]
        if row["scope"] == "in_scope":
            expected = expected_sources(row)
            rank = next((index for index, source in enumerate(sources, 1) if source in expected), 0)
            hits += bool(rank)
            top1 += rank == 1
            reciprocal_ranks.append(1 / rank if rank else 0.0)
            if not rank:
                misses.append(row["id"])
        elif not matches:
            refusals += 1
        else:
            misses.append(row["id"])
    ordered = sorted(latencies)
    return {
        "total": len(rows),
        "in_scope": len(in_scope),
        "out_of_scope": len(out_of_scope),
        "hit_at_3": hits,
        "hit_at_1": top1,
        "mrr": statistics.mean(reciprocal_ranks) if reciprocal_ranks else 0.0,
        "refusals": refusals,
        "median_ms": statistics.median(latencies) if latencies else 0.0,
        "p95_ms": ordered[max(0, math.ceil(0.95 * len(ordered)) - 1)] if ordered else 0.0,
        "misses": misses,
    }


def main() -> int:
    rows = load_rows()
    if not rows:
        raise SystemExit("The RAG evaluation dataset is empty.")
    for split in (*SPLITS, "all"):
        subset = rows if split == "all" else [row for row in rows if row.get("split", "seed") == split]
        if not subset:
            continue
        result = evaluate(subset)
        n_in, n_out = result["in_scope"], result["out_of_scope"]
        print(f"[{split}] {result['total']} questions ({n_in} in-scope, {n_out} out-of-scope)")
        if n_in:
            print(
                f"  hit@1: {result['hit_at_1']}/{n_in} ({result['hit_at_1'] / n_in:.1%})"
                f"  hit@3: {result['hit_at_3']}/{n_in} ({result['hit_at_3'] / n_in:.1%})"
                f"  MRR@3: {result['mrr']:.3f}"
            )
        if n_out:
            print(f"  out-of-scope refusal: {result['refusals']}/{n_out} ({result['refusals'] / n_out:.1%})")
        print(f"  latency: median={result['median_ms']:.2f}ms, p95={result['p95_ms']:.2f}ms")
        print(f"  missed/false-retrieval IDs: {', '.join(result['misses']) or 'none'}")
    print("This lexical retrieval baseline does not measure answer faithfulness or usability.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
