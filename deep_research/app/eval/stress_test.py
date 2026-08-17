"""Simple HTTP stress test for the research API.

Uses stdlib only. Each request POSTs to /api/v1/research/run and the script
reports throughput and latency percentiles. Real requests consume DashScope
and Bocha quota, so start small.

Usage:
    python app/eval/stress_test.py --base-url http://localhost:8000 \
        --query "调研2026年AI Agent框架趋势" --total 10 --concurrency 2
"""

import argparse
import concurrent.futures
import json
import statistics
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path


def send_request(base_url: str, query: str, timeout: int, index: int) -> dict:
    payload = {
        "query": query,
        "user_id": "stress_user",
        "thread_id": f"stress_{index}",
        "tenant_id": "default_tenant",
    }
    data = json.dumps(payload).encode("utf-8")
    request = urllib.request.Request(
        base_url.rstrip("/") + "/api/v1/research/run",
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    started = time.perf_counter()
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            response.read()
        ok = True
        status = response.status
    except urllib.error.HTTPError as exc:
        ok = False
        status = exc.code
    except Exception:
        ok = False
        status = None
    elapsed = time.perf_counter() - started
    return {"ok": ok, "status": status, "latency_seconds": elapsed}


def percentile(values: list[float], q: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    idx = min(len(ordered) - 1, int(len(ordered) * q))
    return ordered[idx]


def main() -> int:
    parser = argparse.ArgumentParser(description="Concurrent HTTP stress test")
    parser.add_argument("--base-url", default="http://localhost:8000")
    parser.add_argument("--query", required=True)
    parser.add_argument("--total", type=int, default=10)
    parser.add_argument("--concurrency", type=int, default=1)
    parser.add_argument("--timeout", type=int, default=600)
    parser.add_argument("--out", default="output/eval_stress.json")
    args = parser.parse_args()

    sys.stdout.reconfigure(encoding="utf-8")
    started = time.perf_counter()
    results = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=args.concurrency) as executor:
        futures = [
            executor.submit(send_request, args.base_url, args.query, args.timeout, i)
            for i in range(1, args.total + 1)
        ]
        for future in concurrent.futures.as_completed(futures):
            results.append(future.result())
    wall_seconds = time.perf_counter() - started

    latencies = [r["latency_seconds"] for r in results]
    ok_count = sum(1 for r in results if r["ok"])
    summary = {
        "query": args.query,
        "total_requests": args.total,
        "concurrency": args.concurrency,
        "wall_seconds": round(wall_seconds, 3),
        "qps": round(args.total / wall_seconds, 3) if wall_seconds > 0 else None,
        "ok_count": ok_count,
        "error_count": args.total - ok_count,
        "error_rate": round((args.total - ok_count) / args.total, 4) if args.total else None,
        "latency_seconds": {
            "min": round(min(latencies), 3),
            "avg": round(statistics.fmean(latencies), 3),
            "p50": round(percentile(latencies, 0.50), 3),
            "p90": round(percentile(latencies, 0.90), 3),
            "p95": round(percentile(latencies, 0.95), 3),
            "max": round(max(latencies), 3),
        },
    }

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0 if ok_count == args.total else 1


if __name__ == "__main__":
    raise SystemExit(main())
