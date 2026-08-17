# AI Agent 开发岗面试：DeepResearch 项目题库与回答教程

> 按你最新简历整理。简历里的数字都能在 `deep_research/output/` 和
> `deep_research/docs/修订日志-引用锚定修复.md` 找到出处，面试时可以放心讲口径。

## 0. 怎么用

1. 用「提示词 A」让任意 AI 当面试官，按代码深挖你。
2. 每答完一题，用「提示词 B」让 AI 给出代码级标准答案。
3. 面试前重点过一遍「简历数字口径表」和「坑点清单」。

代码根目录：`deep_research/app/`

```text
app/mult_agents/graph.py     图编排、条件路由、并行边
app/mult_agents/state.py     ResearchState
app/mult_agents/nodes.py     全部节点逻辑
app/mult_agents/prompts.py   Agent 提示词
app/mult_agents/tools.py     Bocha 搜索
app/mult_agents/rag/core.py  Milvus RAG
app/mult_agents/memory/      三层记忆
app/backend/                 FastAPI + SSE
app/eval/                    评测脚本
front/agent_front/src/App.vue 前端流式渲染
docs/修订日志-引用锚定修复.md 修复前后指标
output/eval_metrics.json     自动指标
output/eval_judge_bocha3.json LLM 裁判结果
```

---

## 1. 三段可直接复制的提示词

### 提示词 A：模拟面试官

```text
你是一位资深 AI Agent 开发岗面试官，正在面试候选人。候选人的核心项目是 DeepResearch 多 Agent 深度研究助手，代码在 D:\deepresearch\deep_research，请先阅读 app/mult_agents、app/backend、app/eval、docs/修订日志-引用锚定修复.md、output/eval_metrics.json、output/eval_judge_bocha3.json。

候选人简历原文：
基于 LangGraph 多 Agent 协作构建企业级 AI 深度研究助手，实现从意图识别、双源检索、证据审计到带引用深度研报生成的端到端自动化。
1. 基于 LangGraph + ResearchState 设计多 Agent 流水线（意图路由、规划、双源侦察、证据裁判、分析、反思、撰稿），采用规则引擎 + LLM 双模态意图分流；10 条带标签示例集路由 9/9 正确，约 44% 简单问答被路由到 direct，不进入深度研究链路。
2. 搭建 Bocha 网络搜索 + Milvus 本地 RAG 双路检索与 Evidence Judge 证据裁判机制，实现去重、冲突检测、信源评分；实测网页检索 173 条原始结果保留 97 条（keep rate 56%），信源评分使低质量信源占比从 86.6% 降至 73.2%；Analyst + Reflect 迭代补搜闭环，示例集 55.6% 触发补搜、平均迭代 1.7 轮。
3. 构建评测框架（固定题库 + 自动指标 + LLM 裁判 + 人工复核 + 并发压测），定位并修复引用锚定问题：语义引用准确率由 14.7% 提升至 19.2%，相关证据充分场景达 62.5%；设计短期/长期/语义三层记忆（Postgres + Milvus），支持跨会话个性化与多租户隔离。

面试规则：
1. 一次只问一个问题，问题顺序不固定。每轮根据候选人上一轮的回答和简历覆盖进度，动态选择下一题，不要按固定清单机械推进。
2. 出题必须覆盖简历的每一点：LangGraph + ResearchState 多 Agent 流水线、规则引擎 + LLM 双模态意图分流（9/9、44% direct）、Bocha + Milvus 双路检索（keep rate 56%）、Evidence Judge 去重/冲突/信源评分（86.6%→73.2%）、Analyst + Reflect 补搜（55.6%、1.7 轮）、评测框架（固定题库 + 自动指标 + LLM 裁判 + 人工复核 + 并发压测）、引用锚定修复（14.7%→19.2%、62.5%）、三层记忆与多租户隔离。覆盖完简历所有点后，再自然延伸部署、工程化、开放题。
3. 回答必须能用仓库代码支撑；含糊或与代码不符时连续追问 2-3 次。
4. 禁止吹捧。发现数字口径错误、过度承诺、编造实现时直接指出。
5. 每轮反馈格式：考察点 / 回答亮点 / 漏洞与代码证据（文件 + 函数）/ 1 分钟参考回答。
6. 面试中穿插追问简历数字：9/9 样本是否太小、44% direct 意味着什么、56% keep rate 是否达标、86.6%→73.2% 为什么降幅不大、55.6% 补搜率是否过高、14.7%→19.2% 是怎么修出来的、62.5% 具体指哪个场景、本地检索 kept=0 你怎么解释。
```

### 提示词 B：逐题教学

```text
你是 AI Agent 开发岗面试辅导老师。下面这道题来自候选人的 DeepResearch 项目，代码在 D:\deepresearch\deep_research。

题目：<粘贴题目>

请输出：
1. 面试官想考察什么。
2. 回答框架（先结论，3-5 个要点）。
3. 代码证据：引用 app/mult_agents 或 app/backend 中真实存在的函数、变量、数据流；若简历说的功能代码里没有，必须标注"仓库未实现/未验证"。
4. 1 分钟口头版逐字稿（中文，像跟面试官说话，别背稿）。
5. 最可能追问的 1-2 个问题及应对要点。
```

### 提示词 C：复盘评分

```text
你是资深面试官，复盘下面的面试回答。岗位：AI Agent 开发岗；项目：DeepResearch，代码在 D:\deepresearch\deep_research。

按五维打分（1-5）并给改进建议：
1. 技术准确性：与仓库代码是否一致；
2. 结构清晰度：是否先结论后展开；
3. 诚实度：是否区分简历口径与实测口径，有没有编数字；
4. 工程深度：是否提到具体函数、数据流、异常与降级；
5. 抗追问：连续追问时是否稳定。

<粘贴你的回答>
```

---

## 2. 1 分钟项目介绍（按你简历版本）

面试官您好，我的核心项目叫 DeepResearch，是一个基于 LangGraph 多 Agent 协作的企业级 AI 深度研究助手，解决的是"分析师跨平台找资料慢、信息需要交叉验证、大模型直接回答容易幻觉且引用不可追溯"的问题。

架构上是一条端到端流水线：Intent Router 用"规则引擎 + LLM 双模态"先分流，约 44% 的简单问答直接秒回，不占深度链路；深度研究由 Planner 拆解子问题，Web Scout 和 Local Scout 并行检索网络与本地知识库，Evidence Judge 做去重、冲突检测和信源评分，Analyst 判断证据是否够，不够就由 Reflect 补搜，最后 Writer 基于证据池写带引用编号的深度研报。

工程上我做了三层记忆（短期会话、长期画像、语义向量），FastAPI 提供 /run 和 /stream，前端用 SSE 实时展示节点进度；同时搭了一套评测框架，用固定题库、自动指标、LLM 裁判、人工复核和并发压测把路由准确率、keep rate、补搜轮次、引用准确率都量化出来。

这里我想特别讲一下我踩过并修复的一个真问题：引用锚定。最早 WebScout 可以让 LLM 编造 url 和 title，LLM 裁判测出来语义引用准确率只有 14.7%；我把证据字段改成强制以 Bocha/Milvus 原始检索记录为准，并加了正文链接白名单，修完提升到 19.2%，在证据充分的场景（q06 框架对比）达到 62.5%。虽然整体还不到理想值，但至少我证明了这套评测框架能定位问题、验证修复。

---

## 3. 高频题：考察点 + 代码证据 + 口头版

### Q1. 为什么用 LangGraph，而不是传统 LangChain AgentExecutor 或 ReAct？

考察点：Agent 编排框架选型，是否踩过黑盒循环、上下文污染的坑。

代码证据：
- `graph.py`：`StateGraph(ResearchState)` + `add_node` + `add_conditional_edges`。
- `graph.py`：`should_continue_research()` 精确控制 analyze → reflect 或 write。
- `state.py`：`TypedDict` 定义全局状态，`messages` 用 `Annotated[List[BaseMessage], operator.add]` 自动累积。

口头版：LangGraph 本质是状态机，我可以精确控制每一步的先后和条件分支；AgentExecutor 是黑盒 while 循环，复杂流程容易死循环或丢目标。我的场景是"规划-检索-裁判-分析-补搜-写作"的流水线，天然适合图编排。我选的是 Plan-and-Execute 变体，每个 Agent 职责单一，Prompt 短，可控性强。

### Q2. ResearchState 是怎么设计的？为什么用 TypedDict + Annotated？

考察点：状态设计、类型安全、消息累积。

代码证据：
- `state.py`：`query/user_id/tenant_id/plan/sub_questions/evidence_pool/audit_flags/findings/source_index/iteration/max_iterations/final` 等字段。
- `state.py`：`messages: Annotated[List[BaseMessage], operator.add]`，节点返回值自动追加而不是覆盖。
- `nodes.py`：各节点只读写自己需要的字段，避免整包传递。

口头版：共享状态是节点之间的"协议"，所有字段先定义清楚，IDE 和类型检查能兜住低级错误。`operator.add` 让 messages 自动累积，同时我在 `_invoke_json_agent` 里刻意不把全量 messages 传给模型，控制 Token。

### Q3. 双模态意图路由具体怎么做？9/9 和 44% direct 意味着什么？

考察点：成本控制、路由质量、样本量诚实。

代码证据：
- `nodes.py`：`detect_intent()` 用关键词/正则先给规则结果，如"调研/趋势/20xx年"强制 multiagent。
- `nodes.py`：`intent_node()` 把规则初判注入 prompt 并作为 fallback，LLM 输出非法时回退规则。
- `prompts.py`：intent_router 只输出 `{"route": "direct|multiagent", "reason": "..."}`。
- `output/eval_metrics.json`：9 条完成样例路由 9/9，direct 占比 44.4%。

口头版：先走免费、毫秒级的规则层，命中直接定；规则拿不准才让 LLM 判断，LLM 异常回退规则。44% direct 说明近一半请求被拦截在深度链路之外，这部分请求的响应成本和延迟都大幅下降。9/9 是 10 条带标签样例里 9 条完成样本的结果，样本量小，只能说流程和口径跑通了，不能说系统已经 100% 鲁棒。

追问应对：面试官问"9/9 是不是样本太小"，直接答："是，所以我把它写成 10 条示例集 9/9，没有写 96%；下一步是把题库扩到 200 条并加入人工复核。"

### Q4. 双路并行检索怎么实现？keep rate 56% 怎么解释？

考察点：LangGraph superstep 并行、检索质量口径。

代码证据：
- `graph.py`：`plan` 同时连 `web_search` 和 `local_rag` 两条边，两者无依赖，同一 superstep 并行。
- `nodes.py`：`web_search_node()` 调 `bocha_web_search_records(query, count=4)`，再 `_assign_source_ids` 生成 `WEB{迭代}_{查询}-{序号}`。
- `nodes.py`：`local_rag_node()` 调 `search_knowledge_base_records(limit=4)`，生成 `LOC{迭代}_{查询}-{序号}`。
- `nodes.py`：`_dedupe_sources`、`_minimal_record_filter`、`_prune_evidence_to_allowed_sources` 控制保留率。
- `output/eval_metrics.json`：web raw 173 / kept 97，keep rate 56.1%。

口头版：并行是图结构给的，不是手写 asyncio。从 plan 同时连两条边，两个 Scout 无依赖，框架在同一 superstep 并发执行，都写回 state 后才进 deep_dive。keep rate 56% 是"173 条原始结果经去重、字段过滤、LLM 相关性筛选后保留 97 条"，说明过滤不是摆设；但也要看业务口径，保留太多是噪声，保留太少是漏检，我目前更担心漏检，所以规则上偏向保留。

追问应对：面试官问本地检索 kept=0。诚实答："当前样例里本地知识库 raw 20、kept 0，说明本地证据被相关性筛选全部过滤掉了。可能原因有三个：知识库入库内容与查询不匹配、LLM 过滤阈值太严、本地 collection 的 metadata 不完整。这是我评测暴露出来的真实问题，下一步会加本地证据的强制保留规则和过滤日志。"

### Q5. Evidence Judge 到底做了什么？低质量信源 86.6%→73.2% 为什么降幅不大？

考察点：证据审计机制，以及"评分"和"剔除"的区别。

代码证据：
- `nodes.py`：`deep_dive_node()` 汇总 web/local evidence，产出 `evidence_pool`、`audit_flags`、`source_index`。
- `nodes.py`：`_score_evidence()`：local 0.92、官方 0.88、主流媒体 0.72、普通站点 0.58、来源不完整 0.45。
- `nodes.py`：`_fallback_audit()`：score < 0.6 打 `low_confidence` 标记，不进 source_index。
- `nodes.py`：`_dedupe_sources()` 按 url/doc_id 去重。
- `output/eval_metrics.json`：Judge 前 86.6%，Judge 后 73.2%。

口头版：Judge 做四件事：信源评分、去重、冲突检测、构建 source_index。分数低的证据会被打 `low_confidence` 标记，并且不进 Writer 能看到的来源白名单。

追问应对：降幅不大是因为 Bocha 返回的很多是低质中文站点，评分本身是"打标"不是"删除"；73.2% 这个指标统计的是 evidence_pool 全体的低质量占比，而不是 Writer 实际能用的来源占比。要真正降下来，得在检索层加域名/时效过滤，在裁判层对低分证据直接剔除或要求交叉验证，而不是只打标。这是我下一步的方向。

### Q6. Analyst + Reflect 补搜闭环怎么防死循环？55.6% 触发补搜算高吗？

考察点：反思机制、迭代预算、成本控制。

代码证据：
- `nodes.py`：`analyze_node()` 输出 `needs_more_research`、`missing_gaps`、`findings`。
- `nodes.py`：`reflect_node()` 把 `iteration` +1，生成 `supplementary_queries`。
- `graph.py`：`should_continue_research()` 先判断 `iteration >= max_iterations` 强制 write，再判断 `needs_more_research`。
- `config.json`：`max_iterations: 3`，API 可覆盖。
- `output/eval_metrics.json`：55.6% 触发补搜，平均 1.67 轮，平均缺口 1.56 个。

口头版：Analyst 评估证据完备性，不足就输出 missing_gaps；Reflect 根据"已尝试过的搜索词"生成更垂直的补充查询，再回检索。防死循环靠条件边里的迭代计数，达到预算强制写报告，宁可写"证据不足"也不无限烧 Token。

追问应对：55.6% 说明模型对"证据是否充分"很敏感，也说明单轮检索确实经常不够。这个比例本身没有绝对好坏，要看成本和完备性收益：1.67 轮平均意味着多数任务只多搜一次，预算内可控。如果补搜率过高，我会提高 Analyst 的判定标准或收紧 budget，而不是关掉机制。

### Q7. 引用锚定问题是怎么定位和修复的？14.7%→19.2% 具体怎么来的？

考察点：能否讲清"评测发现问题 → 根因 → 修复 → 复测"的完整链路，这是你简历最有说服力的点。

代码证据：
- `docs/修订日志-引用锚定修复.md`：修复前 8 条完成、语义引用准确率 14.7%；修复后 9 条完成、19.2%；q06 达 62.5%。
- `nodes.py`：`_enrich_evidence_from_raw()` 改为强制覆盖 url/domain/title/snippet/source_type/published_at。
- `nodes.py`：`deep_dive_node()` 对 evidence_pool 再次锚定原始检索记录。
- `nodes.py`：`_strip_unapproved_links()` 正文链接必须命中 source_index.locator 白名单，否则退化为纯文本。
- `prompts.py`：write prompt 增加"无来源数据写暂无可靠公开来源/待核实"。
- `app/eval/judge_metrics.py`：Qwen 严格裁判口径。

口头版：最开始 LLM 裁判报出三个典型错误：引用 URL 404、域名非法、2026 页面支撑 2025 事件。根因是 WebScout 整理证据时可以对合法 source_id 编造 url/title，原来的 `_enrich_evidence_from_raw` 只在字段缺失时补全，不会覆盖编造值；Judge 也可能改写 locator；Writer 只校验了引用编号，没校验链接。修复分三步：证据字段强制以原始检索记录为准、deep_dive 后再锚定一次、正文链接加白名单校验。复测后 14.7%→19.2%，q06 这种证据充分的场景到 62.5%。

追问应对：被问"为什么整体还是 19.2%"。答："剩余问题在信源质量：Bocha 返回的低质中文站点多、snippet 不含量化数据，加上 Writer 仍会用模型记忆补细节。下一步是信源质量/时效过滤，并强制只引用 snippet 里能证的内容。"

### Q8. 除了引用编号校验，还怎么控制幻觉？

考察点：是否理解提示约束、数据回填、后处理各自的边界。

代码证据：
- `nodes.py`：`write_node()` 只注入 findings + source_index + audit_flags，并给出合法 source_id 列表。
- `nodes.py`：`_validate_and_fix_citations()` 正则移除非法引用 ID。
- `nodes.py`：`_enrich_evidence_from_raw()` 覆盖 LLM 编造的字段。
- `nodes.py`：`_ensure_reference_section()` 自动拼接参考资料。

口头版：三道防线：检索层用原始记录回填，杜绝假 URL；写作层只给白名单来源并硬约束"没有来源就写待核实"；输出层正则校验引用编号、链接白名单。但我必须诚实说：这些管住的是"引用锚定"，管不住"声明级事实"；所以我评测时把两者分开，LLM 裁判盯的是声明有没有被来源支撑。

### Q9. 评测框架怎么搭的？为什么分开"自动指标"和"LLM 裁判"？

考察点：工程化评测、指标口径、诚实度。

代码证据：
- `app/eval/run_eval.py`：跑固定题库，保存 route/evidence/source_index/iteration/latency/final。
- `app/eval/compute_metrics.py`：路由准确率、引用 ID 合法性、低质量信源占比、检索覆盖率、完备性代理、延迟分位数、迭代统计。
- `app/eval/judge_metrics.py` / `judge_reports.py`：Qwen 严格裁判 + 人工复核表。
- `app/eval/run_http_eval.py`：黑盒 API 评测。
- `app/eval/stress_test.py`：HTTP 并发压测。
- `output/eval_metrics.json`、`output/eval_judge_bocha3.json`：两类结果分开存放。

口头版：我分四层：路由层、检索层、引用层、端到端层。自动脚本算的是可复现的机械指标（路由、引用 ID 是否在 source_index、延迟分位数）；LLM 裁判算的是声明级幻觉和引用可验证性，人工复核再兜底。两套口径必须分开，因为"引用编号合法"和"引用真的支撑结论"是两件事，混在一起就是自欺欺人。

追问应对：被问"LLM 裁判本身可不可靠"。答："LLM 裁判有偏差，所以我的设计是 LLM 初筛 + 人工盲评复核，当前仓库已生成评审 CSV；最终写进简历的数字以人工复核为准。"

### Q10. 三层记忆怎么设计？多租户怎么隔离？

考察点：记忆架构、跨会话注入、数据隔离。

代码证据：
- `memory/manager.py`：short_term / semantic / episodic 三类，后端 postgres、redis、sqlite、Milvus。
- `memory/manager.py`：`add_short_term_message()` + `_compress_pg_thread()`：超过 `short_term_max_messages`（30）触发滚动摘要，旧消息物理清理。
- `memory/manager.py`：`persist_turn()` 按"记住/我叫/我喜欢"标记提取事实和偏好，写 user_profiles / memory_entries，同时写 Milvus。
- `memory/manager.py`：`build_personalized_prompt_context()` 组装画像、最近对话、摘要、相关记忆、最近任务。
- `memory/manager.py`：`_search_milvus()` 逐条校验 tenant_id/user_id，不匹配打 `tenant_or_user_mismatch` 丢弃。
- `nodes.py`：`with_memory_context()` 以 `[跨会话记忆]` 注入各节点。

口头版：短期记忆管会话，超阈值滚动压缩；长期记忆分语义（画像/事实）和情景（历史任务），Postgres 打底 + Milvus 向量索引；每次请求 `build_personalized_prompt_context` 把 5 类数据拼成上下文注入所有节点。隔离上，存储层所有表带 tenant_id + user_id，Redis key 也是租户/用户前缀，Milvus 检索后代码级强校验 metadata，跨用户命中直接丢弃。

### Q11. Milvus 挂了系统会崩吗？

考察点：降级容错，生产意识。

代码证据：
- `memory/manager.py`：`search_semantic()` Milvus 无结果或异常时降级 `_search_postgres()`。
- `memory/manager.py`：`_search_postgres()` 用 `summary ILIKE %s OR content::text ILIKE %s`。
- `memory/manager.py`：`_index_memory_milvus()` 写入前 `setdefault("source", "memory")`，避免缺字段写失败。
- `memory/manager.py`：长期记忆 PG + Milvus 双写。
- `app/mult_agents/rag/core.py`：RAG 搜索异常时返回错误文本，不抛死。

口头版：记忆是双写的，Milvus 只作为增强检索；写入失败打 warning，检索失败自动降级 PG 的 ILIKE，再不行还有 SQLite。向量库挂掉最多是"没那么懂用户"，流程不会断。

### Q12. FastAPI + SSE 的流式进度是怎么实现的？

考察点：异步、事件流、前后端契约。

代码证据：
- `backend/service/workflow_service.py`：`stream_events()` 用 `asyncio.Queue` + 后台 `Thread(worker)`，`run_coroutine_threadsafe` 把事件送回事件循环。
- `backend/service/workflow_service.py`：`_run_sync_with_events()` 用 `app.stream(stream_mode="updates")` 遍历节点，emit phase/route/final。
- `backend/router/research_router.py`：`/stream` 返回 `StreamingResponse`，事件序列化为 `data: {...}\n\n`。
- `front/agent_front/src/App.vue`：`fetch` + `getReader()` + `TextDecoder`，按 `\n\n` 切分，`JSON.parse` 成 `StreamEvent` 分发。

口头版：后端把 LangGraph 的 stream 包装成事件源，每个节点完成推一个 phase 事件。因为图是同步执行，我用工作线程跑图，通过 asyncio.Queue 桥接回事件循环。前端用 ReadableStream 逐步解 SSE，实时渲染进度，final 到达后渲染 Markdown。

### Q13. Token 和上下文怎么控制？

考察点：多 Agent 上下文膨胀、渐进式注入。

代码证据：
- `nodes.py`：`_format_raw_records()` 每条 snippet 截 500 字符。
- `nodes.py`：`web_search_node()` 每查询 count=4。
- `nodes.py`：`_invoke_json_agent()` 不传 `state["messages"]`，每节点只带当前指令和数据。
- `nodes.py`：`write_node()` 只给当前一条指令，避免被前面 JSON 带偏。
- `memory/manager.py`：滚动摘要压缩长对话。

口头版：三处控制：输入端长对话压成摘要；中间层截断、去重、剪枝；模型调用层按节点注入，不复述全量历史。

### Q14. LLM 输出不是合法 JSON 怎么办？

考察点：工程鲁棒性。

代码证据：
- `nodes.py`：`_extract_json_block()` 剥离围栏、取首尾大括号。
- `nodes.py`：`_load_json()` 失败返回 fallback。
- `nodes.py`：每节点有 fallback：`_default_plan`、`_fallback_web_evidence`、`_fallback_local_evidence`、`_fallback_audit`、`_fallback_analysis`。

口头版：所有 JSON 节点走统一封装，解析失败返回该节点专属默认结构，图继续往下走，不会因为一个节点输出异常整条链路崩溃。

### Q15. 多用户并发会串吗？服务怎么隔离？

考察点：服务层并发 + 状态隔离。

代码证据：
- `backend/service/workflow_service.py`：`_ensure_initialized()` 用 `Lock` 保证单例；`run()` 用 `asyncio.to_thread`；`stream_events()` 每请求一个 worker 线程。
- `backend/service/workflow_service.py`：每次请求 `create_initial_state()` 新建 state，`thread_id` 隔离 checkpoint。
- `memory/manager.py`：所有 key/SQL 带 tenant/user/thread。

口头版：初始化用锁保证单例；每个请求独立 state，checkpointer 按 thread_id 隔离；记忆全部按租户/用户/会话过滤。流式请求各自独立线程 + 队列，不共享可变状态。

### Q16. 最大难点是什么？

考察点：复盘能力，是否愿意讲失败。

推荐答案：引用锚定。因为它是"评测才发现、根因在 LLM 数据污染、修复涉及三个环节"的真问题：WebScout 编造字段、Judge 改写 locator、Writer 校验不足。修复后引用准确率从 14.7% 到 19.2%，证据充分的场景到 62.5%。它让我明白，Agent 的可靠性不能靠单个节点的 prompt，要靠"数据回填 + 白名单 + 后处理 + 评测闭环"整条链路。

备选答案：上下文膨胀。处理方式是 snippet 截断、证据剪枝、按节点注入。

---

## 4. 简历数字口径表

| 简历写法 | 仓库出处 | 被追问怎么答 |
| --- | --- | --- |
| 10 条带标签示例集路由 9/9 | `output/eval_metrics.json`：9 条完成、route 100% | "10 条里 q08 因 DashScope 读超时失败，所以是 9/9 完成样本；样本量小，我没写成 96%。" |
| 约 44% direct | `eval_metrics.json`：direct_route_share 44.4% | "44% 是 4/9 的 direct 占比，表示简单问答被拦在深度链路外，成本和延迟都省了。" |
| 网页 173 raw → 97 kept，56% | `eval_metrics.json`：web raw_count=173、kept_count=97 | "56% 是去重+字段过滤+LLM 相关性筛选后的保留率；保留策略偏宽松，优先不漏检。" |
| 低质量信源 86.6%→73.2% | `eval_metrics.json`：before_judge / after_judge | "评分是打标不是删除，73.2% 统计的是整个证据池；Writer 实际只能看到 source_index 白名单。" |
| 55.6% 触发补搜、平均 1.7 轮 | `eval_metrics.json`：needs_more_research_rate 55.6%、avg_iterations 1.67 | "平均只多搜不到一轮，预算默认 3 轮封顶，可配置。" |
| 语义引用准确率 14.7%→19.2% | `docs/修订日志-引用锚定修复.md`；bocha2 14.7%、bocha3 19.2% | "这是 Qwen 严格裁判口径：34 条引用验证 5 条 → 52 条验证 10 条；不是引用 ID 合法性口径。" |
| 相关证据充分场景 62.5% | `eval_judge_bocha3.json` q06（LangGraph vs CrewAI） | "62.5% 是 q06 单条：8 条引用验证 5 条。证据相关时效果明显，整体仍受信源质量拖累。" |
| 三层记忆 Postgres + Milvus | `memory/manager.py` | "短期 postgres/redis，长期语义+情景 postgres + Milvus，异常降级 SQLite/ILIKE。" |

## 5. 坑点清单

1. 不要说"96%、25%→6%、94%、200 条"这些旧文档数字，你的简历已经用实测数字，口径统一。
2. q08 失败原因说清楚：DashScope 读超时，不是业务逻辑问题，已留日志待重跑。
3. 本地检索 kept=0 一定要主动认，别等面试官挖出来；给出三个根因假设和下一步。
4. 引用准确率 19.2% 是 LLM 裁判口径，引用 ID 合法率 100% 是脚本口径，两者别混着说。
5. "checkpoint 按月分区/Cron 清理"仓库没实现，不要说做了；回答是生产化待办。
6. 短期记忆默认后端是 postgres，Redis 是可选后端，别说成默认。
7. SSE 实际是 Thread + asyncio.Queue，不是 `asyncio.create_task`，按真实实现讲。
8. 8 个研究角色之外还有 direct_answer，一共 9 个图节点，数清楚。

---

## 6. 30 分钟冲刺

1. 0-5 分钟：背第 2 节项目介绍，说一遍。
2. 5-20 分钟：用提示词 A 模拟面试，每题 1 分钟，不看文档。
3. 20-25 分钟：把回答贴给提示词 C 打分。
4. 25-30 分钟：用提示词 B 重学最弱两题，再复述一遍。

练完给自己留一张"一页答案卡"：每题只写 3 个代码证据 + 3 句口头版。
