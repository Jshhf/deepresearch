"""Claim-level hallucination, semantic citation accuracy and completeness judge.

Uses Qwen as the LLM judge. Each report is split into claims; every claim is
classified as supported / contradicted / unsupported against the cited
sources, and every citation marker is checked for real support.

Usage:
    python app/eval/judge_metrics.py --results-dir output/eval_results \
        --out output/eval_judge.json
    python app/eval/judge_metrics.py --results-dir output/eval_results \
        --baseline-dir output/eval_results_old --out output/eval_judge.json

The baseline form prints before/after values for the same metric set.
"""

import argparse
import csv
import json
import os
import re
import statistics
import sys
from pathlib import Path

APP_ROOT = Path(__file__).resolve().parents[2] / "app"
sys.path.insert(0, str(APP_ROOT))


JUDGE_PROMPT = """你是研报质量评审员。请核对研报中的事实性声明及其引用。

输出 JSON（不要输出其他内容）：
{{
  "claims": [
    {{
      "text": "声明原文",
      "citations": ["WEB1_1-2"],
      "verdict": "supported|contradicted|unsupported"
    }}
  ],
  "citation_checks": [
    {{"citation": "WEB1_1-2", "verified": true}}
  ],
  "completeness_score": 0,
  "reason": "简要理由"
}}

判定规则：
1. supported：引用来源中存在内容支持该声明。
2. contradicted：来源内容与该声明矛盾。
3. unsupported：无来源、来源不相关或来源无法支持该声明。
4. citation_checks.verified：该引用对应的来源确实包含支持该句子的内容。
5. completeness_score：报告是否完整回答核心问题和子问题，0-100 分。

核心问题：
{query}

子问题：
{sub_questions}

引用来源列表：
{sources}

研报正文：
{report}
"""


def load_records(results_dir: Path) -> list[dict]:
    records = []
    for path in sorted(results_dir.glob("*.json")):
        if path.name.startswith("_"):
            continue
        try:
            record = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            continue
        if "error" in record or not str(record.get("final") or "").strip():
            continue
        records.append(record)
    return records


def extract_json(text: str) -> dict:
    cleaned = str(text).strip()
    if cleaned.startswith("```"):
        cleaned = re.sub(r"^```(?:json)?", "", cleaned).strip()
        cleaned = re.sub(r"```$", "", cleaned).strip()
    start = cleaned.find("{")
    end = cleaned.rfind("}")
    if start != -1 and end != -1 and end > start:
        cleaned = cleaned[start : end + 1]
    try:
        value = json.loads(cleaned)
        return value if isinstance(value, dict) else {}
    except json.JSONDecodeError:
        return {}


def format_sources(record: dict) -> str:
    lines = []
    evidence_lookup = {
        str(item.get("source_id", "")).strip(): item
        for item in (record.get("evidence_pool") or [])
        if item.get("source_id")
    }
    for item in (record.get("source_index") or [])[:40]:
        sid = str(item.get("source_id", "")).strip()
        evidence = evidence_lookup.get(sid) or {}
        snippet = str(evidence.get("snippet") or "").strip()
        published = str(evidence.get("published_at") or item.get("published_at") or "").strip()
        meta = f" | 发布时间: {published}" if published else ""
        lines.append(
            f"- [{sid}] ({item.get('source_type')}) "
            f"{item.get('label')} | {item.get('locator')}{meta}"
        )
        if snippet:
            lines.append(f"  原文片段: {snippet[:500]}")
    if not lines:
        lines.append("- 无来源")
    return "\n".join(lines)


def judge_report(judge, record: dict) -> dict:
    prompt = JUDGE_PROMPT.format(
        query=record.get("query", ""),
        sub_questions=json.dumps(record.get("sub_questions") or [], ensure_ascii=False),
        sources=format_sources(record),
        report=str(record.get("final") or "")[:12000],
    )
    from langchain_core.messages import HumanMessage

    response = judge.invoke([HumanMessage(content=prompt)])
    return extract_json(response.content)


def aggregate(records: list[dict], judge) -> dict:
    total_claims = 0
    hallucinated = 0
    total_citations = 0
    verified_citations = 0
    completeness = []
    per_case = []

    for record in records:
        verdict = judge_report(judge, record)
        claims = verdict.get("claims") or []
        checks = verdict.get("citation_checks") or []
        case_claims = len(claims)
        case_hallucinated = sum(
            1 for c in claims if str(c.get("verdict", "")).strip().lower() in {"contradicted", "unsupported"}
        )
        case_citations = len(checks)
        case_verified = sum(1 for c in checks if bool(c.get("verified")))
        score = verdict.get("completeness_score")
        total_claims += case_claims
        hallucinated += case_hallucinated
        total_citations += case_citations
        verified_citations += case_verified
        if isinstance(score, (int, float)):
            completeness.append(float(score))

        per_case.append(
            {
                "id": record.get("id"),
                "query": record.get("query", ""),
                "total_claims": case_claims,
                "hallucinated_claims": case_hallucinated,
                "hallucination_rate": (case_hallucinated / case_claims) if case_claims else None,
                "total_citations": case_citations,
                "verified_citations": case_verified,
                "citation_accuracy": (case_verified / case_citations) if case_citations else None,
                "completeness_score": score,
                "judge_reason": str(verdict.get("reason", "")),
            }
        )

    return {
        "total_cases": len(records),
        "total_claims": total_claims,
        "hallucinated_claims": hallucinated,
        "hallucination_rate": (hallucinated / total_claims) if total_claims else None,
        "total_citations": total_citations,
        "verified_citations": verified_citations,
        "citation_accuracy": (verified_citations / total_citations) if total_citations else None,
        "completeness_avg": statistics.fmean(completeness) if completeness else None,
        "per_case": per_case,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="LLM judge for hallucination and citation accuracy")
    parser.add_argument("--results-dir", required=True)
    parser.add_argument("--baseline-dir", default=None)
    parser.add_argument("--out", default="output/eval_judge.json")
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--model", default="qwen-plus")
    args = parser.parse_args()

    sys.stdout.reconfigure(encoding="utf-8")
    records = load_records(Path(args.results_dir))
    if args.limit:
        records = records[: args.limit]
    if not records:
        print("no records found under", args.results_dir)
        return 1

    from langchain_community.chat_models import ChatTongyi

    api_key = os.getenv("DASHSCOPE_API_KEY", "")
    if api_key:
        os.environ["DASHSCOPE_API_KEY"] = api_key
    judge = ChatTongyi(model=args.model, temperature=0.0)

    result = aggregate(records, judge)
    payload = {"current": result}
    if args.baseline_dir:
        baseline = load_records(Path(args.baseline_dir))
        if args.limit:
            baseline = baseline[: args.limit]
        payload["baseline"] = aggregate(baseline, judge)
        for metric in ("hallucination_rate", "citation_accuracy", "completeness_avg"):
            before = payload["baseline"].get(metric)
            after = payload["current"].get(metric)
            if before is not None and after is not None:
                payload[f"delta_{metric}"] = after - before

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    csv_path = out_path.with_suffix(".csv")
    with csv_path.open("w", encoding="utf-8-sig", newline="") as fh:
        writer = csv.DictWriter(
            fh,
            fieldnames=[
                "id", "query", "total_claims", "hallucinated_claims", "hallucination_rate",
                "total_citations", "verified_citations", "citation_accuracy",
                "completeness_score", "judge_reason",
            ],
        )
        writer.writeheader()
        writer.writerows(payload["current"]["per_case"])

    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
