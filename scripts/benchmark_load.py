from __future__ import annotations

import argparse
import os
import statistics
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timedelta, timezone
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

os.environ.setdefault("DEMO_MODE", "true")
os.environ.setdefault("SECRET_KEY", "benchmark-load-secret-key-at-least-32-chars-long")

import jwt  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
from app.config import ALGORITHM, SECRET_KEY  # noqa: E402
from app.main import app  # noqa: E402
from app.rag import build_retrieval_index  # noqa: E402
from app import store  # noqa: E402


def create_benchmark_token(username: str = "user", role: str = "user") -> str:
    now = datetime.now(timezone.utc)
    payload = {
        "sub": username,
        "role": role,
        "iat": now,
        "exp": now + timedelta(hours=2),
    }
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)


def run_benchmark(
    endpoint: str,
    method: str = "GET",
    payload: dict | None = None,
    total_requests: int = 150,
    concurrency: int = 10,
    headers: dict[str, str] | None = None,
) -> dict[str, float | int]:
    client = TestClient(app)
    latencies: list[float] = []
    success_count = 0
    failure_count = 0

    def single_request() -> tuple[bool, float]:
        t0 = time.perf_counter()
        try:
            if method == "POST":
                res = client.post(endpoint, json=payload, headers=headers)
            else:
                res = client.get(endpoint, headers=headers)
            duration = (time.perf_counter() - t0) * 1000.0
            return (res.status_code in {200, 201}, duration)
        except Exception:
            duration = (time.perf_counter() - t0) * 1000.0
            return (False, duration)

    start_time = time.perf_counter()
    with ThreadPoolExecutor(max_workers=concurrency) as executor:
        futures = [executor.submit(single_request) for _ in range(total_requests)]
        for fut in as_completed(futures):
            ok, duration = fut.result()
            latencies.append(duration)
            if ok:
                success_count += 1
            else:
                failure_count += 1

    total_time = time.perf_counter() - start_time
    rps = total_requests / total_time if total_time > 0 else 0.0

    latencies.sort()
    p50 = statistics.median(latencies) if latencies else 0.0
    p90 = latencies[int(len(latencies) * 0.90)] if latencies else 0.0
    p95 = latencies[int(len(latencies) * 0.95)] if latencies else 0.0
    p99 = latencies[int(len(latencies) * 0.99)] if latencies else 0.0
    mean_lat = statistics.mean(latencies) if latencies else 0.0

    return {
        "total_requests": total_requests,
        "concurrency": concurrency,
        "total_time_sec": round(total_time, 3),
        "rps": round(rps, 1),
        "success": success_count,
        "failures": failure_count,
        "mean_ms": round(mean_lat, 2),
        "p50_ms": round(p50, 2),
        "p90_ms": round(p90, 2),
        "p95_ms": round(p95, 2),
        "p99_ms": round(p99, 2),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Benchmark OpsMind Helpdesk API throughput and latency.")
    parser.add_argument("--requests", type=int, default=150, help="Total requests per test case (default: 150)")
    parser.add_argument("--concurrency", type=int, default=10, help="Concurrency level (default: 10)")
    args = parser.parse_args()

    store.initialize_store()
    build_retrieval_index()

    auth_token = create_benchmark_token("user", "user")
    auth_headers = {"Authorization": f"Bearer {auth_token}"}

    test_cases = [
        {"name": "Healthcheck", "endpoint": "/health", "method": "GET", "payload": None, "headers": None},
        {"name": "Public Config", "endpoint": "/config", "method": "GET", "payload": None, "headers": None},
        {
            "name": "RAG BM25 Retrieval",
            "endpoint": "/rag/ask",
            "method": "POST",
            "payload": {"question": "Làm sao kết nối VPN FortiClient khi báo lỗi sai mật khẩu?"},
            "headers": auth_headers,
        },
        {"name": "Knowledge Runbooks", "endpoint": "/knowledge", "method": "GET", "payload": None, "headers": auth_headers},
    ]

    print("=" * 82)
    print(" OpsMind Helpdesk — Performance & Load Benchmark (NFR-02 Verification)")
    print(f" Requests per endpoint: {args.requests} | Concurrency: {args.concurrency}")
    print("=" * 82)
    print(f"{'Endpoint':<22} | {'Reqs':>6} | {'RPS':>8} | {'Mean(ms)':>9} | {'p50(ms)':>8} | {'p95(ms)':>8} | {'Status':>6}")
    print("-" * 82)

    results = []
    for tc in test_cases:
        res = run_benchmark(
            endpoint=tc["endpoint"],
            method=tc["method"],
            payload=tc["payload"],
            total_requests=args.requests,
            concurrency=args.concurrency,
            headers=tc["headers"],
        )
        results.append((tc["name"], res))
        status_ok = "PASS" if res["failures"] == 0 else f"ERR({res['failures']})"
        print(
            f"{tc['name']:<22} | {res['total_requests']:>6} | {res['rps']:>8.1f} | "
            f"{res['mean_ms']:>9.2f} | {res['p50_ms']:>8.2f} | {res['p95_ms']:>8.2f} | {status_ok:>6}"
        )

    print("-" * 82)
    print("\nSummary for Graduation Thesis Appendix (Phụ lục Báo cáo Thực nghiệm):")
    print("| Nghiệp vụ / Endpoint | Số request | Concurrency | Thông lượng (RPS) | Latency TB (ms) | p50 (ms) | p95 (ms) |")
    print("|---|:---:|:---:|:---:|:---:|:---:|:---:|")
    for name, res in results:
        print(f"| {name} | {res['total_requests']} | {res['concurrency']} | **{res['rps']} req/s** | {res['mean_ms']} ms | {res['p50_ms']} ms | {res['p95_ms']} ms |")
    print()


if __name__ == "__main__":
    main()
