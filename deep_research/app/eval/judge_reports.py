"""Generate a review sheet for hallucination and completeness judgments.

Usage:
    python app/eval/judge_reports.py --results-dir output/eval_results
    python app/eval/judge_reports.py --results-dir output/eval_results --llm-judge

The CSV has one row per report. Run without --llm-judge to create a blank sheet
for manual review; with --llm-judge, Qwen fills the first verdict columns.
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


JUDGE_PROMPT = """你是研报质量评审员。请基于引用来源列表，逐条核对研报正文中的事实性陈述。

判断规则：
1. total_claims：正文中可独立核验的事实性声明总数。
2. hallucinated_claims：没有来源支持、与所引用来源矛盾、或明显超出来源内容的声明数。
3. completeness_score：研报是否完整回答了核心问题与子问题，0-100 分。

只输出 JSON，不要输出其他内容：
{{"total_claims": N, "hallucinated_claims": N, "completeness_score": N, "reason": "简要理由"}}

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
    cleaned = text.strip()
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
    for item in (record.get("source_index") or [])[:40]:
        lines.append(
            f"- [{item.get('source_id')}] ({item.get('source_type')}) "
            f"{item.get('label')} | {item.get('locator')}"
        )
    return "\n".join(lines) or "- 无来源"


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate human/LLM review sheet")
    parser.add_argument("--results-dir", default="output/eval_results")
    parser.add_argument("--out", default="output/eval_review.csv")
    parser.add_argument("--llm-judge", action="store_true", help="fill verdicts with Qwen")
    parser.add_argument("--model", default="qwen-plus")
    parser.add_argument("--api-key", default=None)
    parser.add_argument("--limit", type=int, default=None)
    args = parser.parse_args()

    sys.stdout.reconfigure(encoding="utf-8")
    records = load_records(Path(args.results_dir))
    if args.limit:
        records = records[: args.limit]
    if not records:
        print("no reports found under", args.results_dir)
        return 1

    judge = None
    if args.llm_judge:
        from langchain_community.chat_models import ChatTongyi
        from langchain_core.messages import HumanMessage

        api_key = args.api_key or os.getenv("DASHSCOPE_API_KEY", "")
        if api_key:
            os.environ["DASHSCOPE_API_KEY"] = api_key
        judge = ChatTongyi(model=args.model, temperature=0.0)

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = [
        "id", "query", "report_chars", "source_count",
        "hallucination_rate", "hallucinated_claims", "total_claims",
        "completeness_score", "judge_reason",
        "human_hallucination_verdict", "human_completeness_score", "human_notes",
    ]
    rows = []
    rates = []
    completeness = []
    for index, record in enumerate(records, 1):
        report = str(record.get("final") or "")
        row = {
            "id": record.get("id") or f"case_{index}",
            "query": record.get("query", ""),
            "report_chars": len(report),
            "source_count": len(record.get("source_index") or []),
            "hallucination_rate": "",
            "hallucinated_claims": "",
            "total_claims": "",
            "completeness_score": "",
            "judge_reason": "",
            "human_hallucination_verdict": "",
            "human_completeness_score": "",
            "human_notes": "",
        }
        if judge is not None:
            prompt = JUDGE_PROMPT.format(
                query=record.get("query", ""),
                sub_questions=json.dumps(record.get("sub_questions") or [], ensure_ascii=False),
                sources=format_sources(record),
                report=report[:12000],
            )
            response = judge.invoke([HumanMessage(content=prompt)])
            verdict = extract_json(str(response.content))
            total = verdict.get("total_claims")
            hallucinated = verdict.get("hallucinated_claims")
            if isinstance(total, int) and isinstance(hallucinated, int) and total > 0:
                rate = hallucinated / total
                rates.append(rate)
                row["hallucination_rate"] = f"{rate:.1%}"
                row["hallucinated_claims"] = str(hallucinated)
                row["total_claims"] = str(total)
            score = verdict.get("completeness_score")
            if isinstance(score, (int, float)):
                completeness.append(float(score))
                row["completeness_score"] = str(score)
            row["judge_reason"] = str(verdict.get("reason", ""))
            print(f"[{index}/{len(records)}] judged {row['id']}", flush=True)
        rows.append(row)

    with out_path.open("w", encoding="utf-8-sig", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    print(f"review sheet written to {out_path}")
    if rates:
        print(f"LLM avg hallucination rate: {statistics.fmean(rates):.1%}")
    if completeness:
        print(f"LLM avg completeness score: {statistics.fmean(completeness):.1f}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
