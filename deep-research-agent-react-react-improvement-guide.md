# Deep Research Agent 改进实施文档：ReAct 研究循环 + React 控制台

> 目标读者：Claude Code（接入 DeepSeek 模型）  
> 项目对象：`deep-research-agent`  
> 当前背景：项目后端基于 LangChain `deepagents`，采用 Supervisor + N Researcher + 可选 Critic 的多 Agent 架构；前端当前为 Vue 3 + Vite；已有搜索、RAG、归档、报告生成和基础 Web UI。  
> 本文目标：指导 Claude Code 在不推翻现有架构的前提下，引入 **ReAct-style Agent 行为循环**，并在后端稳定后可选迁移到 **React.js + Vite + TypeScript 前端控制台**。

---

## 0. 总体结论

本项目不要重写成一个单体 ReAct Agent，也不要为了流行直接把 Vue 改成 React。

正确方向是：

```text
DeepAgents 多 Agent 架构继续保留
├── Supervisor：规划、分解、委派、综合、修订
├── Researcher：内部改造为 ReAct-style research loop
├── Critic：负责结构、论证、覆盖度审查
└── Verifier：新增或强化，使用 ReAct-style verification loop 做证据核验

React.js：
└── 只作为第二阶段的前端控制台，用于可视化 run、events、sources、claims、report
```

也就是说：

```text
DeepAgents = 编排骨架
ReAct = 单个研究员/验证器的行动协议
React.js = 前端可视化控制台
```

本次改造优先级：

```text
P0：后端 ReAct-style 研究循环
P1：Source Ledger + Claim Ledger + Verifier
P2：React.js 前端控制台迁移
P3：高级可视化与评测
```

---

## 1. 严格禁止事项

Claude Code 必须遵守以下约束：

```text
1. 不要把整个后端替换成单个 ReAct Agent。
2. 不要删除当前 Supervisor + N Researcher + Critic 架构。
3. 不要删除现有搜索工具、RAG、Chroma、history-database、report 生成逻辑。
4. 不要第一阶段迁移 React.js 前端。
5. 不要破坏现有 CLI 参数和 Flask SSE API。
6. 不要让工具直接返回大段网页正文。
7. 不要将完整隐藏 chain-of-thought 写入日志、文件或前端。
8. 不要让没有 source_id 的发现进入最终结论。
9. 不要让 Verifier 相信 Supervisor 或 Researcher 的总结，Verifier 只能信原始 source 文件。
10. 不要在没有回归测试的情况下修改 RAG / Chroma 索引逻辑。
```

---

## 2. 术语澄清

### 2.1 ReAct-style loop

这里的 ReAct 指 Agent 行为协议：

```text
Reasoning Summary → Action → Observation → Decision → Final
```

注意：这里的 `Reasoning Summary` 不是完整隐藏思维链，而是可审计的简短决策摘要。

允许写入日志的是：

```text
- 为什么选择这个工具
- 当前缺什么信息
- 工具返回了哪些可用观察
- 下一步继续还是停止
```

禁止写入日志的是：

```text
- 完整 chain-of-thought
- 长篇自我推理
- 模型内部推理过程
```

### 2.2 React.js

React.js 是前端 UI 框架。它可以增强：

```text
- Agent 运行过程可视化
- Source ledger 查看
- Claim verification 面板
- Run timeline
- Report preview
- Resume / stop / download 交互
```

但它不会直接提升研究质量。因此 React.js 迁移放在 P2，不作为 P0。

---

## 3. 当前架构保留原则

当前项目应继续保留以下核心结构：

```text
deep-research-agent/
├── run_test.py
├── server.py
├── build_index.py
├── deep_research/
│   ├── agent.py
│   ├── config.py
│   ├── model_factory.py
│   ├── prompts.py
│   ├── subagents.py
│   ├── tools.py
│   ├── rerank.py
│   ├── knowledge_base.py
│   ├── summarizer.py
│   ├── report.py
│   └── skills/
├── workspace/
├── history-database/
├── vector-store/
└── web/
```

本次可以新增：

```text
deep_research/
├── run_state.py
├── source_registry.py
├── claim_registry.py
└── verifier.py        # 可选；也可只在 subagents.py 中定义 verifier subagent

runs/
└── <run_id>/
    ├── workspace/
    ├── notes/
    ├── sources/
    ├── report.md
    ├── report.docx
    ├── research_progress.json
    ├── events.jsonl
    ├── sources.jsonl
    └── claims.jsonl
```

---

## 4. P0：后端 ReAct-style Research Loop

### 4.1 目标

将 Researcher 从“搜索执行器”升级为“可审计的研究行动者”。

每个 Researcher 在工具调用前后必须遵循：

```text
[REASONING_SUMMARY]
[ACTION]
[ACTION_INPUT]
[OBSERVATION]
[DECISION]
[FINAL]
```

### 4.2 修改文件

优先修改：

```text
deep_research/prompts.py
deep_research/subagents.py
deep_research/tools.py
deep_research/config.py
deep_research/model_factory.py
```

如果当前项目已经完成 run 状态层，则同时接入：

```text
deep_research/run_state.py
```

如果没有，则在 P0 新增最小版 `run_state.py`。

---

## 5. Researcher Prompt 改造规格

在 `deep_research/prompts.py` 中修改 `RESEARCHER_PROMPT`。

### 5.1 新增 ReAct-style 行为协议

将以下内容加入 Researcher Prompt：

```text
你必须使用 ReAct-style 研究循环。

每次调用工具前，先输出一个简短的 [REASONING_SUMMARY]。
这个摘要只允许包含：
- 当前已经知道什么；
- 当前还缺什么；
- 下一步为什么选择该工具或查询。

不要输出完整隐藏思维链，不要输出长篇推理过程。

每次工具调用后，必须基于工具结果形成 [OBSERVATION]。
观察必须包含：
- 哪些信息有用；
- 哪些来源可信；
- 哪些信息无关；
- 是否产生 source_id；
- 是否足以支持当前子任务。

然后给出 [DECISION]：
- continue_search：继续搜索
- fetch_source：读取某个候选来源全文
- query_academic：转入学术检索
- query_kb：查询历史知识库
- finalize：停止搜索并返回最终研究结果

只有当 In-scope 范围基本覆盖，且关键发现至少有 source_id 支撑时，才能 finalize。
```

### 5.2 工具选择规则

加入以下工具路由规则：

```text
优先级：
1. search_knowledge_base：先查历史研究，避免重复研究。
2. search_openalex：论文、模型、算法、综述、学术证据。
3. search_crossref：补 DOI、期刊、作者、年份等规范元数据。
4. web_search：官方文档、产品、新闻、博客、政策、近期信息。
5. web_fetch：只读取已经判断高价值的 URL，不要盲目 fetch。
```

### 5.3 Researcher 最终输出格式

强制 Researcher 返回：

```text
[FINAL_RESEARCH_RESULT]

[SUBTASK]
...

[SEARCH_BUDGET]
已使用 N / M 次搜索

[KEY_FINDINGS]
- finding_1: ...
  source_ids: [src_001, src_004]
  evidence_strength: strong / medium / weak
- finding_2: ...
  source_ids: [src_002]
  evidence_strength: medium

[SOURCES]
1. src_001 — title — url/doi — source_type — published_at
2. src_002 — title — url/doi — source_type — published_at

[CONFLICTS]
- none / ...

[GAPS]
- none / ...

[SUFFICIENCY_SELF_CHECK]
- Scope A: covered / partial / missing
- Scope B: covered / partial / missing

[STATUS]
complete / partial
```

---

## 6. P0：工具返回结构化

### 6.1 目标

当前工具返回自然语言较多，不利于 ReAct 观察、事件记录和后续验证。

需要统一工具返回协议：

```text
[TOOL_OBSERVATION]
tool: ...
query_or_url: ...
source_ids: [...]
raw_saved_path: ...

[OBSERVATION_SUMMARY]
- ...
- ...

[WARNINGS]
- none / ...
```

### 6.2 web_fetch 改造

`web_fetch` 不应直接返回 4000 字符网页正文。

新行为：

```text
1. 抓取 URL。
2. 清洗正文。
3. 注册 source_id。
4. 将正文保存到 runs/<run_id>/sources/src_xxx.txt。
5. 写入 sources.jsonl。
6. 返回 800-1200 字以内摘要、source_id、raw_saved_path。
```

返回示例：

```text
[TOOL_OBSERVATION]
tool: web_fetch
url: https://example.com/article
source_ids: [src_001]
raw_saved_path: runs/<run_id>/sources/src_001.txt

[OBSERVATION_SUMMARY]
- 页面主题：...
- 关键事实：...
- 可引用证据：...
- 局限或风险：...

[WARNINGS]
- none
```

### 6.3 web_search 改造

`web_search` 返回候选来源，不强制保存全文。

新行为：

```text
1. 搜索得到候选结果。
2. 对每个候选生成 source_id 或 candidate source record。
3. 写入 sources.jsonl，raw_text_path 为空。
4. 让 Researcher 决定是否 web_fetch。
```

返回示例：

```text
[TOOL_OBSERVATION]
tool: web_search
query: ...

[SOURCE_CANDIDATES]
1. src_001 — title — url — snippet
2. src_002 — title — url — snippet

[OBSERVATION_SUMMARY]
- 搜索结果主要集中在 ...
- 最值得 fetch 的候选是 src_001 / src_002
- 疑似低质量或重复结果：...
```

### 6.4 search_openalex / search_crossref 改造

返回必须包含：

```text
- source_id
- title
- authors
- year
- doi
- landing_page_url
- abstract_summary
- source_type
```

source_type 推荐：

```text
paper_peer_reviewed
paper_preprint
paper_metadata
official_doc
company_blog
news
forum
unknown
```

---

## 7. P0：run_state.py 事件记录

### 7.1 新增或强化文件

新增：

```text
deep_research/run_state.py
```

职责：

```text
1. 管理当前 run_id。
2. 管理 runs/<run_id>/ 目录。
3. 提供 append_event()。
4. 提供 update_progress()。
5. 提供 paths：events.jsonl、sources.jsonl、claims.jsonl、sources_dir、notes_dir。
```

### 7.2 最小 API

建议实现：

```python
def init_run(topic: str, run_id: str | None = None, resume: bool = False) -> str:
    ...

def get_run_id() -> str:
    ...

def get_run_dir() -> Path:
    ...

def get_sources_dir() -> Path:
    ...

def get_events_path() -> Path:
    ...

def append_event(event_type: str, **payload) -> None:
    ...

def update_progress(**payload) -> None:
    ...
```

### 7.3 events.jsonl 结构

每行一个 JSON：

```json
{
  "event_id": "evt_000001",
  "run_id": "2026-06-06_102233_multimodal-llm",
  "timestamp": "2026-06-06T10:31:00+03:00",
  "agent": "researcher-1",
  "phase": "research",
  "event_type": "tool_action",
  "tool": "web_search",
  "input": {
    "query": "BGE-M3 hybrid retrieval dense sparse RRF"
  },
  "output": {
    "observation_summary": "Found sources about BGE-M3 dense and sparse retrieval.",
    "source_ids": ["src_001", "src_002"]
  },
  "budget": {
    "used": 3,
    "limit": 20
  }
}
```

event_type 可选：

```text
run_started
plan_created
task_dispatched
tool_action
tool_observation
source_registered
claim_registered
claim_verified
note_written
report_written
critic_started
critic_finished
verifier_started
verifier_finished
run_completed
run_failed
```

---

## 8. P1：Source Registry

### 8.1 新增文件

```text
deep_research/source_registry.py
```

### 8.2 职责

```text
1. 生成稳定 source_id。
2. 去重 URL / DOI / title。
3. 写入 sources.jsonl。
4. 保存 source 正文。
5. 为工具返回 source_id。
```

### 8.3 sources.jsonl 数据结构

```json
{
  "source_id": "src_001",
  "run_id": "2026-06-06_102233_multimodal-llm",
  "title": "Example Paper",
  "url": "https://example.com/paper",
  "canonical_url": "https://example.com/paper",
  "doi": "10.xxxx/example",
  "authors": ["Author A", "Author B"],
  "published_at": "2025-10-01",
  "fetched_at": "2026-06-06T10:31:00+03:00",
  "source_type": "paper_preprint",
  "quality_score": 0.82,
  "raw_text_path": "runs/<run_id>/sources/src_001.txt",
  "metadata": {
    "tool": "search_openalex",
    "query": "..."
  }
}
```

### 8.4 source_id 生成规则

```text
1. 有 DOI：使用 normalized_doi 作为去重 key。
2. 无 DOI 但有 canonical_url：使用 canonical_url。
3. 无 URL：使用 normalized_title + published_year。
4. 最后 fallback：hash(title + url + fetched_at)。
```

source_id 格式：

```text
src_001
src_002
src_003
```

同一个 run 内稳定递增。

---

## 9. P1：Claim Registry

### 9.1 新增文件

```text
deep_research/claim_registry.py
```

### 9.2 职责

```text
1. 注册关键论断。
2. 将 finding 与 source_id 绑定。
3. 写入 claims.jsonl。
4. 支持 Verifier 更新 verification status。
```

### 9.3 claims.jsonl 数据结构

```json
{
  "claim_id": "claim_001",
  "run_id": "2026-06-06_102233_multimodal-llm",
  "section": "3.2",
  "claim": "BGE-M3 can combine dense and sparse retrieval signals for hybrid retrieval.",
  "source_ids": ["src_001", "src_002"],
  "importance": "high",
  "status": "pending",
  "verification": {
    "verdict": null,
    "verified_at": null,
    "verifier": null,
    "notes": null
  }
}
```

status 可选：

```text
pending
supported
partially_supported
unsupported
contradicted
needs_more_sources
```

importance 可选：

```text
high
medium
low
```

---

## 10. P1：Verifier 子 Agent

### 10.1 目标

Verifier 负责事实核验，不负责写报告，不负责润色。

Verifier 只相信：

```text
- claims.jsonl
- sources.jsonl
- sources/<source_id>.txt
- report.md
```

Verifier 不应相信：

```text
- Supervisor 总结
- Researcher 自评
- 未保存原文的搜索摘要
```

### 10.2 config.py 新增项

```python
VERIFIER_ENABLED = True
VERIFIER_MAX_CLAIMS = 20
VERIFIER_REQUIRE_HIGH_IMPORTANCE = True
REASONING_EFFORT_VERIFIER = "max"
VERIFIER_MODEL = AGENT_MODEL
```

### 10.3 model_factory.py 修改

支持 role = verifier：

```python
def _get_model_name(role: str) -> str:
    if role == "supervisor":
        return cfg.SUPERVISOR_MODEL
    if role == "researcher":
        return cfg.RESEARCHER_MODEL
    if role == "critic":
        return cfg.CRITIC_MODEL
    if role == "verifier":
        return cfg.VERIFIER_MODEL
    if role == "summarizer":
        return cfg.SUMMARIZER_MODEL
    return cfg.AGENT_MODEL
```

### 10.4 subagents.py 新增

```python
def create_verifier_subagent() -> dict | None:
    if not cfg.VERIFIER_ENABLED:
        return None
    return {
        "name": "verifier",
        "description": "验证报告中的关键论断是否被指定来源支持。",
        "system_prompt": VERIFIER_PROMPT,
        "tools": [],
        "model": make_chat_model("verifier"),
    }
```

在 supervisor agent 创建时追加 verifier subagent。

### 10.5 Verifier Prompt

在 `prompts.py` 新增：

```text
你是一个独立的证据核验 Agent。

你的任务不是润色报告，也不是补充观点，而是判断 claims.jsonl 中的 claim 是否被指定 source 支持。

你只能相信以下文件：
- claims.jsonl
- sources.jsonl
- sources/<source_id>.txt
- report.md

不要相信 Supervisor 或 Researcher 的总结，除非它能被 source 文件直接支持。

你必须使用 ReAct-style verification loop：

[REASONING_SUMMARY]
用 1-3 句话说明当前要核验的 claim、需要打开哪些 source、判断标准是什么。
不要输出完整隐藏思维链。

[ACTION]
读取 claims.jsonl / sources.jsonl / sources/<source_id>.txt / report.md。

[OBSERVATION]
总结来源中是否存在直接支持、部分支持、反驳或无关内容。

[VERDICT]
只能选择：
- supported
- partially_supported
- unsupported
- contradicted
- needs_more_sources

[EVIDENCE]
列出 source_id 和最短必要证据摘录。
不要长篇复制来源原文。

[FIX_SUGGESTION]
如果不是 supported，说明应该如何修改报告：
- 删除 claim
- 降低语气
- 补充限定条件
- 补搜索
- 替换来源
```

### 10.6 Verifier 输出格式

```text
[CLAIM_VERIFICATION_RESULT]

claim_id: claim_001
verdict: supported / partially_supported / unsupported / contradicted / needs_more_sources

[SOURCE_EVIDENCE]
- src_001: supports / partially_supports / does_not_support / contradicts
  note: ...
- src_002: ...

[RECOMMENDED_ACTION]
keep / weaken / revise / remove / research_more

[REVISION_SUGGESTION]
...
```

---

## 11. P1：Supervisor Prompt 调整

Supervisor 不要变成 ReAct Agent。它继续负责规划和综合。

需要加入以下规则：

```text
1. 每个核心结论必须绑定至少一个 source_id。
2. Researcher 返回 finding 但没有 source_id 时，只能进入“待验证观察”，不能进入正式结论。
3. 报告摘要和结论只能使用 evidence_strength 为 strong 或 medium 且 source_id 存在的 finding。
4. 如果启用 Verifier，最终报告必须在 Verifier 完成后再定稿。
5. Verifier verdict 为 unsupported 或 contradicted 的 claim 必须删除或重写。
6. Verifier verdict 为 partially_supported 的 claim 必须降低语气，并补充限制条件。
7. 不要把 Researcher 的“充分性自评”当作事实充分，只能当作参考。
```

---

## 12. P1：CLI 修改

在 `run_test.py` 中新增参数：

```text
--enable-verifier
--disable-verifier
--react-loop
--no-react-loop
--run-id <id>
--resume <id|latest>
--list-runs
```

语义：

```text
--enable-verifier
启用 Verifier 子 Agent。

--disable-verifier
关闭 Verifier。

--react-loop
启用 Researcher ReAct-style loop。

--no-react-loop
关闭 ReAct-style loop，回退旧 Researcher Prompt。

--run-id
指定当前 run_id。

--resume
从已有 run 恢复。

--list-runs
列出 runs/ 下历史运行。
```

如果当前项目已经实现 run 管理，则不要重复实现，直接接入现有 run_state。

---

## 13. P1：Flask API 修改

保持现有 API：

```text
POST /api/research
POST /api/stop
GET  /api/download/<filename>
GET  /api/health
```

新增 API：

```text
GET  /api/runs
GET  /api/runs/<run_id>
GET  /api/runs/<run_id>/events
GET  /api/runs/<run_id>/sources
GET  /api/runs/<run_id>/claims
GET  /api/runs/<run_id>/report
POST /api/runs/<run_id>/resume
```

要求：

```text
1. 原有 /api/research 不破坏。
2. SSE 输出中包含 run_id。
3. 每条日志最好能关联 events.jsonl。
4. stop 只停止当前 active run，不误杀其他 run。
5. API 返回 JSON 时要处理文件不存在情况。
```

---

## 14. P2：React.js 前端迁移

### 14.1 迁移前提

只有在以下后端能力稳定后才迁移：

```text
- run_id 可用
- events.jsonl 可用
- sources.jsonl 可用
- claims.jsonl 可用
- Flask API 能返回 run / events / sources / claims / report
```

### 14.2 技术选型

使用：

```text
React
Vite
TypeScript
CSS Modules 或 Tailwind CSS
```

建议第一版：

```text
React + Vite + TypeScript + CSS Modules
```

### 14.3 web/ 目录目标结构

```text
web/
├── package.json
├── vite.config.ts
├── tsconfig.json
├── index.html
├── src/
│   ├── main.tsx
│   ├── App.tsx
│   ├── api/
│   │   ├── research.ts
│   │   └── runs.ts
│   ├── components/
│   │   ├── ResearchForm.tsx
│   │   ├── RunTimeline.tsx
│   │   ├── AgentActivityPanel.tsx
│   │   ├── SourceLedgerPanel.tsx
│   │   ├── ClaimVerificationPanel.tsx
│   │   ├── ReportPreview.tsx
│   │   └── DownloadPanel.tsx
│   ├── types/
│   │   ├── run.ts
│   │   ├── event.ts
│   │   ├── source.ts
│   │   └── claim.ts
│   └── styles/
│       └── globals.css
```

### 14.4 React 组件职责

#### ResearchForm

```text
- 输入研究主题
- 选择 effort：fast / deep / max
- 开关 critic
- 开关 verifier
- 开关 react-loop
- 启动研究
- 停止研究
```

#### RunTimeline

```text
- 显示 run_started
- 显示 plan_created
- 显示 task_dispatched
- 显示 tool_action / tool_observation
- 显示 report_written
- 显示 verifier_finished
- 显示 run_completed / run_failed
```

#### AgentActivityPanel

```text
- 按 researcher 分组展示工具调用
- 显示 query、tool、budget、observation_summary
- 标识重复搜索、预算耗尽、失败工具调用
```

#### SourceLedgerPanel

```text
- 展示 sources.jsonl
- 支持按 source_type 过滤
- 支持按 quality_score 排序
- 点击 source_id 查看元数据
- 显示 raw_text_path
```

#### ClaimVerificationPanel

```text
- 展示 claims.jsonl
- 显示 claim status
- 高亮 unsupported / contradicted
- 点击 claim 显示 source_ids
```

#### ReportPreview

```text
- 展示 report.md
- 渲染 Markdown
- 支持下载 report.md / report.docx
- 后续可支持点击 source_id 跳转来源
```

---

## 15. React 类型定义

### 15.1 event.ts

```ts
export type EventType =
  | "run_started"
  | "plan_created"
  | "task_dispatched"
  | "tool_action"
  | "tool_observation"
  | "source_registered"
  | "claim_registered"
  | "claim_verified"
  | "note_written"
  | "report_written"
  | "critic_started"
  | "critic_finished"
  | "verifier_started"
  | "verifier_finished"
  | "run_completed"
  | "run_failed";

export interface RunEvent {
  event_id: string;
  run_id: string;
  timestamp: string;
  agent?: string;
  phase?: string;
  event_type: EventType;
  tool?: string;
  input?: Record<string, unknown>;
  output?: Record<string, unknown>;
  budget?: {
    used: number;
    limit: number;
  };
}
```

### 15.2 source.ts

```ts
export interface SourceRecord {
  source_id: string;
  run_id: string;
  title?: string;
  url?: string;
  canonical_url?: string;
  doi?: string;
  authors?: string[];
  published_at?: string;
  fetched_at: string;
  source_type: string;
  quality_score?: number;
  raw_text_path?: string;
  metadata?: Record<string, unknown>;
}
```

### 15.3 claim.ts

```ts
export type ClaimStatus =
  | "pending"
  | "supported"
  | "partially_supported"
  | "unsupported"
  | "contradicted"
  | "needs_more_sources";

export interface ClaimRecord {
  claim_id: string;
  run_id: string;
  section?: string;
  claim: string;
  source_ids: string[];
  importance: "high" | "medium" | "low";
  status: ClaimStatus;
  verification?: {
    verdict?: ClaimStatus;
    verified_at?: string;
    verifier?: string;
    notes?: string;
  };
}
```

---

## 16. 配置项建议

在 `config.py` 中新增：

```python
# ── ReAct-style Research Loop ──
REACT_RESEARCH_LOOP_ENABLED = True
REACT_MAX_DECISION_STEPS = 20
REACT_REQUIRE_OBSERVATION_SUMMARY = True

# ── Source Ledger ──
SOURCE_LEDGER_ENABLED = True
SOURCE_TEXT_SAVE_ENABLED = True
SOURCE_TEXT_INLINE_CHAR_LIMIT = 1200
SOURCE_TEXT_HARD_CHAR_LIMIT = 30000

# ── Claim Ledger / Verifier ──
CLAIM_LEDGER_ENABLED = True
VERIFIER_ENABLED = True
VERIFIER_MAX_CLAIMS = 20
VERIFIER_REQUIRE_HIGH_IMPORTANCE = True
REASONING_EFFORT_VERIFIER = "max"

# ── Model Routing ──
SUPERVISOR_MODEL = AGENT_MODEL
RESEARCHER_MODEL = AGENT_MODEL
CRITIC_MODEL = AGENT_MODEL
VERIFIER_MODEL = AGENT_MODEL
SUMMARIZER_MODEL = SUMMARIZE_MODEL
```

---

## 17. 测试与验收

### 17.1 P0 验收命令

```bash
python run_test.py "测试主题：BGE-M3 混合检索的优势" --react-loop --max-searches 5
```

必须产生：

```text
runs/<run_id>/
├── research_progress.json
├── events.jsonl
├── sources.jsonl
├── notes/
└── report.md
```

检查：

```text
- events.jsonl 至少包含 tool_action / tool_observation
- Researcher 输出包含 REASONING_SUMMARY / ACTION / OBSERVATION / DECISION / FINAL
- sources.jsonl 至少有 1 条 source
- report.md 正常生成
```

### 17.2 P1 验收命令

```bash
python run_test.py "测试主题：RAG 中 dense sparse hybrid retrieval 的证据" --enable-verifier --react-loop --max-searches 8
```

必须产生：

```text
claims.jsonl
sources.jsonl
events.jsonl
report.md
```

检查：

```text
- claims.jsonl 至少有 3 条 claim
- 每条 high importance claim 至少有 1 个 source_id
- Verifier 给出 supported / partially_supported / unsupported 等 verdict
- unsupported claim 不进入最终摘要或结论
```

### 17.3 P2 前端验收命令

```bash
cd web
npm install
npm run build
```

启动：

```bash
python server.py
```

访问：

```text
http://localhost:5001
```

必须支持：

```text
- 输入课题并启动研究
- 实时显示 SSE 日志
- 显示 RunTimeline
- 显示 AgentActivityPanel
- 显示 SourceLedgerPanel
- 显示 ClaimVerificationPanel
- 显示 ReportPreview
- 下载 report.md / report.docx
```

---

## 18. 开发顺序

Claude Code 必须按顺序执行：

```text
Step 1: 检查当前是否已有 run_state.py / runs/ 状态层。
Step 2: 如无，则实现最小 run_state.py。
Step 3: 新增 source_registry.py。
Step 4: 改造 web_fetch，保存正文并返回 source_id。
Step 5: 改造 web_search / OpenAlex / Crossref 输出 source_id。
Step 6: 修改 Researcher Prompt 为 ReAct-style loop。
Step 7: events.jsonl 记录 tool_action / tool_observation。
Step 8: 新增 claim_registry.py。
Step 9: 新增 Verifier Prompt 与 verifier subagent。
Step 10: Supervisor 汇总时绑定 claim/source。
Step 11: CLI 增加 --enable-verifier / --react-loop。
Step 12: Flask API 暴露 runs / events / sources / claims。
Step 13: 后端稳定后再迁移 React + Vite + TypeScript 前端。
```

---

## 19. Claude Code 第一条提示

可以直接把下面这段给 Claude Code：

```text
请阅读本文件，并严格按照 P0 → P1 → P2 的顺序改造项目。

第一阶段不要迁移前端，不要替换 DeepAgents 架构，不要使用单个 create_react_agent 重写系统。

请先实现：
1. Researcher Prompt 的 ReAct-style loop；
2. source_registry.py；
3. web_fetch 保存全文到 runs/<run_id>/sources/，工具只返回摘要和 source_id；
4. events.jsonl 记录 tool_action 和 tool_observation；
5. 保持现有 CLI 和 Flask API 兼容。

完成 P0 后停止，输出：
- 修改文件列表
- 新增数据结构
- 新 Researcher Prompt
- 一次最小测试的运行结果
- 尚未完成的 P1/P2 项目
```

---

## 20. 最终目标

完成后，系统应该从：

```text
能运行的深度研究 Agent
```

升级为：

```text
可审计、可恢复、可验证、可可视化的深度研究 Agent
```

最终定位：

```text
DeepAgents：多 Agent 编排
ReAct-style loop：单 Agent 行动质量控制
Source Ledger：来源追踪
Claim Ledger：论断追踪
Verifier：事实核验
React.js：研究过程控制台
```

这是比“单纯换框架”更稳、更符合当前项目资产积累的改进路径。
