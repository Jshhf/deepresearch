"""Run a labeled query set through the DeepResearch workflow and save traces.

Usage:
    python app/eval/run_eval.py --queries app/eval/sample_queries.jsonl
        --out output/eval_results --limit 10

Each case is written as a JSON file with the full final state (route, evidence
pool, citation index, retrieval stats, report text) plus wall-clock latency.
"""

import argparse
import json
import sys
import time
from pathlib import Path

APP_ROOT = Path(__file__).resolve().parents[2] / "app"
sys.path.insert(0, str(APP_ROOT))

from mult_agents.config import AppConfig
from mult_agents.graph import build_app
from mult_agents.main import build_agents, build_checkpointer, build_memory_manager
from mult_agents.state import create_initial_state


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


def main() -> int:
    parser = argparse.ArgumentParser(description="Run labeled queries and save eval traces")
    parser.add_argument("--queries", required=True, help="JSONL file with one case per line")
    parser.add_argument("--out", default="output/eval_results", help="output directory for per-case JSON")
    parser.add_argument("--config", default=None, help="path to config.json (default: project config.json)")
    parser.add_argument("--max-iterations", type=int, default=None)
    parser.add_argument("--enable-memory", choices=["true", "false"], default=None)
    parser.add_argument("--limit", type=int, default=None, help="only run the first N cases")
    args = parser.parse_args()

    sys.stdout.reconfigure(encoding="utf-8")
    cases = load_cases(Path(args.queries))
    if args.limit:
        cases = cases[: args.limit]

    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)

    config = AppConfig.from_file(args.config)
    if args.enable_memory is not None:
        config = config.with_overrides(enable_memory=args.enable_memory == "true")
    if args.max_iterations is not None:
        config = config.with_overrides(max_iterations=args.max_iterations)

    memory_manager = build_memory_manager(config) if config.enable_memory else None
    agents = build_agents(config.model, config.api_key, config)
    checkpointer = build_checkpointer(config)
    app = build_app(agents, checkpointer)

    summary = {"total": len(cases), "ok": 0, "failed": 0, "failed_ids": []}
    for idx, case in enumerate(cases, 1):
        case_id = str(case.get("id") or f"case_{idx}")
        thread_id = f"eval_{case_id}"
        user_id = str(case.get("user_id") or config.user_id)
        tenant_id = str(case.get("tenant_id") or config.tenant_id)
        query = str(case["query"]).strip()
        print(f"[{idx}/{len(cases)}] {case_id}: {query}", flush=True)

        memory_context = ""
        if memory_manager:
            try:
                memory_context = memory_manager.build_personalized_prompt_context(
                    user_id=user_id,
                    thread_id=thread_id,
                    query=query,
                    tenant_id=tenant_id,
                    max_memories=config.memory_top_k,
                )
            except Exception as exc:
                print(f"  memory context failed: {exc}", flush=True)

        state = create_initial_state(
            query=query,
            max_iterations=config.max_iterations,
            user_id=user_id,
            tenant_id=tenant_id,
            memory_context=memory_context,
        )
        started = time.perf_counter()
        try:
            result = app.invoke(state, {"configurable": {"thread_id": thread_id}})
            elapsed = time.perf_counter() - started
        except Exception as exc:
            elapsed = time.perf_counter() - started
            record = {
                "id": case_id,
                "query": query,
                "error": repr(exc),
                "latency_seconds": round(elapsed, 3),
            }
            (out_dir / f"{case_id}.json").write_text(
                json.dumps(record, ensure_ascii=False, indent=2), encoding="utf-8"
            )
            summary["failed"] += 1
            summary["failed_ids"].append(case_id)
            print(f"  FAILED: {exc}", flush=True)
            continue

        record = {
            "id": case_id,
            "query": query,
            "expected_route": case.get("expected_route"),
            "expected_sub_questions": case.get("expected_sub_questions", []),
            "latency_seconds": round(elapsed, 3),
            "route": result.get("intent"),
            "iteration": result.get("iteration", 0),
            "needs_more_research": bool(result.get("needs_more_research", False)),
            "missing_gaps": result.get("missing_gaps", []),
            "sub_questions": result.get("sub_questions", []),
            "research_questions": result.get("research_questions", []),
            "search_plan": result.get("search_plan", []),
            "supplementary_queries": result.get("supplementary_queries", []),
            "web_retrieval_stats": result.get("web_retrieval_stats", {}),
            "local_retrieval_stats": result.get("local_retrieval_stats", {}),
            "web_search_trace": result.get("web_search_trace", []),
            "local_rag_trace": result.get("local_rag_trace", []),
            "web_evidence": result.get("web_evidence", []),
            "local_evidence": result.get("local_evidence", []),
            "evidence_pool": result.get("evidence_pool", []),
            "audit_flags": result.get("audit_flags", []),
            "findings": result.get("findings", []),
            "claim_map": result.get("claim_map", []),
            "source_index": result.get("source_index", []),
            "final": result.get("final", ""),
        }
        (out_dir / f"{case_id}.json").write_text(
            json.dumps(record, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        summary["ok"] += 1
        print(
            f"  OK route={record['route']} latency={record['latency_seconds']}s "
            f"iteration={record['iteration']}",
            flush=True,
        )

    (out_dir / "_summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0 if summary["failed"] == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
