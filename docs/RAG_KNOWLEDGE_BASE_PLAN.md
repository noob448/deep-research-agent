# 本地 RAG 知识库实施方案 · Local RAG Knowledge Base Plan

> 本文件用于给深度研究 agent 增加「本地向量化知识库 + RAG 检索」能力：把每轮研究归档的浓缩摘要向量化、本地持久化，让 agent 在研究新课题时可选择性地查询历史积累，给出更高质量的回答。
> 它是一份可执行的实施方案，供编码助手（Claude Code，驱动 DeepSeek）按任务实现。
> 配套文件：`SEARCH_QUALITY_PLAN.md`、`CN_ACADEMIC_SOURCES.md`。

---

## 0. 给编码助手的执行规则

1. **一次只做一个任务**，做完跑「验证」、确认通过后再做下一个。
2. **只新增/修改本方案指出的文件**，不重构无关代码，不改动 Supervisor-Researcher 的核心编排与文件边界机制。
3. 新建 `.py` 文件第一行写 `# -*- coding: utf-8 -*-`。
4. **本项目 config.py 使用大写常量**（如 `RERANK_MODEL`、`RERANK_TOP_K`、`PROJECT_ROOT`）。新增配置一律沿用此风格（大写常量），并按项目现有的方式引用（如 `from .config import EMBEDDING_MODEL`）。
5. 所有外部/IO 操作必须有 `try/except`，**知识库失败绝不能中断主研究流程**（优雅降级）。
6. 嵌入模型与 reranker 一样**本地加载**，沿用 `rerank.py` 的「lazy-load + lru_cache」模式。
7. 遇到与现有代码不一致处（如变量名、config 引用方式），以实际项目为准并提示用户，不要臆测。

---

## 1. 背景、目标与设计决策

**目标**：基于现有 `history-database/`（Summarizer 浓缩后的研究摘要）建立本地向量库，让 agent 通过 RAG 选择性查询历史知识。

**已确认的设计决策（实现时直接采用）**：

| 决策点 | 选择 | 理由 |
|---|---|---|
| 嵌入模型 | **BGE-M3**（本地） | 与现有 `bge-reranker-v2-m3` 同家族、同 sentence-transformers 基础设施；中英文强；8192 token 上下文远超浓缩摘要长度 |
| 向量库 | **Chroma**（本地持久化） | 嵌入式、落盘到本地目录、支持按元数据（分类/日期）过滤，满足"选择性查询" |
| 切块策略 | **1 篇摘要 = 1 个向量** | 语料已是浓缩摘要（通常 200–900 字），无需切块；这是 Summarizer 设计带来的红利 |
| 索引时机 | **run_test.py 后处理阶段**（Summarizer 写库之后） | 确定性操作放在 agent 循环外（项目设计原则 #7）；增量 upsert + 一次性引导建库 |
| 暴露方式 | **研究员工具 `search_knowledge_base`**（主）+ 规划期注入（可选） | 契合现有"研究员持搜索工具 + 路由表"架构；真正的 agentic RAG |
| 持久化位置 | **`vector-store/`**（项目根，不随 workspace 清空） | 满足"向量信息本地持久存储" |

**关键约束（写进提示词/skill，见任务 4）**：
- 历史研究结果标注「内部历史研究·已浓缩」，时效性强的结论必须用新搜索核实（可能已过时）。
- `search_knowledge_base` 是本地检索，**不计入研究员的 8 次网络搜索上限**。
- 增量索引用稳定 ID（文件路径哈希）做 upsert，避免重复入库。

**数据流（新增部分如何嵌入现有流程）**：

```
【建库】history-database/*.txt ──embed(BGE-M3)──► vector-store/ (Chroma, 本地持久化)
            ▲                                          │
            │ 每轮任务结束后增量 upsert（任务5）         │ 检索
   阶段5后处理（Summarizer 写库之后）                   ▼
                                   ┌────────────────────────────────────┐
                                   │ 研究员调用 search_knowledge_base（任务3）│ ← 研究时选择性查询
                                   │ 规划期注入给 Supervisor（任务6，可选）   │ ← 避免重复研究
                                   └────────────────────────────────────┘
```

---

## 2. 实施任务

---

### 任务 0 · 依赖与配置

**目标**：装好 Chroma，配置好 RAG 相关常量，并解决模型下载问题。

**涉及文件**：`requirements.txt`、`deep_research/config.py`

**依赖安装**

```bash
pip install chromadb
```
> `sentence-transformers` 已随 reranker 安装，无需重复装。

**模型下载（中国大陆重要）**：BGE-M3 需从 HuggingFace 下载（约 1.2GB）。大陆直连可能很慢，**首次运行前**设置镜像：

```bash
# Windows (conda/Anaconda Prompt)
set HF_ENDPOINT=https://hf-mirror.com
# 或永久写入环境变量；Linux/Mac 用 export HF_ENDPOINT=https://hf-mirror.com
```

**在 `config.py` 末尾新增（大写常量，沿用现有风格）**：

```python
# ===== 向量库 / RAG =====
RAG_ENABLED = True
EMBEDDING_MODEL = "BAAI/bge-m3"                      # 本地嵌入模型（与 reranker 同家族）
VECTOR_STORE_DIR = PROJECT_ROOT / "vector-store"    # 本地持久化目录（不随 workspace 清空）
VECTOR_COLLECTION = "research_history"
RAG_TOP_K = 3                                       # 每次检索返回的历史研究条数
```

**验证**

```bash
python -c "from deep_research.config import EMBEDDING_MODEL, VECTOR_STORE_DIR, RAG_TOP_K; print(EMBEDDING_MODEL, VECTOR_STORE_DIR, RAG_TOP_K)"
```
预期：`BAAI/bge-m3 .../vector-store 3`

**完成标准**：chromadb 已安装；config 常量可读取；HF 镜像已配置。

---

### 任务 1 · 核心模块 knowledge_base.py

**目标**：实现嵌入 + Chroma 读写的核心模块，提供 `index_document()`（索引单文件）和 `search_kb()`（检索）。

**涉及文件**：`deep_research/knowledge_base.py`（新建）

**依赖**：任务 0

**实现** — 新建 `deep_research/knowledge_base.py`：

```python
# -*- coding: utf-8 -*-
"""本地知识库：用 BGE-M3 嵌入历史研究摘要，存入本地 Chroma，供 agent 检索。
设计与 rerank.py 一致：模型与集合均 lazy-load + lru_cache 缓存。"""
import hashlib
from functools import lru_cache
from pathlib import Path

from .config import (
    EMBEDDING_MODEL,
    VECTOR_STORE_DIR,
    VECTOR_COLLECTION,
    RAG_TOP_K,
)


@lru_cache(maxsize=1)
def _get_embedder():
    """延迟加载本地嵌入模型（BGE-M3），首次调用时下载并缓存。"""
    from sentence_transformers import SentenceTransformer
    return SentenceTransformer(EMBEDDING_MODEL)


@lru_cache(maxsize=1)
def _get_collection():
    """延迟创建/打开本地 Chroma 持久化集合（cosine 相似度）。"""
    import chromadb
    VECTOR_STORE_DIR.mkdir(parents=True, exist_ok=True)
    client = chromadb.PersistentClient(path=str(VECTOR_STORE_DIR))
    return client.get_or_create_collection(
        name=VECTOR_COLLECTION,
        metadata={"hnsw:space": "cosine"},
    )


def _embed(texts):
    """文本列表 → 归一化向量列表（list[list[float]]）。"""
    model = _get_embedder()
    vecs = model.encode(texts, normalize_embeddings=True)
    return [v.tolist() for v in vecs]


def _parse_metadata(file_path: Path) -> dict:
    """从 history-database/<分类>/<日期>_<课题>.txt 解析元数据。"""
    category = file_path.parent.name          # 分类 = 上级文件夹名
    stem = file_path.stem                      # <日期>_<课题>
    date, _, topic = stem.partition("_")
    return {
        "category": category,
        "date": date,
        "topic": topic or stem,
        "path": str(file_path),
    }


def index_document(file_path) -> str:
    """把单个历史研究 txt 嵌入并 upsert 到向量库（幂等，重复调用不重复入库）。"""
    file_path = Path(file_path)
    if not file_path.exists():
        return f"文件不存在：{file_path}"
    text = file_path.read_text(encoding="utf-8").strip()
    if not text:
        return f"文件为空，跳过：{file_path}"

    meta = _parse_metadata(file_path)
    # 用文件路径哈希作为稳定 ID，保证幂等 upsert（再次索引同一文件只会覆盖，不会重复）
    doc_id = hashlib.md5(str(file_path).encode("utf-8")).hexdigest()

    collection = _get_collection()
    embedding = _embed([text])[0]
    collection.upsert(
        ids=[doc_id],
        embeddings=[embedding],
        documents=[text],
        metadatas=[meta],
    )
    return f"已索引：[{meta['category']}] {meta['topic']}"


def search_kb(query: str, top_k: int = None, category: str = None):
    """检索知识库，返回 [{text, category, date, topic, score}, ...]，按相关度降序。
    category 不为空时只在该分类内检索（实现"选择性查询"）。"""
    top_k = top_k or RAG_TOP_K
    collection = _get_collection()
    if collection.count() == 0:
        return []
    where = {"category": category} if category else None
    q_emb = _embed([query])[0]
    res = collection.query(query_embeddings=[q_emb], n_results=top_k, where=where)

    out = []
    docs = (res.get("documents") or [[]])[0]
    metas = (res.get("metadatas") or [[]])[0]
    dists = (res.get("distances") or [[]])[0]
    for doc, meta, dist in zip(docs, metas, dists):
        out.append({
            "text": doc,
            "category": meta.get("category", ""),
            "date": meta.get("date", ""),
            "topic": meta.get("topic", ""),
            "score": round(1 - dist, 3),   # cosine 距离 → 相似度
        })
    return out
```

> 说明：因为语料是浓缩摘要，**一篇 = 一个向量**，不做切块。若以后想索引完整 report.md（很长），再在 `index_document` 里加切块逻辑。

**验证**（嵌入 + 索引 + 检索一条龙）

新建临时脚本 `verify_kb.py`：

```python
# -*- coding: utf-8 -*-
from pathlib import Path
from deep_research.knowledge_base import _get_embedder, index_document, search_kb

# 1) 嵌入维度（BGE-M3 应为 1024）
dim = _get_embedder().encode(["测试"]).shape
print("嵌入维度:", dim)

# 2) 造一个临时历史文件并索引
tmp = Path("history-database/测试分类/2026-06-04_知识库连通性测试.txt")
tmp.parent.mkdir(parents=True, exist_ok=True)
tmp.write_text("本文研究了向量数据库 Chroma 与 BGE-M3 嵌入模型的本地集成方法。", encoding="utf-8")
print(index_document(tmp))

# 3) 检索
hits = search_kb("向量数据库怎么用", top_k=2)
for h in hits:
    print(h["score"], h["category"], h["topic"])
```
```bash
python verify_kb.py
```
预期：打印维度 `(1, 1024)`、`已索引：[测试分类] 知识库连通性测试`、以及一条相关度较高的检索结果。验证后可删除该脚本和测试文件。

**完成标准**：嵌入模型能加载（首次会下载）；索引和检索均成功；`vector-store/` 目录已生成。

---

### 任务 2 · 引导建库脚本 build_index.py

**目标**：把 `history-database/` 下**已有的**全部 txt 一次性建入向量库。

**涉及文件**：`build_index.py`（新建，放项目根目录）

**依赖**：任务 1

**实现**

```python
# -*- coding: utf-8 -*-
"""一次性引导脚本：把 history-database/ 下已有的全部 txt 建入向量库。
幂等：重复运行不会产生重复向量。"""
from pathlib import Path
from deep_research.config import PROJECT_ROOT   # 若 config 已有 history 路径常量，直接用它
from deep_research.knowledge_base import index_document

HISTORY_DIR = PROJECT_ROOT / "history-database"


def main():
    files = list(HISTORY_DIR.rglob("*.txt"))
    if not files:
        print("history-database/ 下没有 txt 文件，无需建库。")
        return
    print(f"发现 {len(files)} 个历史研究文件，开始建库...")
    for i, f in enumerate(files, 1):
        try:
            print(f"  [{i}/{len(files)}] {index_document(f)}")
        except Exception as e:
            print(f"  [{i}/{len(files)}] 失败：{f} → {e}")
    print("建库完成。")


if __name__ == "__main__":
    main()
```

**验证**

```bash
python build_index.py
python -c "from deep_research.knowledge_base import _get_collection; print('库中文档数:', _get_collection().count())"
```
预期：打印每个文件的索引结果 + "建库完成"；文档数 > 0（等于你 history-database 里的 txt 数量）。

**完成标准**：已有历史研究全部入库，文档数正确。

---

### 任务 3 · 检索工具 search_knowledge_base（主路径）

**目标**：把知识库检索包成 `@tool`，注册给**研究员**，让它们在研究时可主动查历史。

**涉及文件**：`deep_research/tools.py`（新增工具）、`deep_research/subagents.py` 或 `agent.py`（注册到研究员工具列表）

**依赖**：任务 1、2

**实现** — 在 `tools.py` 新增：

```python
# -*- coding: utf-8 -*-
from langchain_core.tools import tool
from .knowledge_base import search_kb
from .config import RAG_ENABLED


@tool
def search_knowledge_base(query: str) -> str:
    """检索本项目过去已完成研究的浓缩知识库（本地、免费、不计入网络搜索次数）。
    在开始一个子问题前优先查询，看是否已有相关积累，可作为背景和起点。
    返回内容标注为【内部历史研究·已浓缩】，时效性强的结论需再用网络搜索核实。"""
    if not RAG_ENABLED:
        return "知识库未启用。"
    try:
        results = search_kb(query)
    except Exception as e:
        return f"知识库检索失败（不影响其他搜索）：{e}"
    if not results:
        return "知识库中暂无相关历史研究（可能尚未建库或无匹配内容）。"
    blocks = []
    for r in results:
        blocks.append(
            f"【内部历史研究·已浓缩｜分类: {r['category']}｜日期: {r['date']}｜"
            f"课题: {r['topic']}｜相关度: {r['score']}】\n{r['text']}"
        )
    return "\n\n---\n\n".join(blocks)
```

**注册到研究员**：在定义研究员工具列表的地方（`subagents.py` 或 `agent.py`，即原本放 `web_search, web_fetch, search_openalex, search_crossref` 的位置），把 `search_knowledge_base` 加进去。三个研究员都加。

> 不要注册给 Supervisor（保持设计原则 #1：Supervisor 不持搜索工具）。

**验证**

```bash
python -c "from deep_research.tools import search_knowledge_base; print(search_knowledge_base.invoke({'query':'<填一个你库里确实有的主题关键词>'}))"
```
预期：返回带「内部历史研究·已浓缩」标注的历史摘要。

**完成标准**：工具能返回历史研究；已注册进三个研究员的工具列表。

---

### 任务 4 · 提示词路由 + source-quality 规则

**目标**：告诉研究员何时用知识库、KB 不计入搜索上限、以及如何对待历史知识（防止把过时结论当事实）。

**涉及文件**：`deep_research/prompts.py`（RESEARCHER_PROMPT）、`deep_research/skills/source-quality/SKILL.md`

**依赖**：任务 3

**实现 1** — 在 `RESEARCHER_PROMPT` 中**追加**（不要删改已有内容）：

```text
## 知识库（历史研究）使用
- 开始研究一个子问题前，先用 search_knowledge_base 查一次，看本项目过去是否已有相关积累。
- search_knowledge_base 是本地检索，免费、快速，【不计入】上面的 8 次网络搜索上限。
- 历史研究结果标注为「内部历史研究·已浓缩」：可作为背景和起点，但时效性强的结论必须再用 web_search / search_openalex 核实，不要直接当作最新事实。

工具路由表新增一行：
  ┌─────────────────────────┬────────────────────────┐
  │ 查询历史研究/已积累知识  │ search_knowledge_base  │
  └─────────────────────────┴────────────────────────┘
```

**实现 2** — 在 `source-quality/SKILL.md` 正文**追加**一节：

```markdown
## 内部历史研究的使用
- 知识库返回的「内部历史研究·已浓缩」是过去某时点的结论，可能已过时。
- 将其作为背景和起点，不作为最终事实；时效性强的结论必须用新搜索交叉验证。
- 引用时与外部来源区分标注（例如"据本项目历史研究"），不与外部一手来源混为一谈。
```

**验证**

```bash
python -c "from deep_research.prompts import RESEARCHER_PROMPT; print('search_knowledge_base' in RESEARCHER_PROMPT)"
python -c "print('内部历史研究' in open('deep_research/skills/source-quality/SKILL.md', encoding='utf-8').read())"
```
（`RESEARCHER_PROMPT` 换成实际变量名）
预期：两条都输出 `True`。

**完成标准**：研究员提示词含知识库使用与路由；source-quality skill 含内部知识使用规则。

---

### 任务 5 · 每轮自动增量索引

**目标**：每轮任务结束、Summarizer 把摘要写入 `history-database/` 之后，自动把这个新文件索引进向量库。

**涉及文件**：`run_test.py`（后处理阶段）

**依赖**：任务 1

**实现** — 在 `run_test.py` 中，**Summarizer 写入 `history-database/<分类>/<文件>.txt` 之后**，加入：

```python
# 在 condense_and_categorize 写出归档文件之后：
if config.RAG_ENABLED:
    try:
        from deep_research.knowledge_base import index_document
        print(f"[知识库] {index_document(archived_file_path)}")
    except Exception as e:
        print(f"[知识库] 索引失败（不影响主流程）：{e}")
```

> `archived_file_path` 换成 run_test.py 中**实际保存归档文件路径的变量**。若当前代码没有把该路径存成变量，先把写文件那一步的路径接出来再传入。
> `config` 按 run_test.py 现有的引用方式（如 `from deep_research import config`）。

**验证**

跑一次完整研究任务，观察控制台：
```bash
python run_test.py
```
预期：流程结束时打印 `[知识库] 已索引：[<分类>] <课题>`。再确认文档数增加了 1：
```bash
python -c "from deep_research.knowledge_base import _get_collection; print('库中文档数:', _get_collection().count())"
```

**完成标准**：每轮任务结束后新摘要自动入库，文档数随之增长，且索引失败不影响报告生成。

---

### 任务 6（可选/进阶）· 规划期注入历史研究给 Supervisor

**目标**：在 agent 开始前，用课题检索相关历史研究并注入初始消息，让 Supervisor 避免重复研究、衔接历史结论。**不给 Supervisor 工具**（保持设计原则 #1），检索在 Python 层完成（保持原则 #7）。

**涉及文件**：`run_test.py`（调用 `agent.stream(...)` 之前）

**依赖**：任务 1、2

**实现** — 在构造给 agent 的初始输入之前：

```python
prior_knowledge = ""
if config.RAG_ENABLED:
    try:
        from deep_research.knowledge_base import search_kb
        hits = search_kb(user_topic, top_k=3)
        if hits:
            prior_knowledge = (
                "\n\n【已有相关历史研究（供参考，避免重复研究；"
                "时效性强的结论需重新核实）】\n"
            )
            for h in hits:
                prior_knowledge += (
                    f"- [{h['category']}] {h['topic']}（{h['date']}，"
                    f"相关度{h['score']}）：{h['text'][:300]}...\n"
                )
    except Exception as e:
        print(f"[知识库] 规划期检索失败（忽略）：{e}")

# user_topic 换成你实际接收用户课题的变量；把 prior_knowledge 拼到初始消息后面
initial_input = user_topic + prior_knowledge
# 然后用 initial_input 作为 agent.stream({messages:[...]}) 的用户消息
```

**验证**

用一个**你之前研究过的相关课题**跑一次，观察 Supervisor 的规划阶段是否提到/利用了历史研究（控制台流式输出里可见）。

**完成标准**：相关历史研究被注入初始上下文；Supervisor 规划时能参考、不重复已有工作。

---

## 3. 验收清单

- [ ] 任务 0：chromadb 已装，config 常量可读，HF 镜像已配
- [ ] 任务 1：`knowledge_base.py` 嵌入/索引/检索一条龙通过，`vector-store/` 已生成
- [ ] 任务 2：`build_index.py` 把已有历史研究全部入库，文档数正确
- [ ] 任务 3：`search_knowledge_base` 工具能返回历史研究，已注册给三个研究员（未给 Supervisor）
- [ ] 任务 4：研究员提示词含路由与"不计入搜索上限"，source-quality 含内部知识规则
- [ ] 任务 5：每轮任务结束后新摘要自动入库，失败不影响主流程
- [ ] 任务 6（可选）：规划期向 Supervisor 注入相关历史研究
- [ ] 端到端：研究一个有历史积累的课题，报告中能体现对历史知识的利用，且历史与外部来源区分标注

---

## 4. 实施顺序与注意事项

**顺序**：任务 0 → 1 → 2（先把库建起来）→ 3 → 4（核心需求到此完成）→ 5（自动入库）→ 6（可选增强）。

**注意事项**：
- **模型下载**：BGE-M3 约 1.2GB，大陆务必先设 `HF_ENDPOINT=https://hf-mirror.com`，否则首次加载会很慢或失败。
- **内存**：BGE-M3（~1.2GB）+ bge-reranker 同时加载约占 2–3GB 内存，CPU 可跑；有 GPU 会快很多（sentence-transformers 自动用 GPU）。
- **幂等**：增量索引和建库都用文件路径哈希做 upsert，重复运行不会重复入库。
- **优雅降级**：知识库相关代码全部包 `try/except`，任何失败都只打印日志、不中断研究与报告生成。
- **语料即浓缩摘要**：一篇一个向量，不切块；这是 Summarizer 设计的红利，别为已浓缩的内容画蛇添足加切块。
- **chromadb 版本**：上面用的是 `PersistentClient` / `get_or_create_collection` / `upsert` / `query` / `count` 稳定 API；若你安装的版本接口有差异，以 chromadb 官方文档为准，必要时在 requirements.txt 固定版本。
- **价值随积累增长**：库越大，RAG 越有用。现在先建起来，之后每轮自动积累。
