# Deep Research Agent — 完整技术文档

> **版本**: V3.0 | **最后更新**: 2026-06-07 | **分支**: main
> **简短说明**: 基于 LangChain deepagents 的多智能体深度研究系统，Supervisor + Researcher × N + Critic + Verifier 协作完成 Web 调研并生成带引用的结构化报告。

---

## 目录

1. [项目概述](#1-项目概述)
2. [系统架构](#2-系统架构)
3. [Agent 角色体系](#3-agent-角色体系)
4. [数据流与上下文隔离](#4-数据流与上下文隔离)
5. [模块详解](#5-模块详解)
6. [配置系统](#6-配置系统)
7. [工具系统](#7-工具系统)
8. [搜索质量管线](#8-搜索质量管线)
9. [Web 服务](#9-web-服务)
10. [前端 UI](#10-前端-ui)
11. [命令行用法](#11-命令行用法)
12. [目录结构](#12-目录结构)
13. [扩展点](#13-扩展点)

---

## 1. 项目概述

### 1.1 核心思想

普通 Agent 做长程研究时会遇到三个问题：
- **不会规划** → 想到哪搜到哪，维度遗漏
- **上下文爆炸** → 原始搜索结果塞满 context window
- **无法纵深** → 一个线程深入时丢失其他线程的发现

本系统的解决方案——四项 LangChain deepagents 内置原语：

| 原语 | 实现 | 解决的问题 |
|------|------|-----------|
| **Planning** | `write_todos` | 防止乱搜，MECE 分解 |
| **Context Offloading** | 虚拟文件系统 `/notes/` `/report.md` | 上下文不膨胀 |
| **Delegation** | `task()` → sub-agents | 独立上下文窗口，隔离搜索噪音 |
| **Memory** | RAG 向量知识库 + Skills | 跨 run 积累，技能按需加载 |

### 1.2 技术栈

| 层 | 技术 |
|----|------|
| Agent 框架 | LangChain `deepagents` (create_deep_agent) |
| 编排 | LangGraph (StateGraph, recursion_limit=250) |
| 模型 | DeepSeek V4 Pro (OpenAI 兼容 API) |
| 搜索引擎 | DuckDuckGo (`ddgs` 库), 免费无需 API key |
| 学术搜索 | OpenAlex API + Crossref API |
| 重排 | BAAI/bge-reranker-v2-m3 (本地 Cross-Encoder, ~300MB) |
| 向量库 | BGE-M3 + Chroma (本地持久化, ~1.2GB) |
| 正文抽取 | trafilatura → readability-lxml → regex (三级降级) |
| 后端 | Flask + SSE (Server-Sent Events) 实时推流 |
| 前端 | Vue 3 + Vite + highlight.js |
| 报告生成 | python-docx (确定性转换, agent 循环外) |

---

## 2. 系统架构

### 2.1 整体拓扑

```
┌─────────────────────────────────────────────────────────────┐
│  run_test.py / server.py  (入口层)                          │
│  CLI 解析 → init_run() → set_research_timeout()             │
│         → create_supervisor_agent() → agent.stream()        │
│         → convert_report() → archive_summary()              │
└──────────────┬──────────────────────────────────────────────┘
               │
┌──────────────▼──────────────────────────────────────────────┐
│  agent.py  (装配层)                                          │
│  create_supervisor_agent()                                   │
│  ├─ _prepare_workspace()    清空/恢复 workspace              │
│  ├─ make_chat_model()       创建 LLM 实例                    │
│  ├─ _create_backend()       FilesystemBackend                │
│  ├─ _load_skills()          读取 skills/                     │
│  ├─ create_researcher_subagents()  → researcher-1/2/3...     │
│  ├─ create_critic_subagent()       → critic (可选)           │
│  └─ _build_agent() → create_deep_agent()                     │
└──────────────┬──────────────────────────────────────────────┘
               │
┌──────────────▼──────────────────────────────────────────────┐
│  Supervisor (LangGraph Agent)                                │
│  System Prompt = SUPERVISOR_PROMPT                           │
│  Tools: write_todos, write_file, read_file, ls               │
│         + request_plan_approval (HITL 可选)                  │
│  Sub-agents:                                                 │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐       │
│  │ researcher-1 │  │ researcher-2 │  │ researcher-3 │       │
│  │ web_search   │  │ web_search   │  │ web_search   │       │
│  │ web_fetch    │  │ web_fetch    │  │ web_fetch    │       │
│  │ openalex     │  │ openalex     │  │ openalex     │       │
│  │ crossref     │  │ crossref     │  │ crossref     │       │
│  │ kb_search    │  │ kb_search    │  │ kb_search    │       │
│  └──────────────┘  └──────────────┘  └──────────────┘       │
│  ┌──────────────┐                                            │
│  │ critic (可选) │  只读文件, 不搜索                          │
│  └──────────────┘                                            │
└─────────────────────────────────────────────────────────────┘
```

### 2.2 运行流程（7 阶段）

| 阶段 | 动作 | 谁做 |
|------|------|------|
| 1. 计划 | `write_todos` + MECE 分解 + 任务简报 | Supervisor |
| 2. 审批 | `request_plan_approval` (HITL, 可选) | Supervisor ↔ 用户 |
| 3. 委托 | 并行 `task()` 派发 N 个 researcher | Supervisor |
| 4. 归档 | researcher 结果 → `/notes/*.md` + 查漏补缺 | Supervisor |
| 5. 撰写 | 分 4 节增量写入 `/report.md` | Supervisor |
| 6. 反思 | task("critic") → 补研究 → 修订 (最多3轮, 可选) | Supervisor+Critic |
| 7. 自评 | 自评弱点 + `/research_summary.txt` + 归档 | Supervisor |

### 2.3 三级努力度

| 模式 | CLI 参数 | 搜索上限 | 时间限制 | Critic | Verifier | 推理档 |
|------|----------|---------|---------|--------|----------|-------|
| **Fast** | `--short-thinking` | 5 次 | 5 分钟 | ❌ | ❌ | high |
| **Deep** | (默认) | 20 次 | 无 | ❌ | ❌ | max |
| **Max** | `--long-thinking --enable-critic` | 20 次 | 无 | ✅ 3轮 | ✅ | max |

---

## 3. Agent 角色体系

共 **5 种角色**，4 个在 Agent 循环内 + 1 个在 Python 编排层：

### 3.1 Agent 循环内（LangGraph Sub-Agents）

#### Supervisor (研究总监)
- **模型**: `deepseek-v4-pro`, reasoning_effort=`max`
- **工具**: `write_todos`, `task`, `write_file`, `read_file`, `ls`, `request_plan_approval`
- **职责**: 规划→分配→质量把关→成文。**禁止自己搜索**
- **Prompt**: `prompts.py` → `SUPERVISOR_PROMPT` (STATIC + DYNAMIC 拆分)

#### Researcher × N (研究员)
- **模型**: `deepseek-v4-pro`, reasoning_effort=`high` (不设 max 防止并发限流)
- **数量**: 由 Supervisor 动态决定 1~5 个（`SUBAGENT_MAX_CONCURRENCY`）
- **工具**: `web_search`, `web_fetch`, `search_openalex`, `search_crossref`, `search_knowledge_base`
- **硬约束**:
  - 每 researcher 最多 N 次搜索（代码层拦截，`RESEARCHER_SEARCH_LIMIT`）
  - 搜索去重（按 researcher 隔离的 query hash 缓存）
  - 上下文输出预算：软限制 18K 字符 / 硬限制 30K 字符
  - 可选的全局时限（`RESEARCH_TIMEOUT_MINUTES`）
- **Prompt**: `prompts.py` → `RESEARCHER_PROMPT` (OODA 循环)

#### Critic (批判审查员, 仅 max 模式)
- **模型**: `deepseek-v4-pro`, reasoning_effort=`max`
- **工具**: 无（只有 FilesystemMiddleware 注入的 `read_file` / `ls`）
- **职责**: 结构+质量审查，输出 `[CRITIC_REPORT]` 含评分和 `REQUIRES_REWORK`
- **重要**: Critic 是结构审查者，不是事实核验者——事实验证留给 Verifier
- **Prompt**: `prompts.py` → `CRITIC_PROMPT`

### 3.2 Python 编排层

#### Claim Verifier (事实核验, 仅 max 模式)
- **模型**: `deepseek-v4-pro`, reasoning_effort=`max`
- **执行时机**: Critic 循环完成后，由 `run_test.py` 调用 `claim_verifier.py`
- **输入**: 从 `report.md` 抽取 claims + 读取 `/sources/` 原始文件
- **输出**: 每条 claim → `SUPPORTED | PARTIAL | UNSUPPORTED | CONTRADICTED`
- **文件**: `claims.jsonl`, `verification.jsonl`, `verification_summary.md`

#### Summarizer (浓缩归档)
- **模型**: `deepseek-v4-pro`
- **执行时机**: 研究完成后
- **职责**: 将研究摘要分类 + 浓缩，写入知识库供后续 RAG 检索

---

## 4. 数据流与上下文隔离

### 4.1 隔离机制

```
每个 researcher 有独立 LangGraph 上下文窗口
         │
         │  raw search output stays HERE (not in supervisor)
         ▼
    ┌─────────┐
    │  res-1  │ → 返回结构化摘要 (核心发现 + 来源 + 自评)
    └─────────┘
    ┌─────────┐
    │  res-2  │ → 返回结构化摘要
    └─────────┘
         │
         ▼
    Supervisor 写入 /notes/*.md → 读 notes → 写 /report.md
```

### 4.2 信息归档路径

```
web_search / web_fetch
  │
  ├─ 轻量摘要 (≤1200 字符) → 返回给 Agent（含 source_id）
  └─ 全文 → 保存到 /sources/<source_id>.txt
       │
       ▼
  Claim Verifier → 读取 /sources/ → 核验 /report.md 中的 claims
```

### 4.3 Run 目录结构

每次研究生成独立目录，支持断点恢复和事后审查：

```
runs/<YYYYMMDD_HHMMSS>/
├── workspace/          ← 该次研究的独立虚拟文件系统
│   ├── notes/          ← 研究员返回归档
│   ├── skills/         ← 技能文件副本
│   ├── report.md       ← 最终报告
│   └── research_summary.txt
├── sources/            ← 抓取网页/论文全文
│   └── src_xxxxxx.txt
└── state/
    ├── events.jsonl            ← 事件流
    ├── research_progress.json  ← 阶段/进度
    ├── sources.jsonl           ← 来源账本
    ├── claims.jsonl            ← 论断账本
    └── verification.jsonl      ← 验证结果
```

---

## 5. 模块详解

### 5.1 核心模块一览

| 模块 | 文件 | 行数 | 职责 |
|------|------|------|------|
| **config** | `config.py` | 165 | 所有可调参数集中配置 |
| **agent** | `agent.py` | 194 | Supervisor agent 装配 |
| **prompts** | `prompts.py` | 437 | 全部 System Prompt |
| **tools** | `tools.py` | ~700 | 5 个搜索工具 + 预算/去重/上下文追踪 |
| **subagents** | `subagents.py` | 72 | Researcher + Critic 子智能体定义 |
| **model_factory** | `model_factory.py` | 81 | 按角色创建 LLM，含并发限流 |
| **rerank** | `rerank.py` | 53 | Cross-encoder 重排管线 |
| **report** | `report.py` | ~200 | Markdown → .docx 确定性转换 |
| **summarizer** | `summarizer.py` | ~150 | LLM 驱动的摘要分类+浓缩 |
| **knowledge_base** | `knowledge_base.py` | ~400 | Chroma 向量库, 混合检索+上下文检索 |
| **source_registry** | `source_registry.py` | ~200 | URL 规范化, source_id 生成, 全文保存 |
| **claim_verifier** | `claim_verifier.py` | ~300 | 事实核验管线 |
| **runtime_state** | `runtime_state.py` | ~200 | Run 生命周期, 进度跟踪, 事件日志 |
| **server** | `server.py` | 288 | Flask SSE 桥接服务 |
| **run_test** | `run_test.py` | ~500 | CLI 入口 + Agent 流式监控 |

### 5.2 model_factory.py — 模型工厂

```python
# 关键设计：全局信号量限制并发 API 调用
_API_SEMAPHORE = threading.Semaphore(3)

def make_chat_model(role: str) -> BaseChatModel:
    # role → 模型名映射
    "supervisor" → SUPERVISOR_MODEL
    "researcher" → RESEARCHER_MODEL
    "critic"     → CRITIC_MODEL
    "verifier"   → VERIFIER_MODEL
    "summarizer" → SUMMARIZE_MODEL

    # role → reasoning_effort 映射
    "supervisor" → "max"
    "researcher" → "high"    # 永远不设 max——并发多了会触发 API 限流
    "critic"     → "max"
    "verifier"   → "max"

    # _RateLimitedChatOpenAI: 透明地在 invoke 前获取信号量
```

### 5.3 prompts.py — 提示词体系

采用 **STATIC/DYNAMIC 拆分**策略，STATIC 部分固定不变享受 LLM 前缀缓存：

| Prompt | 用途 | 注入条件 |
|--------|------|---------|
| `SUPERVISOR_PROMPT_STATIC` | 核心编排规则 | 始终 |
| `SUPERVISOR_PROMPT_DYNAMIC` | 运行配置（数量/限制/开关） | 始终 |
| `RESEARCHER_PROMPT` | OODA 循环 + 预算 + 输出格式 | 始终 |
| `HITL_INSTRUCTIONS` | 计划审批 | `INTERACTIVE_PLAN_APPROVAL=True` |
| `CRITIC_INSTRUCTIONS` | 反思循环规则 | `CRITIC_ENABLED=True` |
| `CRITIC_PROMPT` | Critic 审查 SOP | `CRITIC_ENABLED=True` |
| `VERIFIER_PROMPT` | 事实核验 SOP | max 模式的 claim_verifier |

### 5.4 runtime_state.py — 运行状态层

```python
@dataclass
class RunContext:
    run_id: str
    topic: str | None
    run_dir: Path            # runs/<run_id>/
    workspace_dir: Path      # runs/<run_id>/workspace/
    sources_dir: Path        # runs/<run_id>/sources/
    state_dir: Path          # runs/<run_id>/state/
    resumed: bool

# 核心 API
init_run(topic, run_id, resume) → RunContext
get_run()                       → RunContext (当前)
record_event(type, data)        → 追加到 events.jsonl
save_progress(data)             → 写入 research_progress.json
load_progress(run_id?)          → 读取进度
list_runs()                     → 列出所有 run
append_jsonl(path, record)      → 原子追加到账本
```

### 5.5 source_registry.py — 来源注册表

每个网页/论文注册为 `SourceRecord`，提供：

- **URL 规范化**: 去跟踪参数 (`utm_*`, `fbclid` 等), 去 fragment, 标准化 hostname
- **source_id 生成**: `src_<8-char-hash>` 基于规范化 URL 的 SHA-256
- **去重**: 同 URL 不重复注册，返回已有 source_id
- **全文保存**: 网页/论文正文存到 `/sources/<source_id>.txt`
- **轻量返回**: 工具返回给 Agent 时只含 `source_id + snippet`，不污染上下文

### 5.6 knowledge_base.py — 向量知识库

```
历史研究摘要
     │
     ▼
Summarizer LLM 生成 context header → 分块
     │
     ├─ BGE-M3 FlagEmbedding  → dense + sparse + colbert
     ├─ sentence-transformers → dense embedding
     └─ Chroma 持久化        → vector-store/
     │
     ▼
检索时 (混合检索):
  1. dense recall top-20
  2. sparse (lexical_weights) 召回
  3. RRF (Reciprocal Rank Fusion) 融合
  4. cross-encoder 重排 → top-3
  5. 父文档去重（同归档多 chunk 只保留最高排名）
```

---

## 6. 配置系统

### 6.1 导入模式（重要）

所有模块使用 `from . import config as cfg`，不直接从 config 导入值。这是因为 CLI 覆盖需要修改模块级属性（如 `cfg.RESEARCHER_SEARCH_LIMIT = 5`），如果用 `from .config import RESEARCHER_SEARCH_LIMIT` 会捕获导入时的值快照，CLI 覆盖失效。

### 6.2 关键配置项

#### 模型配置
```python
DEEPSEEK_API_KEY        # 优先级: 环境变量 > ../deepseek.txt
DEEPSEEK_BASE_URL       # "https://api.deepseek.com"
SUPERVISOR_MODEL        # "deepseek-v4-pro"
RESEARCHER_MODEL        # "deepseek-v4-pro"
CRITIC_MODEL            # "deepseek-v4-pro"
VERIFIER_MODEL          # "deepseek-v4-pro"
SUMMARIZE_MODEL         # "deepseek-v4-pro"
```

#### 搜索配置
```python
SEARCH_MAX_RESULTS = 10         # web_search 原始返回数（重排前）
FETCH_CHAR_LIMIT = 4000         # (deprecated) 旧截断值
FETCH_TIMEOUT = 15              # web_fetch 请求超时（秒）
RESEARCHER_SEARCH_LIMIT = 20    # 每 researcher 硬上限
COUNT_FAILED_SEARCHES = False   # 失败/空结果不计入预算 (deep/max)
RESEARCH_TIMEOUT_MINUTES = 0    # 全局时限, 0=不限
```

#### 上下文控制 (P1)
```python
WEB_FETCH_INLINE_CHAR_LIMIT = 1200     # 返回给 Agent 的最大字符
WEB_FETCH_FULLTEXT_SAVE = True         # 全文存 /sources/
TOOL_OUTPUT_SOFT_CHAR_LIMIT_PER_AGENT = 18000  # 软限制警告
TOOL_OUTPUT_HARD_CHAR_LIMIT_PER_AGENT = 30000  # 硬限制强制停止
ENABLE_SOURCE_REGISTRY = True          # source_id 追踪
```

#### 重排配置
```python
RERANK_ENABLED = True
RERANK_MODEL = "BAAI/bge-reranker-v2-m3"
RERANK_TOP_K = 4              # 重排后保留条数
```

#### 运行时配置
```python
RECURSION_LIMIT = 250         # LangGraph 步数上限
SUBAGENT_MAX_CONCURRENCY = 5  # 最大 researcher 数
THINKING_ENABLED = True
THINKING_MAX_OUTPUT_TOKENS = 16000
```

#### RAG 配置
```python
RAG_ENABLED = True
EMBEDDING_MODEL = "BAAI/bge-m3"
VECTOR_STORE_DIR = PROJECT_ROOT / "vector-store"
RAG_TOP_K = 3                 # 检索返回条数
HYBRID_RETRIEVAL_ENABLED = True
KB_RERANK_ENABLED = True
CONTEXTUAL_RETRIEVAL_ENABLED = True
```

#### Critic / HITL
```python
CRITIC_ENABLED = False        # --enable-critic 开启
CRITIC_MAX_ROUNDS = 3         # 最多 3 轮反思循环
INTERACTIVE_PLAN_APPROVAL = False  # --interactive-plan 开启
```

### 6.3 CLI 覆盖机制

```python
# run_test.py → apply_cli_to_config()
args = parse_cli_args()
apply_cli_to_config(args)

# --short-thinking 快捷开关
cfg.REASONING_EFFORT_SUPERVISOR = "high"
cfg.REASONING_EFFORT_RESEARCHER = "high"
cfg.RESEARCHER_SEARCH_LIMIT = 5
cfg.RESEARCH_TIMEOUT_MINUTES = 5
cfg.SUBAGENT_MAX_CONCURRENCY = 3
cfg.COUNT_FAILED_SEARCHES = True

# --long-thinking 快捷开关
cfg.REASONING_EFFORT_SUPERVISOR = "max"
cfg.REASONING_EFFORT_CRITIC = "max"
```

---

## 7. 工具系统

### 7.1 工具清单

| 工具 | 类型 | 使用者 | 说明 |
|------|------|--------|------|
| `web_search` | @tool | Researcher | DuckDuckGo 网页搜索，含 rerank + source 注册 |
| `web_fetch` | @tool | Researcher | 抓取网页全文，自动保存 /sources/ |
| `search_openalex` | @tool | Researcher | OpenAlex 学术搜索（2.4 亿+论文） |
| `search_crossref` | @tool | Researcher | Crossref 元数据搜索 |
| `search_knowledge_base` | @tool | Researcher | 本地 Chroma 历史研究检索（不计搜索预算） |
| `write_todos` | deepagents | Supervisor | 制定研究计划 |
| `write_file` | deepagents | Supervisor | 写入虚拟文件系统 |
| `read_file` | deepagents | Supervisor/Critic | 读取虚拟文件系统 |
| `ls` | deepagents | Supervisor/Critic | 列出虚拟目录 |
| `task` | deepagents | Supervisor | 派发子智能体任务 |
| `request_plan_approval` | @tool | Supervisor | HITL 计划审批 |

### 7.2 搜索预算控制

```python
# 每个 researcher 独立的模块级状态
_search_budget = {}     # {agent_name: count}
_search_cache = {}      # {agent_name: {query_hash: True}}
_research_start_time = None
_tool_output_chars = {} # {agent_name: total_chars}

# 搜索前的多重检查
def _check_search_budget(query):
    1. 时限检查     → 超时则返回 TIMEOUT_BLOCK_MSG
    2. 预算检查     → 耗尽则返回 BUDGET_EXCEEDED_MSG
    3. 去重检查     → 重复则返回 DUPLICATE_MSG (不计预算)
    → 全部通过: None

# 搜索成功后的提交
def _commit_search(query):
    → 标记去重缓存
    → 递增搜索计数
```

### 7.3 上下文预算控制

```python
def _track_tool_output(text):
    → 累计字符数
    → >=HARD_LIMIT: 追加强制停止消息
    → >=SOFT_LIMIT: 追加收敛警告消息
    → 返回原文本（可能附带警告）
```

---

## 8. 搜索质量管线

### 8.1 完整链路

```
用户输入课题
    │
    ▼
Supervisor MECE 分解 → 任务简报（含推荐工具优先级）
    │
    ▼
Researcher OODA 循环
    │
    ├─ Step 1: search_knowledge_base (查历史, 不计预算)
    │
    ├─ web_search(query)
    │   ├─ DDGS.text() → 10 条原始结果
    │   ├─ Cross-Encoder 重排 → 保留 top-4
    │   ├─ 每条注册 source_id
    │   └─ 返回轻量结果（≤18000 软限, ≤30000 硬限）
    │
    ├─ web_fetch(url)
    │   ├─ trafilatura 抽取正文
    │   ├─ (fallback) readability-lxml
    │   ├─ (fallback) regex HTML→text
    │   ├─ 全文保存 /sources/
    │   └─ 返回 source_id + snippet (≤1200 字符)
    │
    ├─ search_openalex(query)  → 学术论文
    ├─ search_crossref(query)  → 论文元数据
    │
    └─ 最终输出: [核心发现] + [关键来源] + [充分性自评]
```

### 8.2 三级正文抽取

```python
def _extract_main_content(html):
    1. trafilatura.extract()       # 最优：学术级正文+表格
    2. readability.Document()      # 降级：文章主体
    3. _html_to_text()             # 保底：正则去标签
```

### 8.3 去重策略

- **URL 规范化**: 去 `utm_*` 等追踪参数, 去 fragment, 标准化 hostname
- **搜索去重**: 按 researcher 隔离的 query hash 缓存（`query.strip().lower()`）
- **Source 去重**: URL 规范化后查重，同 URL 不重复注册

---

## 9. Web 服务

### 9.1 API 接口

| 端点 | 方法 | 说明 |
|------|------|------|
| `/` | GET | 前端 HTML |
| `/api/health` | GET | 健康检查 `{"status": "ok"}` |
| `/api/version` | GET | 版本信息（git commit + 文件 mtime） |
| `/api/research` | POST | 启动研究，返回 SSE 流 `{"topic", "effort"}` |
| `/api/stop` | POST | 终止所有运行中的任务 |
| `/api/runs` | GET | 列出所有 run |
| `/api/runs/<run_id>` | GET | 指定 run 的进度+文件 |
| `/api/resume/<run_id>` | POST | 恢复已有 run |
| `/api/download/<filename>` | GET | 下载 report.md / .docx / summary.txt |
| `/api/download/<run_id>/<filename>` | GET | 下载指定 run 的文件 |
| `/assets/*` | GET | 静态资源 |

### 9.2 SSE 事件格式

```javascript
// 事件流
data: {"type": "start", "task_id": "task_1", "run_id": "20260607_093000"}

data: {"type": "log", "data": "[00:01] >>> Agent 就绪，开始研究"}

data: {"type": "log", "data": "[00:05] 📋 Step 5 ..."}

data: {"type": "done", "exit_code": 0}

data: {"type": "closed"}
```

### 9.3 版本接口

```json
// GET /api/version
{
  "status": "ok",
  "git": {
    "full_hash": "bdaddaf...",
    "short_hash": "bdaddaf",
    "date": "2026-06-07 15:30:00 +0800",
    "message": "fix(agent): restore iron rules + hard time limit"
  },
  "file_mtimes": {
    "config.py": 1749285000,
    "prompts.py": 1749284950,
    "tools.py": 1749284900,
    "agent.py": 1749284850
  }
}
```

---

## 10. 前端 UI

### 10.1 技术栈

- Vue 3 (Composition API, `<script setup>`)
- Vite 6 (port 5173 dev, proxy `/api` → `localhost:5001`)
- vue-router 4
- highlight.js (代码高亮)
- tsparticles (粒子背景)

### 10.2 组件结构

```
App.vue
├── ParticleBg.vue               ← 粒子动画背景
└── <router-view>
    └── ResearchView.vue          ← 主视图
        ├── 输入区: topic + effort 选择 + 开始/终止按钮
        ├── 实时日志: SSE 流, 自动滚动, 变暗过滤
        └── 下载区: Markdown / Word / 摘要
```

### 10.3 Effort 选择器

```
⚡ 快速搜索   → fast:  5次搜索, 5分钟, high推理
🔬 深度检索   → deep:  20次搜索, 无限时, max推理 (推荐)
🧠 深度研究   → max:   20次搜索, 无限时, max推理 + Critic + Verifier
```

---

## 11. 命令行用法

### 11.1 基本命令

```bash
# 快速搜索（5次搜索, 5分钟时限）
python run_test.py "最近AI领域的重大突破" --short-thinking

# 深度检索（默认, 推荐）
python run_test.py "Transformer架构的演进与未来趋势"

# 深度研究（含 Critic + Verifier）
python run_test.py "量子计算对密码学的威胁" --long-thinking --enable-critic

# Manually set reasoning efforts
python run_test.py "topic" --reasoning-effort max

# 带计划审批
python run_test.py "topic" --interactive-plan

# 列出所有历史 run
python run_test.py --list-runs

# 恢复中断的 run
python run_test.py --resume            # 恢复 latest
python run_test.py --resume 20260607_093000   # 恢复指定 run
```

### 11.2 启动 Web 服务

```bash
# 生产模式：构建前端 + 启动 Flask (port 5001)
cd web && npm run build && cd ..
python server.py
# 打开 http://localhost:5001

# 开发模式：两个终端
# 终端 1: python server.py
# 终端 2: cd web && npm run dev
# 打开 http://localhost:5173
```

### 11.3 配置验证

```bash
python -c "from deep_research.config import *; print('OK', AGENT_MODEL, RERANK_ENABLED)"
```

---

## 12. 目录结构

```
self-project-agent/                       ← Git 仓库根
├── CLAUDE.md                             ← Claude Code 项目指南
├── deepseek.txt                          ← API key (不提交)
│
├── deep-research-agent/                  ← 项目主目录
│   ├── requirements.txt
│   ├── server.py                         ← Flask 桥接
│   ├── run_test.py                       ← CLI 入口
│   │
│   ├── deep_research/                    ← Python 包
│   │   ├── __init__.py
│   │   ├── config.py                     ← 全部可调参数
│   │   ├── agent.py                      ← Supervisor 装配
│   │   ├── prompts.py                    ← 全部 Prompt
│   │   ├── tools.py                      ← 搜索工具 + 预算控制
│   │   ├── subagents.py                  ← Researcher/Critic 定义
│   │   ├── model_factory.py              ← LLM 工厂 + 限流
│   │   ├── rerank.py                     ← Cross-encoder 重排
│   │   ├── report.py                     ← Markdown→docx
│   │   ├── summarizer.py                 ← 摘要分类+浓缩
│   │   ├── knowledge_base.py             ← Chroma 向量库
│   │   ├── source_registry.py            ← 来源注册表 (P1)
│   │   ├── claim_verifier.py             ← 事实核验 (P2)
│   │   ├── runtime_state.py              ← Run 状态管理
│   │   └── skills/                       ← 渐进式技能
│   │       ├── academic-report/SKILL.md  ← 报告结构规则
│   │       └── source-quality/SKILL.md   ← 来源可信度
│   │
│   ├── web/                              ← Vue 3 前端
│   │   ├── package.json
│   │   ├── vite.config.js               ← proxy /api → 5001
│   │   ├── index.html
│   │   ├── dist/                         ← 构建产物
│   │   └── src/
│   │       ├── App.vue                   ← 根组件 + 版本标签
│   │       ├── main.js
│   │       ├── style.css
│   │       ├── router.js
│   │       ├── api/research.js           ← API 调用
│   │       ├── components/ParticleBg.vue
│   │       └── views/ResearchView.vue    ← 主视图
│   │
│   ├── runs/                             ← 研究记录
│   │   └── <run_id>/
│   │       ├── workspace/
│   │       ├── sources/
│   │       └── state/
│   │
│   ├── workspace/                        ← 旧路径兼容
│   ├── vector-store/                     ← Chroma 持久化
│   └── tests/                            ← 测试
│
└── .claude/                              ← Claude Code 配置
    └── settings.json
```

---

## 13. 扩展点

按 BUILD_GUIDE Step 8 定义，以下方向可直接扩展：

| 扩展 | 实现位置 | 难度 | 说明 |
|------|---------|------|------|
| **LangGraph Store 记忆** | `agent.py` | 中 | 跨 run 持久化 briefs/reports |
| **上下文摘要** | `agent.py` | 中 | 超长 run 时自动压缩历史 |
| **人机协同计划审批** | 已有 `request_plan_approval` | 低 | `--interactive-plan` 开启 |
| **并行委托** | 已有并行 `task()` | 低 | Supervisor prompt 已指示同消息多 task |
| **学术源 (arXiv)** | `tools.py` | 低 | 新增 `search_papers` @tool |
| **多模型供应商** | `model_factory.py` | 低 | 在 `_model_for_role` 中加 provider 路由 |
| **流式 token 输出** | `run_test.py` | 高 | 需改 `stream_mode` 为 `messages` |
| **WebSocket 替代 SSE** | `server.py` | 中 | 双向通信, 支持实时交互 |
| **数据库替代 JSONL** | `runtime_state.py` | 中 | SQLite 更适合大量 run 的查询 |
| **Docker 部署** | 新增 Dockerfile | 低 | 解决模型下载和路径问题 |

---

> **维护原则**（来自 CLAUDE.md）:
> - Supervisor 不做搜索 — 工具只在 Researcher 上
> - 所有可调值在 config.py — 不硬编码
> - Prompt 是 80% 的行为 — 改行为优先改 Prompt
> - 确定性工作出 Agent 循环 — .docx 在 Python 做
> - 使用 `cfg.X` 动态引用 — 不直接从 config import 值
