# DeepResearch 测评说明

这个目录用于把简历里的量化指标真正跑出来。仓库源码里没有现成的测评
脚本，下面这套工具负责三件事：

1. `run_eval.py`：用带标签的查询集跑一遍完整工作流，把每次运行的
   `route`、证据池、来源索引、检索统计、迭代信息、报告正文和耗时保存成 JSON。
2. `compute_metrics.py`：从保存的结果里自动统计可脚本化的指标。
3. `judge_reports.py`：生成人工评审表，或调用 Qwen 做 LLM 评审，
   用来评估幻觉率与研究完备性。
4. `run_http_eval.py`：对部署后的 FastAPI 服务做黑盒评测，测真实 API 延迟。
5. `stress_test.py`：HTTP 并发压测，输出 QPS、P50/P90/P95、错误率。

## 指标口径

| 简历指标 | 计算方法 | 数据来源 |
| --- | --- | --- |
| 意图路由准确率 | 路由正确数 / 带标签总数 | 每条结果的 `route` vs 标签 `expected_route` |
| 引用准确率（ID 级） | 合法引用数 / 正文引用总数 | 正则提取正文 `[WEBx_y-z]` / `[LOCx_y-z]`，与 `source_index` 比对 |
| 幻觉引用率（自动） | 非法引用数 / 引用总数 | 同上；注意 `write_node` 已自动移除非法引用，所以这个值会很低 |
| 声明级幻觉率 | 无来源支持的声明数 / 声明总数 | 人工或 LLM 评审，见 `judge_reports.py` |
| 低质量信源占比 | `reliability_score < 0.6` 的证据占比 | Judge 前用 `web_evidence` + `local_evidence` 套用启发式评分；Judge 后用 `evidence_pool.reliability_score` |
| 检索覆盖率 | 有保留证据的检索步骤 / 总检索步骤 | `web_search_trace` / `local_rag_trace` 的 `kept_count` |
| 研究完备性代理 | 预期子问题关键词在报告中的覆盖比例 | 标签 `expected_sub_questions` 与报告正文比对；真实完备性请用人工/LLM 打分 |
| 响应时间 | 每次 `app.invoke` 的墙钟耗时 | `latency_seconds` |
| 迭代补搜 | 平均迭代轮次、触发补搜比例、平均缺口数 | `iteration` / `needs_more_research` / `missing_gaps` |

## 跑之前的环境

1. 安装依赖（建议 Python 3.11，项目根目录执行）：

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

2. 启动基础设施（Postgres、Redis、Milvus）并入库，参考项目根目录
   `README-部署说明.md`。至少保证 Milvus 可用，否则本地检索为空，
   “双源检索”相关指标不完整。

3. `.env` 已配置 `DASHSCOPE_API_KEY` 和 `BOCHA_API_KEY` 时，配置模块会
   自动读取；没有配置时网络检索会返回空。

## 使用步骤

```powershell
# 1) 跑查询集（先跑前 5 条试一下）
python app/eval/run_eval.py --queries app/eval/sample_queries.jsonl --out output/eval_results --limit 5

# 2) 自动指标
python app/eval/compute_metrics.py --results-dir output/eval_results

# 3) 生成人工评审表（打开 CSV 逐条填）
python app/eval/judge_reports.py --results-dir output/eval_results --out output/eval_review.csv

# 3b) 用 Qwen 先评一遍，人工再复核
python app/eval/judge_reports.py --results-dir output/eval_results --out output/eval_review.csv --llm-judge
```

## 快速启动工具

项目根目录的 `eval_run.ps1` 是统一启动器：

```powershell
cd D:\deepresearch\deep_research

# 交互菜单
.\eval_run.ps1

# 一键跑内部评测（前 5 条）
.\eval_run.ps1 -Action internal -Limit 5

# 一键算指标
.\eval_run.ps1 -Action metrics

# 一键 HTTP 黑盒评测
.\eval_run.ps1 -Action http -Limit 5

# 一键压测
.\eval_run.ps1 -Action stress -Total 10 -Concurrency 2
```

## 黑盒评测（部署后的 HTTP 服务）

`run_http_eval.py` 直接 POST `/api/v1/research/run`，不关心内部实现，适合验证
部署后的版本并记录真实 API 延迟：

```powershell
python app/eval/run_http_eval.py --queries app/eval/sample_queries.jsonl `
  --base-url http://localhost:8000 --out output/eval_http --limit 5
```

## 压力测试

`stress_test.py` 用线程池并发发送研究请求，统计吞吐与延迟分位数。注意压测会
真实消耗 DashScope / Bocha 调用量，先小规模试跑：

```powershell
python app/eval/stress_test.py --base-url http://localhost:8000 `
  --query "调研2026年AI Agent开发框架发展趋势" --total 10 --concurrency 2
```

## 外部评测工具

- RAGAS：RAG 指标（faithfulness、answer relevancy、context precision/recall）
- DeepEval：断言式 LLM 评测与回归测试
- promptfoo：提示词/模型切换回归测试
- LangSmith / Langfuse：链路追踪、在线评测与人工标注
- k6 / Locust / JMeter：更专业的 HTTP 压测（可对接上面的 `/api/v1/research/run`）

## 把测评集扩到 200 条

`sample_queries.jsonl` 只是格式模板。正式测评建议：

- 混合两类标签：简单问答/闲聊（期望 `direct`）和调研/分析类（期望 `multiagent`）。
- 研究类问题写清楚 `expected_sub_questions`，用于完备性评审。
- 每条最好对应你们真实业务场景（行业研究、政策、竞品、技术选型）。
- 采样后人工盲测 + LLM 初筛，最终数值以人工复核为准。

## 重要说明

简历和学习文档里的“25% 降到 6%”“引用准确率 94%”“完备性 62% 升到 89%”
等数字来自原始项目文档，不是这个仓库里已经算好的结果。把它们写进简历
前，建议用上面的流程在自己的测评集上跑一遍；如果测出来不同，就按真实
结果改简历，面试时也能说清楚口径（人工盲测 + 脚本校验，约 200 条复杂
查询）。

## 性能口径（可选）

`run_eval.py` 记录的是整条工作流的墙钟耗时。如果面试要聊“双源检索平均
响应时间 < 8s”和“检索耗时降低 35%”，可以单独测两个检索调用：

```python
from mult_agents.tools import bocha_web_search_records, search_knowledge_base_records
import time

t0 = time.perf_counter()
web = bocha_web_search_records("你的查询", count=4)
t1 = time.perf_counter()
t2 = time.perf_counter()
local = search_knowledge_base_records("你的查询", limit=4)
t3 = time.perf_counter()

web_elapsed = t1 - t0
local_elapsed = t3 - t2
parallel = max(web_elapsed, local_elapsed)   # 并行后的墙钟时间
serial = web_elapsed + local_elapsed         # 串行估计值
speedup = 1 - parallel / serial              # 并行带来的耗时下降比例
```

“证据覆盖率提升 40%”这类指标无法从系统日志直接算出来，需要先标注一份
“每个查询的正确答案/应命中的资料”集合，再统计双源检索是否命中。没有
标注集时，可以用 `plan_coverage_avg`（计划检索步骤中留下证据的比例）
作为覆盖率代理指标。
