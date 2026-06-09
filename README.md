# Deep Research Agent

基于 LangChain `deepagents` 框架的多智能体深度研究系统。输入一个课题，自动规划、并行搜索、交叉验证、撰写结构化报告、事实核验、归档。

## 工作原理

```
用户课题 → Supervisor MECE 分解 → 动态数量 Researcher 搜索
          ├── DuckDuckGo (通用网络)
          ├── OpenAlex (英文学术, 2.4亿篇)
          ├── Crossref (学术元数据/DOI)
          ├── 百度学术 / 知乎 / 百度百科 (国内来源)
          └── 本地向量知识库 (BGE-M3 + Chroma)

         → Cross-Encoder 重排精排 → 结构化归档
         → Supervisor 分节撰写报告 → Critic 审查（可选）
         → Verifier 事实核验 → Summarizer 浓缩归档
```

- **Supervisor**：编排规划、分配任务、质量把关，**不直接搜索**
- **Researcher × N**：独立上下文，OODA 循环，搜索预算代码层硬拦截
- **Critic**（可选）：独立审查报告质量，输出结构化缺陷清单
- **Verifier**：读取原始来源文件，逐条核验报告中论断的事实支撑
- **RAG 知识库**：每次研究摘要自动向量化入库，后续可检索历史积累

---

## 环境要求

| 资源 | 需求 | 说明 |
|------|------|------|
| Python | 3.10+ | |
| Node.js | 18+ | 仅 Web 前端构建时需要 |
| 内存 | 4GB+（推荐 8GB） | BGE-M3 嵌入模型 ~1.2GB + BGE reranker ~300MB |
| 磁盘 | ~3GB 空闲 | 模型下载后缓存，Chroma 向量库增量增长 |
| CPU | 任意现代 CPU | 模型在 CPU 上运行，无需 GPU |
| GPU | **不需要** | LLM 推理走 DeepSeek API，本地仅做轻量文本嵌入 |
| 网络 | 需要 | 调用 DeepSeek API + DuckDuckGo 搜索 |

> 核心计算在云端——推理走 API，本地只跑 CPU 优化的文本嵌入。几年前的旧笔记本也能正常运行。

---

## 第一步：安装依赖

```bash
# 克隆仓库
git clone git@github.com:noob448/deep-research-agent.git
cd deep-research-agent/deep-research-agent

# 安装 Python 依赖
pip install -r requirements.txt

# （推荐）使用 conda 环境隔离
conda create -n deep-research python=3.12
conda activate deep-research
pip install -r requirements.txt
```

---

## 第二步：配置 API Key

在项目根目录（`self-project-agent/`）下创建 `deepseek.txt`：

```
sk-your-deepseek-api-key
```

或者设置环境变量：

```bash
export DEEPSEEK_API_KEY="sk-your-deepseek-api-key"
```

默认使用 DeepSeek V4 Pro（OpenAI 兼容接口）。如需切换模型，编辑 `deep_research/config.py` 中的 `AGENT_MODEL`。

---

## 第三步：CLI 命令行使用

### 基础用法

```bash
# 最简单的运行方式（deep 模式，推荐）
python run_test.py "你的研究课题"

# 快速搜索（fast 模式，5次搜索/5分钟时限）
python run_test.py "简单事实查询" --short-thinking

# 深度研究（max 模式，含 Critic 审查 + Verifier 核验）
python run_test.py "复杂研究课题" --long-thinking --enable-critic
```

### 三档模式对比

| 模式 | CLI 参数 | 搜索上限 | 时间限制 | Critic | Verifier | 适用场景 |
|------|---------|---------|---------|--------|----------|---------|
| ⚡ Fast | `--short-thinking` | 5 次 | 5 分钟 | ❌ | ❌ | 简单事实查询 |
| 🔬 Deep | (默认) | 20 次 | 无 | ❌ | ✅ | 常规深度研究 |
| 🧠 Max | `--long-thinking --enable-critic` | 20 次 | 无 | ✅ | ✅ | 复杂多维课题 |

### 完整 CLI 参数

```bash
# 推理深度
python run_test.py "课题" --reasoning-effort max      # Supervisor 推理档位 (high/max)
python run_test.py "课题" --researcher-effort high     # Researcher 推理档位

# 搜索控制
python run_test.py "课题" --max-searches 15            # 每研究员搜索上限
python run_test.py "课题" --max-researchers 3          # 并行 researcher 数量

# 反思与审批
python run_test.py "课题" --enable-critic              # 开启 Critic 反思回路
python run_test.py "课题" --critic-rounds 2            # Critic 最多轮数（默认3）
python run_test.py "课题" --interactive-plan           # HITL 人工计划审批

# RAG 调试
python run_test.py "课题" --no-hybrid-kb               # 关闭混合检索
python run_test.py "课题" --no-rerank-kb               # 关闭 KB 重排
python run_test.py "课题" --no-contextual-rag          # 关闭上下文检索

# 运行管理
python run_test.py --list-runs                         # 列出历史 run
python run_test.py --resume                            # 恢复最近一次 run
python run_test.py --resume 20260608_091942            # 恢复指定 run
python run_test.py "课题" --run-id my_custom_id        # 指定 run 目录名

# 调试
python run_test.py "课题" --debug                      # 打印 thinking 内容

# 查看全部选项
python run_test.py --help
```

### 运行产出

```bash
runs/<run_id>/
├── workspace/
│   ├── report.md          # 最终研究报告（Markdown）
│   ├── report.docx        # Word 格式报告
│   ├── research_summary.txt  # 浓缩摘要
│   └── notes/             # 研究员返回归档
├── sources/               # 来源全文保存
│   └── src_xxxxxx.txt
└── state/
    ├── events.jsonl       # 事件流
    ├── sources.jsonl      # 来源账本
    ├── claims.jsonl       # 论断账本
    └── research_progress.json
```

---

## 第四步：Web 界面使用

### 启动方式

```bash
# 方式一：生产模式（单端口 5001，需要先构建前端）
cd web
npm install
npm run build
cd ..
python server.py
# 浏览器打开 http://localhost:5001

# 方式二：开发模式（双端口，前端热更新）
# 终端 1
python server.py
# 终端 2
cd web
npm install
npm run dev
# 浏览器打开 http://localhost:5173（Vite dev 代理到 Flask :5001）
```

### Web 功能面板

| 面板 | 功能 | 数据源 |
|------|------|--------|
| **实时日志** | SSE 实时推流，自动滚动 | Agent stdout |
| **Agent 活动** | 按 Researcher 分组展示工具调用链 | 日志解析 |
| **来源账本** | 按类型过滤查看所有来源 | sources.jsonl |
| **论断验证** | 报告论断的核验状态（SUPPORTED/PARTIAL/UNSUPPORTED） | claims.jsonl |
| **报告预览** | Markdown 渲染 + 下载 .md/.docx/.txt | report.md |

---

## 配置说明

所有可调参数集中在 `deep_research/config.py`，主要配置项：

```python
# ── 模型配置 ──
AGENT_MODEL = "deepseek-v4-pro"         # 默认模型
DEEPSEEK_BASE_URL = "https://api.deepseek.com"
REQUEST_TIMEOUT = 300                   # API 超时（秒）
MAX_RETRIES = 5

# ── 搜索配置 ──
RESEARCHER_SEARCH_LIMIT = 20            # 每研究员搜索硬上限
SEARCH_MAX_RESULTS = 10                 # 单次搜索返回数（重排前）
RERANK_TOP_K = 4                        # 重排后保留数
FETCH_TIMEOUT = 15                      # 网页抓取超时

# ── 学术来源 ──
USE_OPENALEX = True                     # 英文学术
USE_CROSSREF = True                     # 学术元数据
USE_CN_SEARCH = True                    # 国内来源（知乎/百科/百度学术）

# ── 上下文控制 ──
TOOL_OUTPUT_SOFT_CHAR_LIMIT = 18000     # 软限制警告
TOOL_OUTPUT_HARD_CHAR_LIMIT = 30000     # 硬限制强制停止
ENABLE_SOURCE_REGISTRY = True           # 来源追踪

# ── Verifier ──
VERIFIER_ENABLED = True                 # 事实验证
VERIFIER_AS_SUBAGENT = False            # False=Python层调用, True=LangGraph subagent
```

---

## 项目结构

```
deep-research-agent/
├── run_test.py                 # CLI 主入口
├── server.py                   # Flask Web 服务
├── requirements.txt            # Python 依赖
├── deep_research/              # 核心包
│   ├── config.py               # 集中配置（160+ 项）
│   ├── agent.py                # Agent 组装工厂
│   ├── prompts.py              # 全部 System Prompt
│   ├── tools.py                # 6 类搜索工具 + 预算控制
│   ├── subagents.py            # Researcher + Critic + Verifier
│   ├── model_factory.py        # LLM 工厂 + 并发限流
│   ├── rerank.py               # Cross-Encoder 重排
│   ├── report.py               # Markdown → .docx
│   ├── knowledge_base.py       # BGE-M3 + Chroma 向量库
│   ├── summarizer.py           # 摘要分类 + 浓缩
│   ├── source_registry.py      # 来源注册 + source_id 追踪
│   ├── claim_verifier.py       # 论断抽取 + 事实核验
│   ├── runtime_state.py        # Run 状态管理
│   └── skills/                 # 渐进式 Skills
│       ├── academic-report/SKILL.md
│       └── source-quality/SKILL.md
├── web/                        # React 前端
│   ├── src/
│   │   ├── App.tsx
│   │   ├── components/         # 9 个 UI 组件
│   │   ├── api/research.ts     # API 调用
│   │   └── types/              # TypeScript 类型定义
│   ├── package.json
│   └── vite.config.ts
├── docs/                       # 开发文档
└── runs/                       # 研究产出（运行时生成）
```

## 许可证

MIT
