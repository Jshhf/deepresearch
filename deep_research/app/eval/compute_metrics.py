"""Compute measurable metrics from saved eval traces.

Usage:
    python app/eval/compute_metrics.py --results-dir output/eval_results

Outputs aggregate numbers to stdout and writes output/eval_metrics.json.
"""

import argparse
import json
import re
import statistics
import sys
from pathlib import Path

CITATION_RE = re.compile(r"\[((?:WEB|LOC)\d+_\d+-\d+)\]")
LOW_QUALITY_THRESHOLD = 0.6


def extract_citations(text: str) -> list[str]:
    return list(dict.fromkeys(CITATION_RE.findall(text or "")))


def score_evidence(record: dict) -> float:
    """Mirror nodes._score_evidence so metrics can be computed offline."""
    source_type = record.get("source_type")
    if source_type == "local":
        return 0.92
    domain = str(record.get("domain", "")).lower()
    if domain.endswith((".gov.cn", ".gov", ".edu", ".edu.cn")) or "gov" in domain or "official" in domain:
        return 0.88
    if any(word in domain for word in ["news", "finance", "reuters", "bloomberg", "people", "xinhuanet"]):
        return 0.72
    if domain:
        return 0.58
    return 0.45


def low_quality_ratio(items: list[dict], scored: bool) -> float | None:
    if not items:
        return None
    low = 0
    for item in items:
        score = item.get("reliability_score") if scored else score_evidence(item)
        if isinstance(score, (int, float)) and score < LOW_QUALITY_THRESHOLD:
            low += 1
    return low / len(items)


def term_set(text: str) -> set[str]:
    terms = re.findall(r"[\u4e00-\u9fff]{2,}|[A-Za-z0-9_-]{3,}", text.lower())
    stopwords = {
        "什么", "如何", "以及", "一个", "关于", "这个", "那个", "进行", "基于",
        "附带", "来源", "清单", "帮助", "调研", "研究", "分析", "报告",
    }
    return {t for t in terms if t not in stopwords}


def completeness_proxy(record: dict) -> float | None:
    expected = record.get("expected_sub_questions") or []
    report = str(record.get("final") or "")
    if not expected or not report:
        return None
    matched = 0
    for question in expected:
        terms = term_set(str(question))
        if terms and any(t in report.lower() for t in terms):
            matched += 1
    return matched / len(expected)


def plan_coverage(record: dict) -> float | None:
    traces = (record.get("web_search_trace") or []) + (record.get("local_rag_trace") or [])
    if not traces:
        return None
    covered = sum(1 for t in traces if t.get("kept_count", 0) > 0)
    return covered / len(traces)


def pct(values: list[float], q: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    idx = min(len(ordered) - 1, int(len(ordered) * q))
    return ordered[idx]


def main() -> int:
    parser = argparse.ArgumentParser(description="Compute metrics from eval traces")
    parser.add_argument("--results-dir", default="output/eval_results")
    parser.add_argument("--out", default="output/eval_metrics.json")
    args = parser.parse_args()

    sys.stdout.reconfigure(encoding="utf-8")
    results_dir = Path(args.results_dir)
    records = []
    for path in sorted(results_dir.glob("*.json")):
        if path.name.startswith("_"):
            continue
        try:
            record = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            continue
        if "error" in record:
            continue
        records.append(record)

    if not records:
        print("no valid results found under", results_dir)
        return 1

    metrics: dict = {
        "total_cases": len(records),
        "direct_route_share": None,
        "intent_route_accuracy": None,
        "citation_stats": {},
        "low_quality_source_ratio": {"before_judge": None, "after_judge": None},
        "retrieval_stats": {},
        "plan_coverage_avg": None,
        "completeness_proxy_avg": None,
        "iteration_stats": {},
        "latency_seconds": {},
        "report_chars_avg": None,
    }

    routes = [str(r.get("route", "")).strip().lower() for r in records]
    metrics["direct_route_share"] = routes.count("direct") / len(routes)

    labeled = [r for r in records if r.get("expected_route")]
    if labeled:
        correct = sum(1 for r in labeled if str(r.get("route", "")).lower() == str(r.get("expected_route", "")).lower())
        metrics["intent_route_accuracy"] = correct / len(labeled)

    total_citations = 0
    valid_citations = 0
    invalid_citations = 0
    pre_items = []
    post_items = []
    coverage = []
    completeness = []
    latencies = []
    report_lengths = []
    iterations = []
    needs_more = 0
    missing_gaps_total = 0
    web_stats = {"query_count": 0, "raw_count": 0, "kept_count": 0, "dropped_count": 0}
    local_stats = {"query_count": 0, "raw_count": 0, "kept_count": 0, "dropped_count": 0}

    for record in records:
        report = str(record.get("final") or "")
        citations = extract_citations(report)
        source_ids = {
            str(item.get("source_id", "")).strip()
            for item in (record.get("source_index") or []) + (record.get("evidence_pool") or [])
            if item.get("source_id")
        }
        valid = [c for c in citations if c in source_ids]
        total_citations += len(citations)
        valid_citations += len(valid)
        invalid_citations += len(citations) - len(valid)

        pre_items.extend(record.get("web_evidence") or [])
        pre_items.extend(record.get("local_evidence") or [])
        post_items.extend(record.get("evidence_pool") or [])

        cov = plan_coverage(record)
        if cov is not None:
            coverage.append(cov)
        comp = completeness_proxy(record)
        if comp is not None:
            completeness.append(comp)

        latencies.append(float(record.get("latency_seconds") or 0.0))
        report_lengths.append(len(report))
        iterations.append(int(record.get("iteration") or 0))
        if record.get("needs_more_research"):
            needs_more += 1
        missing_gaps_total += len(record.get("missing_gaps") or [])

        for channel, stats in (("web", web_stats), ("local", local_stats)):
            src = record.get(f"{channel}_retrieval_stats") or {}
            for key in ("query_count", "raw_count", "kept_count", "dropped_count"):
                stats[key] += int(src.get(key, 0) or 0)

    metrics["citation_stats"] = {
        "total": total_citations,
        "valid": valid_citations,
        "invalid": invalid_citations,
        "valid_rate": (valid_citations / total_citations) if total_citations else None,
        "invalid_rate": (invalid_citations / total_citations) if total_citations else None,
    }
    metrics["low_quality_source_ratio"] = {
        "before_judge": low_quality_ratio(pre_items, scored=False),
        "after_judge": low_quality_ratio(post_items, scored=True),
    }
    metrics["retrieval_stats"] = {
        "web": web_stats,
        "local": local_stats,
        "web_keep_rate": (web_stats["kept_count"] / web_stats["raw_count"]) if web_stats["raw_count"] else None,
        "local_keep_rate": (local_stats["kept_count"] / local_stats["raw_count"]) if local_stats["raw_count"] else None,
    }
    metrics["plan_coverage_avg"] = statistics.fmean(coverage) if coverage else None
    metrics["completeness_proxy_avg"] = statistics.fmean(completeness) if completeness else None
    metrics["iteration_stats"] = {
        "avg_iterations": statistics.fmean(iterations) if iterations else None,
        "needs_more_research_rate": needs_more / len(records),
        "avg_missing_gaps": missing_gaps_total / len(records),
        "iteration_distribution": {str(i): iterations.count(i) for i in sorted(set(iterations))},
    }
    metrics["latency_seconds"] = {
        "avg": statistics.fmean(latencies) if latencies else None,
        "p50": pct(latencies, 0.50),
        "p90": pct(latencies, 0.90),
        "p95": pct(latencies, 0.95),
        "max": max(latencies) if latencies else None,
    }
    metrics["report_chars_avg"] = statistics.fmean(report_lengths) if report_lengths else None

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(metrics, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(metrics, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
