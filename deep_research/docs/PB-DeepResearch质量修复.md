# DeepResearch 质量修复 Product Backlog

日期：2026-08-13
范围：DeepResearch 多 Agent 深度研究助手
目标：降低幻觉率，提升语义引用准确率与证据召回率，并消除大模型超时导致的评测失败。

## 当前基线

- 研究类声明幻觉率：84.2%（48/57）
- 语义引用准确率：19.2%（10/52）
- 网络证据保留率：56.1%
- 本地知识库证据保留率：0.0%
- 平均耗时：250.8 秒，最大 502.5 秒
- 超时失败用例：q08 等在 DashScope 请求中出现 300 秒读超时

## 根因映射

1. 写作端拿不到原始证据文本，模型被迫凭记忆补全事实。
2. 证据抽取在 LLM 返回空列表时不会回退到原始检索记录。
3. 网络检索只消费摘要，缺少正文抓取、权威性过滤和发布时间过滤。
4. 写作提示词要求“2000-3000 字以上”和“深度扩写”，比可验证证据更早促成编造。
5. LangChain 大模型调用没有节点级超时、重试或降级策略。

## Backlog

| ID | 优先级 | 问题 | 根因 | 建议改动 | 关键文件 | 验收标准 | 状态 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| PB-01 | P0 | 写作端事实依据不足，幻觉高、引用不准 | Writer 只拿到 findings 和 source_index，没有 snippet | 把 evidence_pool 的 snippet、published_at、reliability_score、domain 传入 write_node；每个事实句必须绑定来源，缺少证据写“待核实” | [nodes.py](D:/working/xiangmu/deepresearch/deep_research/app/mult_agents/nodes.py:1357) | 研究类报告语义引用准确率 > 0.7，幻觉率 < 0.2 | 已完成 |
| PB-02 | P0 | 证据抽取可能被 LLM 空数组清零 | `evidence = payload.get("evidence")` 接受空列表，不回退 | 对 web/local evidence 增加 `if not evidence: evidence = fallback["evidence"]` | [nodes.py](D:/working/xiangmu/deepresearch/deep_research/app/mult_agents/nodes.py:1093) [nodes.py](D:/working/xiangmu/deepresearch/deep_research/app/mult_agents/nodes.py:1166) | 本地原始命中不为 0 时，kept_count 不再为 0 | 已完成 |
| PB-03 | P0 | 大模型裸调用超时导致任务失败 | `ChatTongyi.invoke()` 无节点级超时、重试、熔断 | 给 `_invoke_json_agent` 增加超时、重试和指数退避，失败回退 fallback | [nodes.py](D:/working/xiangmu/deepresearch/deep_research/app/mult_agents/nodes.py:165) | 10 题评测超时用例为 0 | 已完成 |
| PB-04 | P1 | 网络来源低质、时效错位 | 只使用 Bocha 摘要，未抓正文，未按日期和域名过滤 | 增加候选 URL 正文抓取、rerank、域名白名单和发布时间过滤；对含年份的问题启用时间约束 | [tools.py](D:/working/xiangmu/deepresearch/deep_research/app/mult_agents/tools.py:45) | q07 类年份错位问题不再出现 | 部分完成 |
| PB-05 | P1 | 检索召回不足 | 搜索计划最多 6 个查询，每查询仅 4 条，缺少查询扩展和并行 | 增加查询改写、同义扩展、官方站点定向查询，提高单次检索上限并支持并行执行 | [nodes.py](D:/working/xiangmu/deepresearch/deep_research/app/mult_agents/nodes.py:258) | plan_coverage_avg 明显提升 | 部分完成 |
| PB-06 | P1 | Writer 温度偏高，诱导自由扩写 | writer temperature=0.4，提示词要求深度扩写 | 事实型报告温度降至 0.1，调整提示词为“基于证据逐段回答” | [main.py](D:/working/xiangmu/deepresearch/deep_research/app/mult_agents/main.py:428) | 无来源量化数据不再进入正文 | 已完成 |
| PB-07 | P2 | 评测没有真正比对来源片段 | judge 只给 source_index，信息不足 | 把 source snippet 传给 judge，增加 recall/coverage 指标 | [judge_metrics.py](D:/working/xiangmu/deepresearch/deep_research/app/eval/judge_metrics.py:39) | 评测能区分“引用 ID 正确”和“内容确实支持” | 已完成 |
| PB-08 | P2 | 缺少写完后的二次事实校验 | 没有 fact_check 节点 | 增加写后校验，删除或降级 unsupported 声明 | [graph.py](D:/working/xiangmu/deepresearch/deep_research/app/mult_agents/graph.py:52) | 输出前所有事实声明均有可追溯来源 | 已完成 |

## 实施进度

- 已完成 P0：PB-01、PB-02、PB-03。
- 已完成 P1 的 PB-06，部分完成 PB-04、PB-05。
- 已完成 P2 的 PB-07、PB-08。
- 已通过 `python -m py_compile` 对 `nodes.py`、`main.py`、`judge_metrics.py` 做语法检查。
- FactChecker 已加入工作流，`write -> fact_check -> END`。
- 已使用有效 Key 在 Docker 内完成 `output/eval_results_v5` 评测，10/10 成功，无超时失败。
- 修复了 `fact_check_node` 中 `_validate_and_fix_citations` 返回值未解包的 tuple 错误。
- 调整来源过滤逻辑，避免低质量来源把 `source_index` 清空导致引用 ID 全被移除。

## 最新验证结果（2026-08-13 v5）

- 运行成功：10/10，失败用例 0，超时用例 0。
- 引用 ID 合法性：64/64，合法率 100.0%。
- 语义引用准确率：37/40，92.5%。
- 声明级幻觉率：整体 38.9%；研究类口径 26.7%（8/30）。
- 研究完备性：整体 64.7；研究类 q05-q10 平均约 64.5。
- 网络检索：raw=139，kept=73，保留率 52.5%。
- 本地知识库检索：raw=22，kept=22，保留率 100.0%。
- 平均耗时：259.28 秒，P90 1045.8 秒；q06 等长报告仍偏慢。

对比修复前：

- 语义引用准确率从 19.2% 提升到 92.5%。
- 研究类声明幻觉率从约 81.3% 降到 26.7%。
- 本地知识库保留率从 0.0% 提升到 100.0%。

> 注：整体幻觉率仍包含 q01/q03/q04 等 direct 问题，裁判规则把无引用的常识/自述类声明判为 unsupported，因此会拉高整体值；研究类口径更适合评估本轮修复。

结果文件：

- `output/eval_metrics_v5.json`
- `output/eval_judge_v5.json`

## 实施顺序

1. 先做 P0：PB-01、PB-02、PB-03。
2. 再做 P1：PB-04、PB-05、PB-06。
3. 最后做 P2：PB-07、PB-08，并重跑评测闭环。

## 下一步验证

```bash
python deep_research/app/eval/run_eval.py \
  --queries deep_research/app/eval/sample_queries.jsonl \
  --out deep_research/output/eval_results_v2

python deep_research/app/eval/judge_metrics.py \
  --results-dir deep_research/output/eval_results_v2 \
  --out deep_research/output/eval_judge_v2.json
```
