"""HTTP load measurement; use only a dedicated test account and disposable data.

The explicit --in-process mode is a local diagnostic, not deployment/NFR evidence.
"""
from __future__ import annotations

import argparse
import json
import math
import os
import platform
import statistics
import time
from collections import Counter
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import httpx


def login_benchmark(client: Any, username: str, password: str) -> dict[str, str]:
    """Exercise real authentication, including session epoch and password changes."""
    response = client.post('/auth/login', json={'username': username, 'password': password})
    if response.status_code != 200:
        raise RuntimeError(f'Benchmark login failed (HTTP {response.status_code}); no load was sent.')
    headers = {'Authorization': 'Bearer ' + response.json()['token']}
    # Reject accounts that must change their password before business requests.
    if client.get('/knowledge', headers=headers).status_code != 200:
        raise RuntimeError('Benchmark account cannot read knowledge; no load was sent.')
    return headers


def run_benchmark(
    endpoint: str,
    method: str = 'GET',
    payload: dict | None = None,
    total_requests: int = 150,
    concurrency: int = 10,
    headers: dict[str, str] | None = None,
    *,
    client: Any,
) -> dict[str, Any]:
    if total_requests < 1 or concurrency < 1:
        raise ValueError('requests and concurrency must be positive')

    def request() -> tuple[str, float]:
        started = time.perf_counter()
        try:
            response = client.request(method, endpoint, json=payload, headers=headers)
            status = str(response.status_code)
        except httpx.RequestError:
            status = 'transport_error'
        return status, (time.perf_counter() - started) * 1000

    # Fail closed before measuring an endpoint that is inaccessible or broken.
    preflight_status, _ = request()
    if not preflight_status.startswith('2'):
        raise RuntimeError(f'{endpoint}: preflight failed ({preflight_status}); result not measured.')

    latencies: list[float] = []
    successful_latencies: list[float] = []
    statuses: Counter[str] = Counter()
    started = time.perf_counter()
    with ThreadPoolExecutor(max_workers=concurrency) as executor:
        futures = [executor.submit(request) for _ in range(total_requests)]
        for future in as_completed(futures):
            status, latency = future.result()
            statuses[status] += 1
            latencies.append(latency)
            if status.startswith('2'):
                successful_latencies.append(latency)
    elapsed = time.perf_counter() - started
    ordered = sorted(latencies)
    successful_latencies.sort()
    success = len(successful_latencies)
    return {
        'total_requests': total_requests, 'concurrency': concurrency,
        'preflight_requests': 1, 'total_time_sec': round(elapsed, 6),
        'success': success, 'failures': total_requests - success,
        'error_rate': (total_requests - success) / total_requests,
        'status_counts': dict(sorted(statuses.items())),
        'attempt_rps': round(total_requests / elapsed, 2),
        'success_rps': round(success / elapsed, 2),
        'mean_ms': round(statistics.mean(latencies), 2),
        'p50_ms': round(statistics.median(latencies), 2),
        'p95_ms': round(ordered[math.ceil(0.95 * len(ordered)) - 1], 2),
        'success_p95_ms': round(successful_latencies[math.ceil(0.95 * success) - 1], 2) if success else None,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--base-url', default='http://127.0.0.1:8000')
    parser.add_argument('--in-process', action='store_true', help='Explicit local TestClient diagnostic only')
    parser.add_argument('--username', default='user', help='Dedicated benchmark account')
    parser.add_argument('--requests', type=int, default=150)
    parser.add_argument('--concurrency', type=int, default=10)
    parser.add_argument('--output', type=Path, help='Save raw JSON results')
    args = parser.parse_args()
    if args.requests < 1 or args.concurrency < 1:
        parser.error('--requests and --concurrency must be positive')
    password = os.getenv('OPSMIND_BENCHMARK_PASSWORD')
    if not password:
        parser.error('Set OPSMIND_BENCHMARK_PASSWORD for a dedicated test account.')
    if args.in_process:
        # Importing the app initializes its store: never do this in remote HTTP mode.
        from fastapi.testclient import TestClient
        from app.main import app
        client = TestClient(app)
    else:
        client = httpx.Client(base_url=args.base_url, timeout=30.0,
                              limits=httpx.Limits(max_connections=args.concurrency))
    report: dict[str, Any] = {
        'started_at_utc': datetime.now(timezone.utc).isoformat(),
        'mode': 'in_process_diagnostic' if args.in_process else 'http',
        'base_url': None if args.in_process else args.base_url,
        'python': platform.python_version(), 'platform': platform.platform(),
        'latency_scope': 'all measured responses; preflight and login excluded',
        'results': [],
    }
    failed = False
    with client:
        try:
            headers = login_benchmark(client, args.username, password)
        except (RuntimeError, httpx.RequestError) as exc:
            print(str(exc))
            return 1
        print(f"Mode: {report['mode']}. RAG calls create chat records; use disposable test data.")
        print('| Endpoint | Success / Total | Error rate | Success RPS | p50 all (ms) | p95 all (ms) |')
        print('|---|---:|---:|---:|---:|---:|')
        for endpoint, method, payload in [
            ('/health', 'GET', None), ('/config', 'GET', None),
            ('/knowledge', 'GET', None),
            ('/rag/ask', 'POST', {'question': 'Không kết nối được VPN FortiClient'}),
        ]:
            try:
                result = run_benchmark(endpoint, method, payload, args.requests, args.concurrency,
                                       headers, client=client)
                failed |= bool(result['failures'])
                print(f"| {endpoint} | {result['success']}/{result['total_requests']} | "
                      f"{result['error_rate']:.1%} | {result['success_rps']} | "
                      f"{result['p50_ms']} | {result['p95_ms']} |")
                report['results'].append({'endpoint': endpoint, **result})
            except RuntimeError as exc:
                failed = True
                report['results'].append({'endpoint': endpoint, 'error': str(exc)})
                print(str(exc))
    report['all_requests_succeeded'] = not failed
    print('No NFR/deployment claim is inferred automatically; record server configuration separately.')
    if args.output:
        args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    return int(failed)


if __name__ == '__main__':
    raise SystemExit(main())
