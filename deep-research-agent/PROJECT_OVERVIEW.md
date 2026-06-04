# 深度研究智能体 · 项目全景文档

> 生成时间：2026-06-04 | 总代码量：~1800 行 Python + 2 个 Skill

---

## 一、项目定位

一个基于 **LangChain deepagents 框架** 的多智能体深度研究系统。
用户输入一个研究课题 → 系统自动制定计划、并行搜索、交叉验证、撰写报告、浓缩归档。

**核心哲学**：Supervisor 负责编排（不搜索），Researcher 负责搜索（不写报告），
两者通过文件系统和消息传递解耦，原始搜索结果永不进入 Supervisor 上下文。

---

## 二、技术栈

| 层级 | 技术 | 用途 |
|------|------|------|
| **大模型** | DeepSeek V4 Pro (OpenAI 兼容 API) | 所有智能体共用同一模型 |
| **Agent 框架** | LangChain deepagents (LangGraph) | 提供 write_todos / task / filesystem / skills 原语 |
| **通用搜索** | DuckDuckGo (ddgs 库) | 免费，无需 API key，底层轮询多引擎 |
| **学术搜索** | OpenAlex REST API | 免费，覆盖 2.4 亿论文，国内可达 |
| **学术元数据** | Crossref REST API | 免费，提供 DOI/期刊/作者 |
| **检索重排** | BAAI/bge-reranker-v2-m3 (Cross-Encoder) | 本地 sentence-transformers 加载，搜索 10→4 精排 |
| **向量嵌入** | BAAI/bge-m3 (1,024 维) | 本地 sentence-transformers 加载，历史研究向量化 |
| **向量库** | Chroma (PersistentClient) | 本地持久化，cosine 相似度检索 |
| **报告生成** | python-docx | Markdown → .docx 纯 Python 转换 |
| **HTTP 抓取** | httpx | web_fetch 的底层 HTTP 客户端 |
| **运行环境** | Python 3.x + conda, Windows 11 | 支持 CPU/GPU |

---

## 三、完整架构图

```
                              run_test.py (入口)
                                    │
                    ┌───────────────┼───────────────┐
                    │               │               │
              config.py        agent.py        用户课题
              (全部配置)    (组装 Supervisor)       │
                                    │               │
                          ┌─────────▼─────────┐     │
                          │    Supervisor     │     │
                          │  (deepseek-v4-pro)│     │
                          │  SUPERVISOR_PROMPT│     │
                          │  工具: write_todos│     │
                          │        task       │     │
                          │        write_file │     │
                          │        read_file  │     │
                          └──┬───────┬───────┬┘     │
                             │       │       │       │
                    task()   task()  task()  │       │
                     ┌────────┐┌────────┐┌───────┐  │
                     ▼        ▼▼        ▼▼       ▼  │
              ┌──────────┐┌──────────┐┌──────────┐   │
              │researcher││researcher││researcher│   │
              │   -1     ││   -2    ││   -3     │   │
              │          ││         ││          │   │
              │ 5 个工具: ││ 同左    ││ 同左     │   │
              │ web_search││         ││          │   │
              │ web_fetch ││         ││          │   │
              │ search_   ││         ││          │   │
              │  openalex ││         ││          │   │
              │ search_   ││         ││          │   │
              │  crossref ││         ││          │   │
              │ search_   ││         ││          │   │
              │  knowledge││         ││          │   │
              │  _base    ││         ││          │   │
              └─────┬─────┘└────┬────┘└─────┬────┘
                    │           │           │
                    ▼           ▼           ▼
              /notes/*.md   (文件系统隔离)
                    │           │           │
                    └───────────┼───────────┘
                                │  Supervisor 读笔记
                                ▼
                          /report.md (9,000+ 字)
                          /research_summary.txt
                                │
                    ┌───────────┼───────────┐
                    ▼           ▼           ▼
              report.docx  summarizer.py  knowledge_base.py
              (python-docx)  (LLM 分类+浓缩)  (BGE-M3 嵌入)
                                │               │
                                ▼               ▼
                          history-database/  vector-store/
                          <分类>/<日期>.txt  (Chroma 持久化)
```

---

## 四、五个阶段详细流程

### 阶段 1 — 制定计划 (write_todos)
Supervisor 收到课题后，第一步就是调用 write_todos 拆解为 3-4 个独立子问题。
每个子问题可并行研究，例如"多模态大模型范式"被拆为：
  ├── 子问题1: 主流处理范式对比
  ├── 子问题2: 成功案例调研
  └── 子问题3: 前沿趋势和方向

### 阶段 2 — 并行委托 (task × 3)
Supervisor 在同一条消息中调用 3 次 task()，一次性派出全部研究员。
每个研究员拥有独立的上下文窗口（不共享），并行工作 5-10 分钟。

研究员内部流程：
  1. 拆解子问题 → 4-5 个窄查询
  2. 调用 search_knowledge_base 查历史积累（1次，不计入上限）
  3. 按路由表选择搜索工具（学术→OpenAlex，产品→DDGS，规范→Crossref）
  4. 搜索 → 重排(10→4) → 抓取 → 分析
  5. 达到 8 次搜索上限后停止（web_search + search_openalex + search_crossref 合计）
  6. 返回结构化摘要：[进度]标记 + 核心发现(带URL) + 关键来源 + 充分性评估

### 阶段 3 — 归档笔记 + 检查补漏
Supervisor 将研究员返回的内容写入 /notes/*.md，然后检查完整性。
如果某个维度不够深入，再次 task 补充。确认后 ls /notes 列出所有笔记。

### 阶段 4 — 分节撰写报告
Supervisor 先读 /skills/academic-report/SKILL.md 获取格式规范，
然后分 4 节增量写入 /report.md（避免一次性生成长时间无输出）：
  第1节: 摘要 + 研究背景
  第2节: 核心发现（含对比表、按主题分组）
  第3节: 分析与讨论（矛盾标注、局限性、开放问题）
  第4节: 结论 + 参考来源（编号制 [1][2]...）

### 阶段 5 — 自我批判 + 归档
Supervisor 通读 /report.md，找出至少 1 处不足。
修正后写入 /research_summary.txt（不含分类标签）。

然后 run_test.py 执行 Python 后处理：
  1. report.md → report.docx (python-docx)
  2. 扫描 history-database/ 已有分类
  3. 调 Summarizer LLM：分类决策 + 内容浓缩 (原长/4, ≥200字)
  4. 写入 history-database/<分类>/<日期>_<课题>.txt (浓缩版)
  5. 调 knowledge_base.index_document()：BGE-M3 嵌入 → Chroma upsert
  6. 打印文档数变化

---

## 五、搜索管道技术细节

### 5.1 通用搜索 (web_search)
```
用户查询 → DDGS.text(query, max_results=10)
         → DuckDuckGo 后端轮询 (Google/Bing/Yahoo/Brave/Startpage/Mojeek)
         → 返回 [{title, href, body}, ...]
         → 如果 RERANK_ENABLED:
             rerank_results(query, results)
             → CrossEncoder(BAAI/bge-reranker-v2-m3).predict([(q, body)])
             → 按分数排序 → 保留 top 4
         → 格式化返回: 编号 + 标题 + URL + 摘要
```

重排模型延迟加载：`@lru_cache(maxsize=1)` + `CrossEncoder`，首次下载 ~300MB。
之后同一进程内缓存，不再重复加载。

### 5.2 网页抓取 (web_fetch)
```
URL (arxiv.org 自动替换为 xxx.itp.ac.cn)
  → httpx GET (User-Agent 伪装, timeout=15s)
  → 正则清洗 HTML (_html_to_text):
     去 <script>/<style> → 块级元素换行 → 去标签 → 实体解码
  → 截断到 4000 字符
  → 失败时自动重试 (3次, 指数退避 1.5s→2.25s→3.375s)
```

### 5.3 学术搜索 (search_openalex)
```
GET https://api.openalex.org/works?search={query}&per-page=5
  → JSON response → results[]
  → 每个 result: {title, publication_year, doi, authorships, abstract_inverted_index}
  → _reconstruct_abstract(): 倒排索引 → 正常文本 (500字截断)
  → 格式化返回
```

### 5.4 引用元数据 (search_crossref)
```
GET https://api.crossref.org/works?query={query}&rows=5
  → JSON → message.items[]
  → 每个 item: {title, DOI, container-title, published, author}
  → 返回规范引用信息（补充 OpenAlex 可能缺失的期刊名/DOI）
```

### 5.5 知识库检索 (search_knowledge_base)
```
用户查询 → knowledge_base.search_kb(query, top_k=3)
  → 获取 BGE-M3 嵌入 (1,024维)
  → Chroma.query(query_embeddings, n_results=3, where={category?})
  → 返回 [{text, category, date, topic, score}, ...]
  → 格式化: 【内部历史研究·已浓缩｜分类: xxx｜日期: xxx｜相关度: 0.xxx】
```

BGE-M3 模型：~1.2GB，延迟加载，首次下载后缓存。
Chroma 集合：线程锁保护 (threading.Lock)，Windows 下 3 次重试。

---

## 六、知识库全生命周期

### 建库 (build_index.py)
```
history-database/*/*.txt → index_document(file)
  → BGE-M3 嵌入 (normalize_embeddings=True)
  → Chroma.upsert(id=MD5(path), embedding, document, metadata)
  → 幂等: 相同文件路径 → 相同 MD5 → upsert 只覆盖不重复
```

### 增量入库 (run_test.py 后处理)
```
每轮任务结束 → Summarizer 写入 history-database/xxx.txt
  → index_document(archived_path) 自动触发
  → 文档数 +1
  → 优雅降级: 索引失败只打日志，不影响报告生成
```

### 检索 (研究员工具)
```
search_knowledge_base(query) → search_kb(query, top_k=3)
  → 可选 category 过滤 (where={"category": "xxx"})
  → 返回 top 3 相似文档 (cosine 相似度)
  → 不计入 8 次网络搜索上限
```

---

## 七、提示词体系 (80% 的行为在这里)

### SUPERVISOR_PROMPT (~1500 字)
- 5 阶段铁律
- 工具表: write_todos / task / write_file / read_file
- 进度追踪格式
- 引用规则: 编号制，禁止正文贴 URL

### RESEARCHER_PROMPT (~1200 字)
- 搜索上限: 8 次 (web_search + search_openalex + search_crossref 合计)
- 查询窄化规范: 拆宽问题为窄查询
- 学术搜索路由: 5 行决策表 (OpenAlex vs DDGS vs Crossref vs KB)
- 知识库使用: 研究前查一次，>0.5 才用，不计入上限
- KB 与 OpenAlex 互补关系
- 返回格式: [进度] + [完成] 研究摘要 + 关键来源
- web_fetch 失败 3 次即放弃

---

## 八、Skills 体系

### academic-report/SKILL.md
- 报告结构: 摘要→背景→发现→讨论→结论→来源
- 引用规则: 每篇论文单独编号，禁止打包引用，学术论文需 arXiv ID/DOI
- 质量检查: 8 项清单

### source-quality/SKILL.md
- 高质量来源标准: 同行评审/官方文档/知名技术媒体
- 低质量警戒: 无日期/内容农场/营销软文/洗稿
- 处理规则: 交叉验证≥2 / 标注存疑 / 记录分歧 / 宁缺毋滥 / 时效优先
- 内部历史研究使用规则: 标注为历史结论，需重新核实

---

## 九、配置系统总览

```
config.py (全大写模块级常量)
├── 路径: PROJECT_ROOT, WORKSPACE_DIR, SKILLS_DIR
├── API:  DEEPSEEK_API_KEY (env > deepseek.txt), DEEPSEEK_BASE_URL
│          AGENT_MODEL="deepseek-v4-pro", REQUEST_TIMEOUT=180s
├── 搜索: SEARCH_MAX_RESULTS=10, FETCH_CHAR_LIMIT=4000, FETCH_TIMEOUT=15s
├── 重排: RERANK_ENABLED=True, RERANK_MODEL="BAAI/bge-reranker-v2-m3", RERANK_TOP_K=4
├── 学术: USE_OPENALEX=True, USE_CROSSREF=True, ARXIV_MIRROR="xxx.itp.ac.cn"
├── RAG:  RAG_ENABLED=True, EMBEDDING_MODEL="BAAI/bge-m3"
│          VECTOR_STORE_DIR, VECTOR_COLLECTION, RAG_TOP_K=3
├── 归档: SUMMARIZE_MODEL, REPORT_FILENAME, OUTPUT_DOCX_FILENAME
└── 运行时: RECURSION_LIMIT=250, SUBAGENT_MAX_CONCURRENCY=3
```

HF_ENDPOINT 自动设为 https://hf-mirror.com (大陆镜像)。

---

## 十、文件结构总览

```
deep-research-agent/          ← 项目根
├── run_test.py               ← 主入口 (流式输出 + 归档 + 增量索引)
├── build_index.py            ← 一次性建库脚本
├── requirements.txt          ← 依赖
├── PROJECT_OVERVIEW.md       ← 本文档
├── AGENT_ARCHITECTURE.txt    ← v1 技术文档 (部分过时)
│
├── deep_research/            ← 核心 Python 包
│   ├── config.py             ← 集中配置 (100+ 行)
│   ├── tools.py              ← 5 个 @tool (360+ 行)
│   │   ├── web_search        (DDGS → rerank)
│   │   ├── web_fetch         (httpx → HTML→text, arXiv 镜像)
│   │   ├── search_openalex   (OpenAlex REST API)
│   │   ├── search_crossref   (Crossref REST API)
│   │   └── search_knowledge_base (Chroma 本地检索)
│   ├── rerank.py             ← Cross-Encoder 重排 (50 行)
│   ├── prompts.py            ← SUPERVISOR_PROMPT + RESEARCHER_PROMPT (200+ 行)
│   ├── subagents.py          ← 3 个 researcher SubAgent 定义 (70 行)
│   ├── agent.py              ← Supervisor 组装工厂 (140 行)
│   ├── summarizer.py         ← LLM 分类决策 + 内容浓缩 (80 行)
│   ├── knowledge_base.py     ← BGE-M3 + Chroma 读写 (110 行)
│   ├── report.py             ← Markdown → .docx 转换 (180 行)
│   └── skills/
│       ├── academic-report/SKILL.md   ← 报告格式 + 引用规则
│       └── source-quality/SKILL.md    ← 来源质量准则
│
├── examples/
│   └── run.py                ← 备用入口 (简洁输出, 无归档)
│
├── workspace/                ← 运行时产出 (每轮自动清空)
│   ├── notes/                ← 研究员笔记
│   ├── report.md / .docx     ← 最终报告
│   └── research_summary.txt  ← 归档用摘要
│
├── history-database/         ← 历史研究 (持久化, 不清空)
│   └── <分类>/<日期>_<课题>.txt  ← 浓缩后的归档文件
│
└── vector-store/             ← Chroma 本地向量库 (持久化)
    └── research_history/     ← BGE-M3 嵌入的文档集合
```

---

## 十一、数据流完整示例

以最近一次"多模态大模型"研究为例：

```
1. 用户输入: "多模态大模型目前流行的处理范式是什么，有哪些成功的案例"
2. Supervisor write_todos → 3 个子问题
3. Supervisor task × 3 → 派出 researcher-1/2/3
4. 每个 researcher:
   ├── search_knowledge_base("多模态大模型") → 命中 3 条历史 (相关度 0.6+)
   ├── search_openalex("multimodal LLM architecture survey") → 5 篇论文
   ├── web_search("LLaVA MLP visual projector...") → 10→4 重排
   ├── web_fetch(arxiv.org/abs/2304.08485) → arXiv 镜像加速
   ├── web_fetch(huggingface.co/...) → 抓取模型文档
   └── 达到 8 次搜索 → 返回结构化摘要
5. Supervisor 读笔记 → 写 /report.md (分 4 节, 8,921 字)
6. Supervisor 自我批判 → 写 /research_summary.txt
7. run_test.py 后处理:
   ├── report.docx 生成
   ├── Summarizer: 已有 5 个分类 → 匹配 "多模态大模型, 视觉语言模型, 架构范式"
   │   浓缩: 1,811→896 字
   ├── 写入 history-database/多模态大模型, 视觉语言模型, 架构范式/2026-06-04_...txt
   └── index_document() → Chroma upsert → 文档数 6
8. 完成: 9分57秒, 35 步
```

---

## 十二、当前实验数据 (4 次报告)

| # | 课题 | 字数 | 学术引用 | KB | 耗时 |
|---|------|------|---------|-----|------|
| 1 | AI Agent 主流范式 | 9,603 | 0 | N/A | 9分40秒 |
| 2 | Agent 记忆系统 | 15,633 | 2 arXiv | N/A | 11分44秒 |
| 3 | VLA 模型范式 | 8,584 | 6 arXiv/DOI | N/A | ~10分 |
| 4 | 多模态大模型 | 8,921 | 4 arXiv + 1 CVPR DOI | 3次/0报错 | 9分57秒 |

累计归档 6 个文件 (含 2 个早期测试)，5 个分类文件夹，向量库 6 个文档。

---

## 十三、已实现 vs 待实现

### ✅ 已完成
- [x] Supervisor + 3 Researcher 多智能体架构
- [x] DuckDuckGo 通用搜索 + 重排
- [x] OpenAlex + Crossref 学术搜索
- [x] arXiv 镜像加速
- [x] 本地 Chroma 向量知识库 + BGE-M3 嵌入
- [x] Summarizer LLM 分类决策 + 内容浓缩
- [x] 每轮自动增量索引
- [x] 2 个 Skills (academic-report + source-quality)
- [x] Markdown → .docx 报告生成
- [x] history-database 分类归档
- [x] 工具路由表 (研究者自主选择搜索工具)
- [x] Windows Chroma 并发 Bug 修复
- [x] 网络请求优雅降级 (timeout + retry)

### 🔜 待实现
- [ ] 秘塔 Metaso 接入 (国产 AI 搜索)
- [ ] LangGraph Store 跨会话记忆
- [ ] Human-in-the-loop 计划审批
- [ ] 反思循环 (critique sub-agent)
- [ ] HTTP 代理支持 (国内网络)
- [ ] 研究进度持久化 (中断可恢复)
