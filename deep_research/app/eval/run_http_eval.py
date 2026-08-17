"""Run labeled queries against the deployed HTTP API and save per-case traces.

Unlike run_eval.py, this script is a black-box test against the running
backend, so it measures real API latency and validates the deployed service.

Usage:
    python app/eval/run_http_eval.py --queries app/eval/sample_queries.jsonl \
        --base-url http://localhost:8000 --out output/eval_http --limit 5
"""

import argparse
import concurrent.futures
import json
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path


def load_cases(path: Path) -> list[dict]:
    cases = []
    with path.open("r", encoding="utf-8") as fh:
        for line_no, line in enumerate(fh, 1):
            line = line.strip()
            if not line:
                continue
            case = json.loads(line)
            if not isinstance(case, dict) or not str(case.get("query", "")).strip():
                raise ValueError(f"line {line_no} is not a valid case")
            cases.append(case)
    return cases


def call_api(
    base_url: str,
    query: str,
    user_id: str,
    thread_id: str,
    tenant_id: str,
    max_iterations: int | None,
    timeout: int,
) -> dict:
    payload = {
        "query": query,
        "user_id": user_id,
        "thread_id": thread_id,
        "tenant_id": tenant_id,
        "max_iterations": max_iterations,
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
            body = json.loads(response.read().decode("utf-8"))
        elapsed = time.perf_counter() - started
        return {
            "ok": True,
            "status": response.status,
            "latency_seconds": round(elapsed, 3),
            "final": str(body.get("final") or ""),
        }
    except urllib.error.HTTPError as exc:
        elapsed = time.perf_counter() - started
        try:
            detail = exc.read().decode("utf-8", errors="replace")
        except Exception:
            detail = ""
        return {
            "ok": False,
            "status": exc.code,
            "latency_seconds": round(elapsed, 3),
            "error": detail[:500] or repr(exc),
            "final": "",
        }
    except Exception as exc:
        elapsed = time.perf_counter() - started
        return {
            "ok": False,
            "status": None,
            "latency_seconds": round(elapsed, 3),
            "error": repr(exc),
            "final": "",
        }


def run_one(base_url: str, case: dict, index: int, timeout: int) -> tuple[str, dict]:
    query = str(case["query"]).strip()
    result = call_api(
        base_url=base_url,
        query=query,
        user_id=str(case.get("user_id") or "eval_user"),
        thread_id=str(case.get("thread_id") or f"eval_http_{index}"),
        tenant_id=str(case.get("tenant_id") or "default_tenant"),
        max_iterations=case.get("max_iterations"),
        timeout=timeout,
    )
    result["id"] = str(case.get("id") or f"case_{index}")
    result["query"] = query
    result["expected_route"] = case.get("expected_route")
    result["expected_sub_questions"] = case.get("expected_sub_questions", [])
    return result["id"], result


def main() -> int:
    parser = argparse.ArgumentParser(description="Black-box eval against the deployed HTTP API")
    parser.add_argument("--queries", required=True, help="JSONL file with one case per line")
    parser.add_argument("--base-url", default="http://localhost:8000")
    parser.add_argument("--out", default="output/eval_http")
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--concurrency", type=int, default=2)
    parser.add_argument("--timeout", type=int, default=600)
    args = parser.parse_args()

    sys.stdout.reconfigure(encoding="utf-8")
    cases = load_cases(Path(args.queries))
    if args.limit:
        cases = cases[: args.limit]

    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)
    summary = {"total": len(cases), "ok": 0, "failed": 0, "failed_ids": []}

    with concurrent.futures.ThreadPoolExecutor(max_workers=args.concurrency) as executor:
        futures = {
            executor.submit(run_one, args.base_url, case, index, args.timeout): (index, case)
            for index, case in enumerate(cases, 1)
        }
        for future in concurrent.futures.as_completed(futures):
            index, _ = futures[future]
            case_id, result = future.result()
            (out_dir / f"{case_id}.json").write_text(
                json.dumps(result, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
            if result["ok"]:
                summary["ok"] += 1
            else:
                summary["failed"] += 1
                summary["failed_ids"].append(case_id)
            print(
                f"[{index}/{len(cases)}] {case_id} ok={result['ok']} "
                f"latency={result['latency_seconds']}s",
                flush=True,
            )

    (out_dir / "_summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0 if summary["failed"] == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
