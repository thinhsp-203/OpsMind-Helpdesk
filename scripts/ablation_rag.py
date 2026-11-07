"""Ablation study for the lexical retrieval pipeline (retrieval only).

Each configuration adds one preprocessing step on top of the previous one, using
the same BM25 formula as app/rag.py. The last configuration must reproduce the
production ranking; the script checks this before printing any number.

Limits: the dictionary (stop words, synonyms, compounds) was tuned on these
datasets (see data/evaluation/DATASET_CARD.md), so gains from steps C-E are an
optimistic upper bound, not independent generalization. Out-of-scope gating is
disabled here so every configuration ranks the same in-scope questions.

Usage: py -m scripts.ablation_rag
"""
from __future__ import annotations

import csv
import math
import os
import re
import sys
import tempfile
import unicodedata
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

os.environ.setdefault("DEMO_MODE", "true")
os.environ.setdefault("SECRET_KEY", "ablation-rag-offline-secret-key-safe-32")
# Isolated throwaway DB: never touch the local demo database.
_TMP = tempfile.mkdtemp(prefix="opsmind-ablation-")
os.environ["HELPDESK_DB_PATH"] = str(Path(_TMP) / "ablation.sqlite3")
os.environ["HELPDESK_STORAGE_PATH"] = _TMP
os.environ["DATABASE_URL"] = ""
os.environ["ENABLE_LLM_GENERATION"] = "false"

from app import rag  # noqa: E402

DATASETS = [ROOT / "data" / "evaluation" / "rag_questions.csv",
            ROOT / "data" / "evaluation" / "rag_holdout.csv"]
RAW_TOKEN_RE = re.compile(r"\w+")

CONFIGS = [
    ("A", "BM25 thô (chữ thường, giữ dấu)", dict(fold=False, stop=False, lexicon=False, title=False)),
    ("B", "A + bỏ dấu tiếng Việt", dict(fold=True, stop=False, lexicon=False, title=False)),
    ("C", "B + từ dừng", dict(fold=True, stop=True, lexicon=False, title=False)),
    ("D", "C + từ đồng nghĩa & từ ghép", dict(fold=True, stop=True, lexicon=True, title=False)),
    ("E", "D + tăng trọng số tiêu đề (= hệ thống)", dict(fold=True, stop=True, lexicon=True, title=True)),
]


def tokenize(text: str, *, fold: bool, stop: bool, lexicon: bool, **_: bool) -> list[str]:
    if not fold:
        return RAW_TOKEN_RE.findall(unicodedata.normalize("NFC", text).lower())
    if lexicon and stop:
        return rag._tokens(text)  # production tokenizer
    words = rag.TOKEN_RE.findall(rag._fold_text(text))
    return [w for w in words if not (stop and w in rag.STOP_WORDS)]


def build(passages: list[dict], config: dict) -> dict:
    docs = []
    for passage in passages:
        tokens = tokenize(f"{passage['title']} {passage['content']}", **config)
        docs.append({
            "source": passage["source"],
            "tf": Counter(tokens),
            "length": len(tokens),
            "title_terms": set(tokenize(passage["title"], **config)),
        })
    df: Counter[str] = Counter()
    for doc in docs:
        df.update(doc["tf"].keys())
    avg = sum(d["length"] for d in docs) / len(docs)
    return {"docs": docs, "df": df, "avg": avg or 1.0, "n": len(docs)}


def rank(index: dict, question: str, config: dict, top_k: int = 3) -> list[str]:
    terms = sorted(set(tokenize(question, **config)))
    n, df, avg = index["n"], index["df"], index["avg"]
    scored = []
    for doc in index["docs"]:
        score = 0.0
        for term in terms:
            tf = doc["tf"][term] + (2 if config["title"] and term in doc["title_terms"] else 0)
            if not tf:
                continue
            idf = math.log(1 + (n - df[term] + 0.5) / (df[term] + 0.5))
            score += idf * (tf * 2.2 / (tf + 1.2 * (0.25 + 0.75 * doc["length"] / avg)))
        scored.append((score, doc["source"]))
    scored.sort(key=lambda item: item[0], reverse=True)
    result: list[str] = []
    for score, source in scored:
        if score < rag.MIN_RELEVANCE or source in result:
            continue
        result.append(source)
        if len(result) == top_k:
            break
    return result


def metrics(rows: list[dict], ranked: list[list[str]]) -> tuple[float, float, float]:
    hit1 = sum(1 for r, s in zip(rows, ranked) if s[:1] == [r["expected_source"]])
    hit3 = sum(1 for r, s in zip(rows, ranked) if r["expected_source"] in s)
    mrr = sum(1 / (s.index(r["expected_source"]) + 1) for r, s in zip(rows, ranked)
              if r["expected_source"] in s)
    n = len(rows)
    return hit1 / n, hit3 / n, mrr / n


def strip_diacritics(text: str) -> str:
    decomposed = unicodedata.normalize("NFD", text)
    stripped = "".join(c for c in decomposed if unicodedata.category(c) != "Mn")
    return unicodedata.normalize("NFC", stripped).replace("đ", "d").replace("Đ", "D")


def load_rows(path: Path) -> list[dict]:
    with path.open(encoding="utf-8-sig", newline="") as file:
        return [row for row in csv.DictReader(file) if row["scope"] == "in_scope"]


def coverage_sweep(rows: list[dict]) -> None:
    """Precision/recall of the chat reference gate (app.rag.KB_REFERENCE_MIN_COVERAGE)."""
    top = []
    for row in rows:
        matches = rag.retrieve_relevant_context(row["question"])
        if matches:
            top.append((matches[0]["coverage"], matches[0]["source"] == row["expected_source"]))
    correct_total = sum(1 for _, ok in top if ok)
    print("\n--- Quét ngưỡng độ phủ cho tài liệu tham khảo (top-1, dev+holdout in-scope) ---")
    print(f"{'Ngưỡng':>7} | {'Hiện':>5} | {'Đúng':>5} | {'Precision':>9} | {'Recall':>7}")
    for threshold in (0.0, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8):
        shown = [ok for cov, ok in top if cov >= threshold]
        correct = sum(shown)
        precision = correct / len(shown) if shown else 0.0
        recall = correct / correct_total if correct_total else 0.0
        mark = "  <- đang dùng" if threshold == rag.KB_REFERENCE_MIN_COVERAGE else ""
        print(f"{threshold:>7.1f} | {len(shown):>5} | {correct:>5} | {precision:>8.1%} | {recall:>6.1%}{mark}")
    print("Precision ở đây chỉ đo trên câu in-scope đã gán nhãn; không thay cho đánh giá của người dùng.")


def main() -> None:
    passages = rag.build_retrieval_index()
    if not passages:
        raise SystemExit("Knowledge Base trống; không thể chạy ablation.")
    datasets = {path.name: load_rows(path) for path in DATASETS}
    # Same questions typed without diacritics (common in chat). Mechanical
    # transform of existing rows: labels are unchanged, no new data is invented.
    datasets["holdout không dấu"] = [
        {**row, "question": strip_diacritics(row["question"])}
        for row in datasets["rag_holdout.csv"]
    ]

    # Sanity check: configuration E must reproduce production retrieval exactly.
    full = CONFIGS[-1][2]
    full_index = build(passages, full)
    all_rows = datasets["rag_questions.csv"] + datasets["rag_holdout.csv"]
    mismatches = [row["id"] for row in all_rows
                  if rank(full_index, row["question"], full)
                  != [m["source"] for m in rag.retrieve_relevant_context(row["question"])]
                  and not rag.is_out_of_scope(row["question"])]
    if mismatches:
        raise SystemExit(f"Cấu hình E lệch với app/rag.py ở: {mismatches}")

    print(f"Kho tri thức: {len({p['source'] for p in passages})} runbook, {len(passages)} đoạn")
    print("Cấu hình E khớp 100% với app/rag.py (đã kiểm tra trước khi in số).\n")
    header = f"{'':2} {'Cấu hình':42}"
    for name, rows in datasets.items():
        header += f" | {name + f' (n={len(rows)})':26} Hit@1  Hit@3  MRR@3"
    print(header)
    for key, label, config in CONFIGS:
        index = build(passages, config)
        line = f"{key:2} {label:42}"
        for rows in datasets.values():
            h1, h3, mrr = metrics(rows, [rank(index, r["question"], config) for r in rows])
            line += f" | {'':26} {h1:5.1%} {h3:6.1%} {mrr:6.3f}"
        print(line)
    print("\nLưu ý: từ điển đã được tinh chỉnh trên chính hai tập này, nên mức tăng ở C–E là cận trên lạc quan.")
    coverage_sweep(all_rows)


if __name__ == "__main__":
    main()
