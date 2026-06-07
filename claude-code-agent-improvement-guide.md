# Claude Code 执行指南：深度研究 Agent 工程化改进方案

> 适用对象：Claude Code（接入 DeepSeek 模型）  
> 目标代码库：`deep-research-agent/`  
> 文档目的：指导 Claude Code 按阶段改进现有多智能体深度研究系统，使其具备更强的长任务稳定性、上下文控制、断点恢复、证据验证和可观测性。  
> 执行原则：不要一次性重构全项目。必须按阶段、小步提交、每阶段验收。

---

## 0. 背景摘要

当前项目已经具备较强的深度研究 Agent 基础能力：

- 架构为 `Supervisor + N Researcher + 可选 Critic`。
- Supervisor 负责任务规划、委托、综合、报告写作。
- Researcher 负责搜索、抓取、整理发现，不直接写最终报告。
- Critic 负责读取 `/report.md` 和 `/notes/` 进行质量审查。
- 搜索管道已有：`DDGS -> Cross-Encoder rerank`，并集成 `OpenAlex / Crossref`。
- 知识库已有：`BGE-M3 dense + sparse`、`RRF`、`Chroma`、`contextual retrieval`、`KB rerank`。
- Prompt 工程已有：MECE 分解、OODA 循环、结构化任务简报、搜索预算、充分性自检。

当前主要瓶颈不是“Agent 不够聪明”，而是：

1. **上下文管理弱**：工具结果会直接进入模型上下文，长任务容易上下文膨胀。
2. **断点恢复弱**：`workspace/` 每轮清空，中断后只能从头跑。
3. **证据验证弱**：Critic 主要审文本质量，不能系统核验每个关键论断是否被来源支持。
4. **状态可观测性弱**：缺少标准化的 run timeline、source ledger、claim ledger、event log。
5. **模型与成本控制粗糙**：Supervisor / Researcher / Critic 基本共用一个模型配置，未充分利用角色差异和 DeepSeek context cache。

本次改造目标：

> 将项目从“能完成一次深度研究的 Agent”升级为“可长时间运行、可恢复、可审计、可验证、成本可控的研究系统”。

---

## 1. 总体执行规则

Claude Code 必须遵守以下规则：

### 1.1 不要做大爆炸式重构

必须按以下顺序执行：

1. P0：运行状态层与 run 目录隔离
2. P1：工具结果 offload 与上下文预算控制
3. P1.5：模型路由与 Prompt cache 友好化
4. P2：Claim Ledger 与事实验证器
5. P2.5：测试、评测、回归保护
6. P3：DeepAgents 新版迁移 Spike 与 Web UI 增强

每一阶段完成后，必须运行对应验收命令。不要在 P0 未稳定前开始 P2/P3。

### 1.2 保留现有能力

不得破坏：

- `run_test.py` 的基本 CLI 运行方式。
- `server.py` 的 Flask SSE 输出。
- `workspace/report.md` 和 `workspace/report.docx` 的生成路径兼容。
- `history-database/` 归档逻辑。
- `vector-store/` Chroma 增量索引逻辑。
- `search_knowledge_base`、`search_openalex`、`search_crossref`、`web_search`、`web_fetch` 的基本工具名。
- Prompt 中已有的 MECE、OODA、搜索预算、充分性自检逻辑。

可以新增路径和配置，但要尽量保持旧入口可用。

### 1.3 优先工程控制，而不是继续堆 Prompt

Prompt 可以增强行为，但不能替代：

- 状态持久化
- 事件日志
- source registry
- claim registry
- 上下文 offload
- 断点恢复
- 验证器

本次改造应尽量把关键约束放到代码层，而不是只写进 Prompt。

### 1.4 所有新增配置必须集中到 `deep_research/config.py`

现有项目的配置系统优点是所有模块通过：

```python
from . import config as cfg
```

动态引用配置。新增参数也必须沿用这个模式，不要在模块 import 时捕获配置值。

---

## 2. 目标架构

改造后目录结构建议如下：

```text
deep-research-agent/
├── run_test.py
├── server.py
├── build_index.py
├── deep_research/
│   ├── config.py
│   ├── agent.py
│   ├── model_factory.py
│   ├── prompts.py
│   ├── subagents.py
│   ├── tools.py
│   ├── source_registry.py        # 新增：来源注册、规范化、正文保存
│   ├── runtime_state.py          # 新增：run 状态、事件日志、进度文件
│   ├── claim_verifier.py         # 新增：claim 抽取与事实验证
│   ├── schemas.py                # 新增：数据结构 / dataclass / schema helpers
│   ├── evals.py                  # 可选新增：检索与报告质量评测入口
│   ├── rerank.py
│   ├── knowledge_base.py
│   ├── summarizer.py
│   ├── report.py
│   └── skills/
├── runs/                         # 新增：每次研究一个 run 目录
│   └── <run_id>/
│       ├── workspace/
│       │   ├── report.md
│       │   ├── report.docx
│       │   ├── research_summary.txt
│       │   ├── notes/
│       │   └── skills/
│       ├── sources/
│       │   ├── src_000001.txt
│       │   └── src_000002.txt
│       └── state/
│           ├── research_progress.json
│           ├── events.jsonl
│           ├── sources.jsonl
│           ├── claims.jsonl
│           └── verification.jsonl
├── workspace/                    # 保留兼容：默认指向/复制 latest run workspace
├── history-database/
└── vector-store/
```

核心变化：

- 每次研究生成一个 `run_id`。
- 每个 run 拥有独立 `workspace/`、`sources/`、`state/`。
- `workspace/` 不再是唯一运行状态来源。
- 大工具结果不直接塞回上下文，而是保存到 `/sources/`。
- 报告中的关键论断进入 `claims.jsonl`。
- Claim Verifier 读取原始来源并给出 `SUPPORTED / PARTIAL / UNSUPPORTED / CONTRADICTED`。

---

## 3. P0：运行状态层与 run 目录隔离

### 3.1 目标

建立项目的“运行控制面”：每次研究都拥有独立 run 目录、进度文件、事件日志和可恢复状态。

完成后应支持：

```bash
python run_test.py "研究主题" --run-id smoke_test
python run_test.py --resume smoke_test
python run_test.py --resume latest
```

### 3.2 修改 `config.py`

新增配置：

```python
# ── Run / State 配置 ──
RUNS_DIR = PROJECT_ROOT / "runs"
DEFAULT_RUN_ID_FORMAT = "%Y%m%d_%H%M%S"
STATE_SCHEMA_VERSION = 1
ENABLE_RUN_STATE = True
COPY_LATEST_TO_WORKSPACE = True

# workspace 兼容策略
LEGACY_WORKSPACE_COMPAT = True

# 事件日志
EVENT_LOG_FILENAME = "events.jsonl"
PROGRESS_FILENAME = "research_progress.json"
SOURCES_LEDGER_FILENAME = "sources.jsonl"
CLAIMS_LEDGER_FILENAME = "claims.jsonl"
VERIFICATION_LEDGER_FILENAME = "verification.jsonl"
```

要求：

- 保持 `WORKSPACE_DIR` 存在，避免旧代码崩溃。
- 新增 `RUNS_DIR`，但不要删除旧 `workspace/`。

### 3.3 新增 `deep_research/runtime_state.py`

实现职责：

1. 创建 run 目录。
2. 恢复已有 run。
3. 维护当前 run 上下文。
4. 写 `research_progress.json`。
5. 追加 `events.jsonl`。
6. 提供 workspace/source/state 路径。
7. 提供简单的原子写 JSON 能力。

建议接口：

```python
from __future__ import annotations

from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Any, Literal
import json
import os
import shutil
from datetime import datetime, timezone

@dataclass
class RunContext:
    run_id: str
    topic: str | None
    run_dir: Path
    workspace_dir: Path
    sources_dir: Path
    state_dir: Path
    resumed: bool = False

_current_run: RunContext | None = None


def init_run(topic: str | None = None, run_id: str | None = None, resume: bool = False) -> RunContext:
    """Create or resume a research run."""
    ...


def get_run() -> RunContext:
    """Return current run context. Initialize default run if needed."""
    ...


def get_workspace_dir() -> Path:
    return get_run().workspace_dir


def get_sources_dir() -> Path:
    return get_run().sources_dir


def get_state_dir() -> Path:
    return get_run().state_dir


def record_event(event_type: str, payload: dict[str, Any] | None = None, agent: str | None = None) -> None:
    """Append one JSON object to events.jsonl."""
    ...


def load_progress() -> dict[str, Any]:
    ...


def save_progress(progress: dict[str, Any]) -> None:
    """Atomic write research_progress.json."""
    ...


def update_progress(**updates: Any) -> None:
    ...


def append_jsonl(filename: str, item: dict[str, Any]) -> None:
    ...


def atomic_write_json(path: Path, data: dict[str, Any]) -> None:
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    os.replace(tmp, path)
```

### 3.4 `research_progress.json` schema

初始结构：

```json
{
  "schema_version": 1,
  "run_id": "20260606_102233",
  "topic": "...",
  "phase": "initialized",
  "created_at": "2026-06-06T10:22:33+03:00",
  "updated_at": "2026-06-06T10:22:33+03:00",
  "status": "running",
  "tasks": [],
  "completed_researchers": [],
  "pending_researchers": [],
  "notes_files": [],
  "source_count": 0,
  "claim_count": 0,
  "verification": {
    "enabled": false,
    "verified": 0,
    "unsupported": 0,
    "partial": 0,
    "contradicted": 0
  },
  "report_status": {
    "outline_done": false,
    "draft_done": false,
    "critic_done": false,
    "verified": false,
    "docx_done": false
  },
  "errors": []
}
```

`phase` 允许值建议：

```text
initialized
planning
researching
notes_consolidated
report_drafting
critic_review
verification
completed
failed
aborted
```

### 3.5 `events.jsonl` schema

每行一个事件：

```json
{
  "ts": "2026-06-06T10:31:00+03:00",
  "run_id": "20260606_102233",
  "event_type": "tool_call",
  "agent": "researcher-1",
  "payload": {
    "tool": "web_search",
    "query": "..."
  }
}
```

建议事件类型：

```text
run_started
run_resumed
phase_changed
tool_call
tool_result
search_committed
source_registered
note_written
report_written
claim_registered
claim_verified
critic_started
critic_completed
archive_completed
index_completed
run_completed
run_failed
```

### 3.6 修改 `agent.py`

当前 `_prepare_workspace()` 会清空全局 `workspace/`。改造后：

- 新 run：清空该 run 下的 `workspace/`。
- resume：不得清空已有 run workspace。
- 保留旧 `workspace/`：如果 `COPY_LATEST_TO_WORKSPACE=True`，可在 run 完成后复制 latest workspace 到项目根 `workspace/`，用于兼容下载和旧脚本。

建议改造：

```python
from .runtime_state import get_run, record_event


def _prepare_workspace(resume: bool = False):
    run = get_run()
    workspace = run.workspace_dir

    if not resume:
        # clear only this run's workspace
        ...
    else:
        # ensure dirs exist, do not delete files
        ...

    (workspace / "notes").mkdir(parents=True, exist_ok=True)
    copy skills into workspace / "skills"
    record_event("workspace_prepared", {"workspace": str(workspace), "resume": resume})
```

注意：如果 `create_supervisor_agent()` 当前没有 `resume` 参数，可以新增：

```python
def create_supervisor_agent(resume: bool = False):
    _prepare_workspace(resume=resume)
    ...
```

### 3.7 修改 `run_test.py`

新增 CLI 参数：

```python
parser.add_argument("--run-id", default=None)
parser.add_argument("--resume", nargs="?", const="latest", default=None)
parser.add_argument("--list-runs", action="store_true")
```

运行逻辑：

```python
if args.list_runs:
    list recent runs
    return

if args.resume:
    run_id = resolve_latest_run() if args.resume == "latest" else args.resume
    init_run(topic=None, run_id=run_id, resume=True)
    topic = load_progress()["topic"]
else:
    init_run(topic=topic, run_id=args.run_id, resume=False)
```

在主要阶段更新 progress：

- 开始：`phase=initialized`
- 调用 agent 前：`phase=planning`
- 发现 task tool calls：`phase=researching`
- 写 report：`phase=report_drafting`
- critic：`phase=critic_review`
- docx 转换后：`report_status.docx_done=true`
- 归档后：`phase=completed,status=completed`
- 异常：`phase=failed,status=failed,errors.append(...)`

### 3.8 修改 `server.py`

Web API 应支持 run_id：

- `/api/research` 返回 `run_id`。
- SSE log 事件中包含 `run_id`。
- `/api/download/<fn>` 默认下载 latest run 的文件。
- 新增 `/api/runs` 列出最近 runs。
- 可选新增 `/api/resume/<run_id>`。

最低要求：不要破坏现有前端。如果前端暂不改，也要保证 `/api/download/report.md` 能拿到 latest run 的 report。

### 3.9 P0 验收

执行：

```bash
python run_test.py "测试：简要研究 Python typing 的最新变化" --short-thinking --run-id smoke_p0
```

检查：

```bash
ls runs/smoke_p0
ls runs/smoke_p0/workspace
ls runs/smoke_p0/state
cat runs/smoke_p0/state/research_progress.json
head runs/smoke_p0/state/events.jsonl
```

必须满足：

- `runs/smoke_p0/workspace/report.md` 存在，或失败时 `research_progress.json` 记录 failed。
- `events.jsonl` 至少包含 `run_started`、`workspace_prepared`、若干 tool 相关事件、`run_completed` 或 `run_failed`。
- `python run_test.py --resume smoke_p0` 不应删除已有 workspace。
- 项目根 `workspace/` 兼容路径仍可用。

---

## 4. P1：工具结果 Offload 与上下文预算控制

### 4.1 目标

减少工具结果对 Agent 上下文的污染。大网页正文、学术摘要、搜索结果不应全部直接返回给模型，而应保存到 run 的 `/sources/`，工具返回轻量摘要、source_id 和文件路径。

### 4.2 修改 `config.py`

新增配置：

```python
# ── Context / Tool Output 控制 ──
WEB_FETCH_INLINE_CHAR_LIMIT = 1200
WEB_FETCH_FULLTEXT_SAVE = True
WEB_SEARCH_INLINE_RESULTS = 4
TOOL_OUTPUT_SOFT_CHAR_LIMIT_PER_AGENT = 18000
TOOL_OUTPUT_HARD_CHAR_LIMIT_PER_AGENT = 30000
SOURCE_ID_PREFIX = "src"
SOURCE_SNIPPET_CHAR_LIMIT = 800
ENABLE_SOURCE_REGISTRY = True

# 可选 HTML 正文抽取
USE_TRAFILATURA = True
USE_READABILITY_FALLBACK = True
```

### 4.3 新增 `deep_research/source_registry.py`

职责：

1. 规范化 URL。
2. 生成稳定 source_id。
3. 保存全文到 `/sources/<source_id>.txt`。
4. 追加 `sources.jsonl`。
5. 对 DOI / canonical URL / title 做去重。
6. 返回轻量的 SourceRecord。

建议接口：

```python
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Any
import hashlib
import json
from urllib.parse import urlsplit, urlunsplit, parse_qsl, urlencode

@dataclass
class SourceRecord:
    source_id: str
    url: str
    canonical_url: str | None = None
    doi: str | None = None
    title: str | None = None
    authors: list[str] | None = None
    published_at: str | None = None
    fetched_at: str | None = None
    source_type: str = "unknown"
    quality_score: float | None = None
    saved_path: str | None = None
    content_chars: int = 0
    query: str | None = None
    tool: str | None = None


def canonicalize_url(url: str) -> str:
    """Remove tracking params, normalize scheme/host, keep meaningful path/query."""
    ...


def make_source_id(url: str | None = None, doi: str | None = None, title: str | None = None) -> str:
    ...


def save_source_text(record: SourceRecord, text: str) -> SourceRecord:
    ...


def register_source(
    *,
    url: str,
    text: str = "",
    title: str | None = None,
    doi: str | None = None,
    source_type: str = "unknown",
    query: str | None = None,
    tool: str | None = None,
    metadata: dict[str, Any] | None = None,
) -> SourceRecord:
    ...


def format_source_tool_response(record: SourceRecord, snippet: str, extra: dict[str, Any] | None = None) -> str:
    ...
```

URL 规范化规则：

- 移除 `utm_*`、`fbclid`、`gclid` 等跟踪参数。
- host 小写。
- 去掉 fragment。
- 保留 DOI、arXiv ID 等关键信息。

### 4.4 修改 `tools.py`：上下文预算

新增全局计数：

```python
_tool_output_chars: dict[str, int] = {}
```

新增函数：

```python
def _track_tool_output(text: str) -> str:
    tag = _get_tag()
    n = len(text or "")
    _tool_output_chars[tag] = _tool_output_chars.get(tag, 0) + n

    total = _tool_output_chars[tag]
    if total >= cfg.TOOL_OUTPUT_HARD_CHAR_LIMIT_PER_AGENT:
        return text + (
            "\n\n⛔ 上下文硬限制已触发：当前研究员累计工具输出过大。"
            "请立即停止搜索，基于已有 source_id 和笔记返回最终结构化发现。"
        )
    if total >= cfg.TOOL_OUTPUT_SOFT_CHAR_LIMIT_PER_AGENT:
        return text + (
            "\n\n⚠️ 上下文软限制已触发：请优先提炼发现到 /notes/，"
            "避免继续抓取大页面。"
        )
    return text
```

所有工具返回前统一包一层：

```python
return _track_tool_output(result)
```

### 4.5 修改 `web_fetch`

当前 `web_fetch` 直接返回最多 4000 字符正文。改成：

1. 抓取网页。
2. 抽取正文。
3. 注册 source。
4. 全文保存到 `/sources/<source_id>.txt`。
5. 返回轻量摘要。

目标返回格式：

```text
[WEB_FETCH_SAVED]
source_id: src_8f31a2
url: https://example.com/article
saved_to: /sources/src_8f31a2.txt
content_chars: 18342

关键片段：
...

使用建议：
- 后续引用请使用 source_id: src_8f31a2
- 如需核验证据，请 read_file('/sources/src_8f31a2.txt')
```

实现注意：

- 如果 `WEB_FETCH_FULLTEXT_SAVE=True`，即使正文很短也保存 source 文件。
- 返回给模型的正文不得超过 `WEB_FETCH_INLINE_CHAR_LIMIT`。
- 失败时仍记录 `tool_result` 事件，但不要注册空 source。

### 4.6 正文抽取改进

当前 `_html_to_text` 是正则清洗。保留它作为 fallback，但优先使用：

```python
try:
    import trafilatura
    text = trafilatura.extract(html, include_comments=False, include_tables=True)
except Exception:
    text = None

if not text:
    try readability / BeautifulSoup

if still not text:
    text = _html_to_text(html)
```

依赖处理：

- 不要强制要求用户必须安装 `trafilatura`。
- 如果未安装，优雅降级。
- 可在 `requirements.txt` 中新增可选依赖，或在文档注明。

### 4.7 修改 `web_search`

`web_search` 可以仍返回前几条结果，但应同时将搜索结果作为轻量 source 注册到 `sources.jsonl`，不保存全文。

返回中加入 source_id：

```text
1. 标题
   source_id: src_ab12cd
   URL: ...
   摘要: ...
```

Researcher 后续调用 `web_fetch(url)` 时，source registry 应能用 canonical URL 合并记录，而不是创建重复 source。

### 4.8 修改 `search_openalex` / `search_crossref`

为每篇论文注册 source：

- `source_type = "paper"`
- `doi` 字段必须填入，如果有。
- `published_at` 使用年份或完整日期。
- `title`、`authors` 尽量填入。
- 如果有摘要，保存到 source text。

返回格式加入 source_id：

```text
1. Paper Title
   source_id: src_paper_abc123
   DOI: ...
   URL: ...
   Year: ...
   摘要: ...
```

### 4.9 P1 验收

执行：

```bash
python run_test.py "测试：检索一篇 Transformer 相关论文并总结" --short-thinking --run-id smoke_p1
```

检查：

```bash
ls runs/smoke_p1/sources
cat runs/smoke_p1/state/sources.jsonl | head
cat runs/smoke_p1/state/events.jsonl | grep source_registered | head
```

必须满足：

- 至少一个 `src_*.txt` 文件被创建。
- `sources.jsonl` 中有对应记录。
- 工具返回中出现 `source_id`。
- `web_fetch` 不再把超长全文直接返回到模型上下文。
- 旧报告生成逻辑不崩溃。

---

## 5. P1.5：模型路由与 Prompt Cache 友好化

### 5.1 目标

降低成本和延迟，同时保持质量。

### 5.2 修改 `config.py`

将单一 `AGENT_MODEL` 拆成角色模型：

```python
# ── 模型路由 ──
SUPERVISOR_MODEL = "deepseek-v4-pro"
RESEARCHER_MODEL = "deepseek-v4-flash"  # 可按质量需求改为 pro
CRITIC_MODEL = "deepseek-v4-pro"
VERIFIER_MODEL = "deepseek-v4-pro"
SUMMARIZE_MODEL = "deepseek-v4-flash"
DEFAULT_AGENT_MODEL = SUPERVISOR_MODEL

# ── 推理深度 ──
REASONING_EFFORT_SUPERVISOR = "max"
REASONING_EFFORT_RESEARCHER = "high"
REASONING_EFFORT_CRITIC = "max"
REASONING_EFFORT_VERIFIER = "max"
```

保留旧 `AGENT_MODEL` 兼容：

```python
AGENT_MODEL = DEFAULT_AGENT_MODEL
```

### 5.3 修改 `model_factory.py`

角色到模型映射：

```python
def _model_for_role(role: str) -> str:
    return {
        "supervisor": cfg.SUPERVISOR_MODEL,
        "researcher": cfg.RESEARCHER_MODEL,
        "critic": cfg.CRITIC_MODEL,
        "verifier": cfg.VERIFIER_MODEL,
        "summarizer": cfg.SUMMARIZE_MODEL,
    }.get(role, cfg.DEFAULT_AGENT_MODEL)
```

`make_chat_model()` 使用 role model，而不是统一 `cfg.AGENT_MODEL`。

### 5.4 Prompt Cache 友好化

DeepSeek context cache 对“相同前缀”更友好。因此：

- 不要把 `topic`、`run_id`、当前时间、随机内容放在 system prompt 前部。
- system prompt 的固定规则尽量保持稳定。
- 动态参数集中放到 prompt 末尾。
- `SUPERVISOR_PROMPT` / `RESEARCHER_PROMPT` 中的固定规则不要频繁变动。

建议把 Supervisor prompt 拆成：

```python
SUPERVISOR_PROMPT_STATIC = """
固定角色、铁律、阶段、工具规则、引用规则...
"""

SUPERVISOR_PROMPT_DYNAMIC = """
本次运行配置：
- max_researchers: {max_researchers}
- search_limit: {search_limit}
- critic_enabled: {critic_enabled}
- hitl_enabled: {hitl_enabled}
- time_constraint: {time_constraint}
"""

SUPERVISOR_PROMPT = SUPERVISOR_PROMPT_STATIC + "\n\n" + SUPERVISOR_PROMPT_DYNAMIC
```

### 5.5 Prompt 内容更新

给 Supervisor 添加规则：

```text
所有引用来源优先使用 source_id。不要把长网页正文复制到报告中。
如果工具返回 saved_to 路径，说明全文已保存。需要核验时读取该文件。
每个核心结论必须能追溯到 source_id。
```

给 Researcher 添加规则：

```text
工具返回 source_id 后，你的最终输出必须在关键来源中保留 source_id。
如果 web_fetch 返回 saved_to，请不要要求再次抓取同一 URL。
当工具提示上下文软限制触发时，立即收敛研究并返回结构化发现。
```

### 5.6 P1.5 验收

执行：

```bash
python run_test.py "测试：简述 RAG 混合检索" --short-thinking --run-id smoke_p15 --debug
```

检查日志：

- Supervisor 使用 `SUPERVISOR_MODEL`。
- Researcher 使用 `RESEARCHER_MODEL`。
- Summarizer 使用 `SUMMARIZE_MODEL`。
- Prompt 不因 run_id/topic 改变而破坏固定前缀结构。

---

## 6. P2：Claim Ledger 与事实验证器

### 6.1 目标

把 Critic 从“泛泛审稿”升级为“结构审查 + 事实核验”。

最终报告中的关键论断必须能追溯到来源，并被验证器标记为：

```text
SUPPORTED
PARTIAL
UNSUPPORTED
CONTRADICTED
NOT_CHECKED
```

### 6.2 Claim Ledger schema

`claims.jsonl` 每行结构：

```json
{
  "claim_id": "claim_000001",
  "run_id": "smoke_p2",
  "section": "3.2",
  "claim": "BGE-M3 混合检索结合 dense 与 sparse 信号，可提升语义召回和关键词匹配能力。",
  "source_ids": ["src_000012", "src_000013"],
  "importance": "high",
  "created_by": "supervisor",
  "verification_status": "NOT_CHECKED",
  "notes": ""
}
```

### 6.3 Verification Ledger schema

`verification.jsonl` 每行结构：

```json
{
  "claim_id": "claim_000001",
  "run_id": "smoke_p2",
  "status": "SUPPORTED",
  "checked_at": "2026-06-06T11:00:00+03:00",
  "evidence": [
    {
      "source_id": "src_000012",
      "supports": true,
      "quote_or_summary": "来源明确说明 BGE-M3 提供 dense、lexical、multi-vector 能力。"
    }
  ],
  "reasoning_summary": "该 claim 被来源支持，但报告中应避免夸大为所有任务都提升。",
  "recommended_action": "keep"
}
```

### 6.4 新增 `deep_research/claim_verifier.py`

职责：

1. 从 `report.md` 中抽取候选 claims。
2. 尽量识别 claim 对应引用或 source_id。
3. 读取相关 source 文件。
4. 调用 verifier model 判断支持程度。
5. 写入 `claims.jsonl` 和 `verification.jsonl`。
6. 生成 `verification_summary.md`。

建议接口：

```python
def extract_claims_from_report(report_path: Path) -> list[dict]:
    """Extract high-value factual claims from report."""
    ...


def verify_claim(claim: dict) -> dict:
    """Use source files to verify one claim."""
    ...


def verify_report(run_id: str | None = None, min_importance: str = "medium") -> dict:
    """Verify report claims for current or specified run."""
    ...
```

### 6.5 Claim 抽取策略

第一阶段不要追求完美 NLP。采用混合方式：

1. Supervisor Prompt 要求写报告时同步维护 `/state/claims.jsonl`。
2. `claim_verifier.py` 再从 `report.md` 中补充抽取明显的事实性句子。
3. 如果找不到 source_id，标记为 `NOT_CHECKED` 或 `UNSUPPORTED`，并建议补来源。

可抽取的 claim 类型：

- 技术事实
- 性能结论
- 年份/版本/发布日期
- 架构对比
- 某论文/官方文档的结论
- “A 比 B 更...”这类比较性判断

不需要验证的内容：

- 纯过渡句
- 作者自己的建议
- 明确标注为推测的内容
- 摘要中的概括性重复，如果正文已经验证

### 6.6 Verifier Prompt

新增 verifier prompt，建议放入 `prompts.py`：

```text
你是事实核验 Agent。你只根据提供的 source 文件内容判断 claim 是否被支持。

规则：
1. 不允许使用你自己的常识补全证据。
2. 不允许因为 claim 看起来合理就判定 SUPPORTED。
3. 如果来源只支持部分内容，判定 PARTIAL。
4. 如果来源与 claim 相反，判定 CONTRADICTED。
5. 如果来源没有相关内容，判定 UNSUPPORTED。
6. 输出必须是 JSON，不要写额外解释。

输入：
- claim_id
- claim
- source records
- source excerpts or full source text

输出 JSON：
{
  "claim_id": "...",
  "status": "SUPPORTED|PARTIAL|UNSUPPORTED|CONTRADICTED",
  "evidence": [
    {"source_id": "...", "supports": true, "quote_or_summary": "..."}
  ],
  "reasoning_summary": "...",
  "recommended_action": "keep|revise|remove|needs_more_sources"
}
```

### 6.7 CLI 集成

`run_test.py` 新增参数：

```python
parser.add_argument("--verify-report", action="store_true")
parser.add_argument("--skip-verification", action="store_true")
```

默认策略建议：

- `--short-thinking` 默认不跑完整 verification，只生成 claims。
- `--long-thinking` 或 `--enable-critic` 时默认跑 high-importance claims 验证。
- `--verify-report` 强制跑验证。

### 6.8 报告输出策略

如果 verification 发现问题：

- `UNSUPPORTED` 的高重要性 claim 不应进入摘要和结论。
- `PARTIAL` claim 应修改措辞，降低强度。
- `CONTRADICTED` claim 必须删除或明确写成来源冲突。
- 最终报告末尾可选添加“验证摘要”。

### 6.9 P2 验收

执行：

```bash
python run_test.py "测试：比较 dense retrieval 与 sparse retrieval" --short-thinking --verify-report --run-id smoke_p2
```

检查：

```bash
cat runs/smoke_p2/state/claims.jsonl | head
cat runs/smoke_p2/state/verification.jsonl | head
ls runs/smoke_p2/workspace | grep verification
```

必须满足：

- `claims.jsonl` 至少有 3 个 claim。
- 每个 claim 有 `claim_id`、`claim`、`source_ids`、`verification_status`。
- `verification.jsonl` 至少有一个 `SUPPORTED / PARTIAL / UNSUPPORTED / CONTRADICTED`。
- 验证失败不应导致整个研究崩溃，应记录 warning。

---

## 7. P2.5：测试与回归保护

### 7.1 目标

避免后续改造破坏旧功能。

### 7.2 新增测试目录

建议：

```text
tests/
├── test_runtime_state.py
├── test_source_registry.py
├── test_tool_offload.py
├── test_claim_verifier.py
├── test_config_dynamic.py
└── test_resume_smoke.py
```

### 7.3 单元测试要求

#### `test_runtime_state.py`

覆盖：

- `init_run()` 创建目录。
- `resume=True` 不删除文件。
- `save_progress()` 原子写。
- `record_event()` 追加 JSONL。

#### `test_source_registry.py`

覆盖：

- URL canonicalization 去掉 `utm_*`。
- 同一 URL 重复注册不会生成大量重复全文文件。
- DOI 优先作为去重依据。
- source text 能保存到 sources 目录。

#### `test_tool_offload.py`

覆盖：

- 模拟大 HTML，`web_fetch` 返回不超过 inline limit。
- 全文保存到 sources。
- 返回中包含 `source_id` 和 `saved_to`。

#### `test_claim_verifier.py`

覆盖：

- 给定 claim 和 source text，mock LLM 返回 SUPPORTED。
- Verifier 能写 verification ledger。
- 缺来源时标记 NOT_CHECKED 或 UNSUPPORTED。

#### `test_config_dynamic.py`

覆盖：

- 修改 `cfg.RESEARCHER_MODEL` 后 `make_chat_model("researcher")` 能读到新值。
- 不允许模块 import 时捕获旧配置。

### 7.4 Smoke Test

新增脚本：

```bash
scripts/smoke_test.sh
```

内容建议：

```bash
#!/usr/bin/env bash
set -euo pipefail

python run_test.py "Smoke test: summarize retrieval augmented generation" \
  --short-thinking \
  --run-id smoke_ci

test -f runs/smoke_ci/state/research_progress.json
test -f runs/smoke_ci/state/events.jsonl
test -d runs/smoke_ci/workspace
```

### 7.5 P2.5 验收

执行：

```bash
pytest -q
bash scripts/smoke_test.sh
```

最低要求：

- 单元测试通过。
- smoke test 能完成或明确记录 failed。
- failed 时不能静默吞错。

---

## 8. P3：DeepAgents 新版迁移 Spike

### 8.1 目标

验证是否值得升级到 DeepAgents 新版本，尤其是以下能力：

- `CompositeBackend`
- `StoreBackend`
- `SummarizationMiddleware`
- Large Tool Result Eviction
- PatchToolCallsMiddleware

### 8.2 执行方式

不要直接改主分支。新建分支：

```bash
git checkout -b spike/deepagents-v2-backend
```

只做最小可行验证，不要和 P0/P1/P2 混在一起。

### 8.3 Spike 验收任务

跑通最小任务：

```bash
python run_test.py "测试 DeepAgents 新 backend 是否兼容" --short-thinking --run-id spike_da2
```

必须验证：

1. `write_todos` 正常。
2. `task()` 子代理正常。
3. Researcher 能写 `/notes/`。
4. Supervisor 能读 notes 并写 `report.md`。
5. SSE 日志仍能解析阶段。
6. run state 不被新 backend 破坏。

### 8.4 迁移决策

Spike 完成后输出：

```text
runs/spike_da2/workspace/deepagents_migration_report.md
```

内容包括：

- 哪些 API 变了。
- 哪些现有逻辑需要改。
- 是否值得迁移。
- 迁移风险。
- 推荐迁移路径。

---

## 9. P3：Web UI 增强

### 9.1 目标

让前端能展示 run 状态、恢复历史任务、下载指定 run 的报告。

### 9.2 后端 API

新增：

```text
GET  /api/runs
GET  /api/runs/<run_id>
POST /api/resume/<run_id>
GET  /api/download/<run_id>/<filename>
GET  /api/sources/<run_id>
GET  /api/claims/<run_id>
```

### 9.3 前端功能

最低功能：

- 显示当前 `run_id`。
- 显示阶段状态：planning / researching / report_drafting / verification / completed。
- 下载 latest run 报告。
- 列出最近 runs。
- 点击历史 run 可查看 report / events / sources / claims。

高级功能可以后续做，不要影响主线。

---

## 10. Prompt 修改摘要

### 10.1 Supervisor Prompt 新增规则

添加到固定规则区后半段，避免破坏前缀缓存：

```text
来源追踪规则：
1. 所有关键事实必须追溯到 source_id。
2. Researcher 返回的 source_id 必须保留在 notes 和 report drafting 依据中。
3. 不要将长网页正文复制到 report；只使用必要摘要和引用编号。
4. 如果工具返回 saved_to，说明全文已保存，需要核验时读取该路径。
5. 写报告时，尽量为关键论断维护 claim 记录，包括 claim、section、source_ids、importance。

上下文控制规则：
1. 当工具提示上下文软限制触发时，不要继续扩展搜索，应先整理 notes。
2. 当工具提示上下文硬限制触发时，立即停止搜索，基于已有材料返回结果。
```

### 10.2 Researcher Prompt 新增规则

```text
source_id 使用规则：
1. 每条关键发现后必须附 source_id 或 DOI/URL。
2. 如果工具返回 source_id，不要丢弃。
3. 如果同一 URL 已有 source_id，不要重复抓取。
4. 最终输出的 [关键来源] 必须包含 source_id。

上下文预算规则：
1. 工具提示软限制后，最多再做 1 次必要搜索。
2. 工具提示硬限制后，禁止继续搜索，立即返回结构化发现。
```

### 10.3 Critic Prompt 新增规则

```text
你是结构与质量审查者，不是事实核验者。
你可以指出哪些 claim 需要验证，但不要声称某事实已经被证明。
事实支持状态以后续 Claim Verifier 为准。
```

### 10.4 Verifier Prompt 新增

见第 6.6 节。

---

## 11. 推荐提交顺序

### Commit 1：runtime_state 基础设施

包含：

- `runtime_state.py`
- `config.py` 新增 run 配置
- `run_test.py` 初始化 run
- `agent.py` 使用 run workspace

验收：P0 基础目录和 progress 生成。

### Commit 2：事件日志接入

包含：

- tool call / tool result event
- phase_changed event
- run_completed / run_failed event

验收：`events.jsonl` 可追踪一次完整运行。

### Commit 3：source_registry

包含：

- `source_registry.py`
- URL canonicalization
- source_id
- sources.jsonl
- source text 保存

验收：source 注册单测通过。

### Commit 4：web_fetch offload

包含：

- `web_fetch` 保存全文
- 返回 source_id + saved_to + snippet
- 上下文输出预算

验收：大网页不直接进入上下文。

### Commit 5：搜索工具 source_id 化

包含：

- `web_search` 返回 source_id
- `search_openalex` 返回 source_id
- `search_crossref` 返回 source_id

验收：Researcher 输出中出现 source_id。

### Commit 6：模型路由

包含：

- `SUPERVISOR_MODEL` 等配置
- `model_factory.py` role model map
- CLI 如需支持则添加参数

验收：debug 日志能看到不同角色模型。

### Commit 7：Prompt 更新

包含：

- source_id 规则
- 上下文预算规则
- claim 规则
- cache-friendly prompt 拆分

验收：旧任务仍可跑通。

### Commit 8：claim_verifier

包含：

- `claim_verifier.py`
- `claims.jsonl`
- `verification.jsonl`
- `--verify-report`

验收：P2 smoke test。

### Commit 9：测试与 smoke script

包含：

- `tests/`
- `scripts/smoke_test.sh`

验收：`pytest -q` 通过。

### Commit 10：Web API 最小增强

包含：

- `/api/runs`
- `/api/download/<run_id>/<filename>`
- latest run 下载兼容

验收：前端旧功能不坏。

---

## 12. 不要做的事

本次改造禁止：

1. 不要删除旧 `workspace/` 兼容逻辑。
2. 不要把所有模块重写成类，除非必要。
3. 不要把 source registry 和 Chroma knowledge base 混成一个系统；前者是证据账本，后者是历史检索。
4. 不要让 Verifier 使用互联网搜索；Verifier 只能看已保存 sources。
5. 不要让 Critic 直接改 report；Critic 输出建议，Supervisor 或后处理逻辑负责修改。
6. 不要在没有测试的情况下升级 DeepAgents 主版本。
7. 不要在 `config.py` 外散落硬编码路径。
8. 不要让 `web_fetch` 再返回几万字符正文。
9. 不要让 `--resume` 清空已有 run。
10. 不要把所有失败吞掉。失败必须写入 `research_progress.json.errors` 和 `events.jsonl`。

---

## 13. 最终验收标准

完成 P0-P2.5 后，系统应满足：

### 13.1 状态与恢复

- 每次运行都有独立 `runs/<run_id>/`。
- 中断后可通过 `--resume <run_id>` 继续或至少不破坏已有材料。
- `research_progress.json` 能显示当前阶段和状态。
- `events.jsonl` 能重建主要执行时间线。

### 13.2 上下文控制

- 大网页正文保存到 `/sources/`。
- 工具返回中只包含 snippet、source_id、saved_to。
- 每个 researcher 有累计工具输出预算。
- 超限后工具会强制收敛搜索行为。

### 13.3 来源追踪

- `sources.jsonl` 记录所有重要来源。
- OpenAlex / Crossref / web_search / web_fetch 都能产生 source_id。
- 同一 DOI / canonical URL 不会大量重复。

### 13.4 事实验证

- `claims.jsonl` 记录关键论断。
- `verification.jsonl` 记录验证结果。
- 高重要性 unsupported claim 不应进入最终摘要和结论。

### 13.5 兼容性

- 旧命令 `python run_test.py "topic"` 仍可运行。
- Web UI 下载 report 不坏。
- history database 和 vector store 归档不坏。

---

## 14. 给 Claude Code 的第一条执行指令

请从 P0 开始实现，不要跳到 P2/P3。第一步只做运行状态层：

1. 新增 `deep_research/runtime_state.py`。
2. 修改 `config.py` 添加 run/state 配置。
3. 修改 `run_test.py` 支持 `--run-id`、`--resume`、`--list-runs`。
4. 修改 `agent.py`，让 `_prepare_workspace()` 使用当前 run 的 workspace，并确保 resume 时不删除已有文件。
5. 加入最小 `events.jsonl` 和 `research_progress.json`。
6. 跑通 P0 smoke test。

完成 P0 后停止，输出改动摘要、涉及文件、测试结果和下一阶段建议。

