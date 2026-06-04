# Deep Research Agent · 改进实施文档 v1.0

> 给 Claude Code 的执行指南。基于现有 `deep_research/` 包结构,按本文顺序与文件清单逐项落地。
>
> **总体原则**
> - 所有新功能加 CLI flag,默认值保守,向后兼容(旧调用方式不会坏)
> - 不破坏现有归档目录 (`history-database/`) 和向量库 (`vector-store/`)——只**增加** metadata 字段,不删除旧字段
> - 仅引入 1 个新依赖:`rank_bm25`(可选,见 §2);其它全部复用现有库
> - 现有的 `bge-reranker-v2-m3`、`bge-m3`、Chroma、deepagents、LangChain 全部保留

---

## 0. 改动模块总览

| # | 模块 | 涉及文件 | 依赖 | 默认开关 |
|---|------|---------|------|---------|
| 1 | 配置层 + CLI | `config.py`, `run_test.py` | 基础,必须先做 | — |
| 2 | RAG 升级(混合检索 + 上下文检索 + KB 重排) | `knowledge_base.py`, `tools.py`, `summarizer.py`, `build_index.py` | 独立 | ON |
| 3 | 推理深度(reasoning_effort + 透传) | `agent.py`, `subagents.py`, `config.py` | 模块 1 | `--reasoning-effort max` |
| 4 | Critic 反思回路 | `subagents.py`, `prompts.py`, `agent.py` | 模块 3 | `--enable-critic` |
| 5 | 任务分配脚手架(prompt 重写) | `prompts.py` | 模块 3、4 | 默认生效 |
| 6 | HITL 计划审批 | `tools.py`, `prompts.py`, `run_test.py` | 模块 1 | `--interactive-plan` |

**执行顺序建议**:1 → 2 → 3 → 5 → 4 → 6 → 8(测试)。模块 2 和 3-5 可并行。

---

## 1. 配置层 + CLI

### 1.1 `deep_research/config.py` 新增常量

在文件末尾(`RECURSION_LIMIT` 那块附近)追加:

```python
# ============================================================
# 新增配置(v1.0 改进)
# ============================================================

# ---- 推理深度控制 ----
# DeepSeek V4 Pro/Flash 支持 reasoning_effort: "high" 或 "max"
# max 档:思维链更长、agentic 任务更深;但需要更长输出窗口、更多 token
# 注意:thinking 模式下 temperature/top_p/penalty 全部静默忽略
REASONING_EFFORT_SUPERVISOR = "max"
REASONING_EFFORT_RESEARCHER = "high"   # researcher 调工具多、推理需求相对低,留在 high 省 token
REASONING_EFFORT_CRITIC = "max"
THINKING_ENABLED = True
THINKING_MAX_OUTPUT_TOKENS = 16000      # max 档需要更长窗口

# ---- 研究员深度 ----
RESEARCHER_SEARCH_LIMIT = 15            # 原 8,改 15
RESEARCHER_SUFFICIENCY_REQUIRED = True  # 必须自评充分性才能停

# ---- Critic 反思回路 ----
CRITIC_ENABLED = False                  # CLI flag 控制
CRITIC_MAX_ROUNDS = 1                   # 默认最多 1 轮反思→补研究→修订

# ---- HITL 计划审批 ----
INTERACTIVE_PLAN_APPROVAL = False       # CLI flag 控制
PLAN_APPROVAL_MAX_REVISIONS = 3         # 用户最多让 Supervisor 改几次

# ---- RAG 混合检索 ----
HYBRID_RETRIEVAL_ENABLED = True
HYBRID_RRF_K = 60                       # RRF 融合参数,默认 60 不用调
KB_CANDIDATE_K = 20                     # dense 召回候选数
KB_RERANK_ENABLED = True                # KB 路径加 cross-encoder 重排
KB_FINAL_TOP_K = 3                      # 重排后返回数量(保持与旧版一致)

# ---- 上下文检索 (Contextual Retrieval) ----
CONTEXTUAL_RETRIEVAL_ENABLED = True
CHUNK_MAX_CHARS = 1200                  # 单文档超过此长度才切块,否则整篇当一个 chunk

# ---- 任务分配 ----
SUBAGENT_MAX_CONCURRENCY = 5            # 原 3,放宽以支持动态数量(1~5)
```

### 1.2 `run_test.py` 入口 CLI 改造

在 `run_test.py` 顶部 import 区追加:

```python
import argparse
```

替换原来"读取课题"的硬编码块为以下函数,并把课题、所有开关传给后续流程:

```python
def parse_cli_args():
    parser = argparse.ArgumentParser(
        description="Deep Research Agent — 多智能体深度研究系统"
    )
    parser.add_argument(
        "topic",
        nargs="?",
        default=None,
        help="研究课题(也可省略,运行时交互输入)"
    )

    # ---- 推理深度 ----
    parser.add_argument(
        "--reasoning-effort",
        choices=["high", "max"],
        default=None,
        help="Supervisor 推理档位(默认读 config.py,通常 max)"
    )
    parser.add_argument(
        "--researcher-effort",
        choices=["high", "max"],
        default=None,
        help="Researcher 推理档位(默认 high)"
    )

    # ---- 长思考整体开关(便捷别名)----
    # --long-thinking 等价于把所有 agent 都设到 max
    # --short-thinking 等价于全部设到 high
    parser.add_argument(
        "--long-thinking",
        action="store_true",
        help="便捷开关:Supervisor / Researcher / Critic 全部跑 max 档"
    )
    parser.add_argument(
        "--short-thinking",
        action="store_true",
        help="便捷开关:全部跑 high 档(更省 token)"
    )

    # ---- Critic ----
    parser.add_argument(
        "--enable-critic",
        action="store_true",
        help="开启 critic 反思回路:报告初稿后自评 → 定向补研究 → 修订"
    )
    parser.add_argument(
        "--critic-rounds",
        type=int,
        default=None,
        help="critic 最多轮数(默认 1)"
    )

    # ---- HITL ----
    parser.add_argument(
        "--interactive-plan",
        action="store_true",
        help="开启 Human-in-the-Loop 计划审批:Supervisor 出计划后等用户批准/修改"
    )

    # ---- 搜索/分配 ----
    parser.add_argument(
        "--max-searches",
        type=int,
        default=None,
        help="单个 researcher 搜索上限(默认 15)"
    )
    parser.add_argument(
        "--max-researchers",
        type=int,
        default=None,
        help="并发 researcher 数量上限(默认 5)"
    )

    # ---- RAG 开关(主要用于调试)----
    parser.add_argument("--no-hybrid-kb", action="store_true", help="关闭混合检索,只用 dense")
    parser.add_argument("--no-rerank-kb", action="store_true", help="关闭 KB 重排")
    parser.add_argument("--no-contextual-rag", action="store_true", help="关闭上下文检索头生成")

    # ---- 其它 ----
    parser.add_argument("--debug", action="store_true", help="打印 thinking 内容、检索详情等")

    return parser.parse_args()


def apply_cli_to_config(args):
    """把 CLI 参数写回 config 模块的全局常量"""
    from deep_research import config as cfg

    # 长/短思考便捷开关
    if args.long_thinking:
        cfg.REASONING_EFFORT_SUPERVISOR = "max"
        cfg.REASONING_EFFORT_RESEARCHER = "max"
        cfg.REASONING_EFFORT_CRITIC = "max"
    elif args.short_thinking:
        cfg.REASONING_EFFORT_SUPERVISOR = "high"
        cfg.REASONING_EFFORT_RESEARCHER = "high"
        cfg.REASONING_EFFORT_CRITIC = "high"

    # 精细覆盖
    if args.reasoning_effort:
        cfg.REASONING_EFFORT_SUPERVISOR = args.reasoning_effort
    if args.researcher_effort:
        cfg.REASONING_EFFORT_RESEARCHER = args.researcher_effort

    if args.enable_critic:
        cfg.CRITIC_ENABLED = True
    if args.critic_rounds is not None:
        cfg.CRITIC_MAX_ROUNDS = args.critic_rounds

    if args.interactive_plan:
        cfg.INTERACTIVE_PLAN_APPROVAL = True

    if args.max_searches is not None:
        cfg.RESEARCHER_SEARCH_LIMIT = args.max_searches
    if args.max_researchers is not None:
        cfg.SUBAGENT_MAX_CONCURRENCY = args.max_researchers

    if args.no_hybrid_kb:
        cfg.HYBRID_RETRIEVAL_ENABLED = False
    if args.no_rerank_kb:
        cfg.KB_RERANK_ENABLED = False
    if args.no_contextual_rag:
        cfg.CONTEXTUAL_RETRIEVAL_ENABLED = False

    cfg.DEBUG = bool(args.debug)
```

在 `main()` / `__main__` 入口调用:

```python
if __name__ == "__main__":
    args = parse_cli_args()
    apply_cli_to_config(args)

    topic = args.topic or input("请输入研究课题: ").strip()
    # ...原来的运行逻辑,topic 用上面这个变量
```

### 1.3 用例

```bash
# 默认(Supervisor max, researcher high,不开 critic、不开 HITL)
python run_test.py "多模态大模型架构"

# 全档拉满 + critic + HITL,深度研究模式
python run_test.py "AI Agent 范式" --long-thinking --enable-critic --interactive-plan

# 调试 RAG:关掉混合检索看 dense-only 的 baseline
python run_test.py "测试课题" --no-hybrid-kb --debug

# 省 token 模式
python run_test.py "简单查询" --short-thinking
```

---

## 2. RAG 升级:混合检索 + 上下文检索 + KB 重排

### 2.1 核心思路回顾

- **混合检索**:dense(BGE-M3 语义)+ sparse(BGE-M3 词法 `lexical_weights`),用 RRF 融合排名
- **上下文检索**:索引前用 Summarizer LLM 给每个 chunk 生成"这是关于 X、属于 Y"的上下文头,prepend 后再嵌入
- **KB 重排**:dense 召回 top-20 → 计算 sparse 分 → RRF 融合 → cross-encoder 重排 → top-3

### 2.2 `knowledge_base.py` 全面改造

#### 2.2.1 顶部 import 与 BGE-M3 双模式加载

把原来用 `sentence-transformers` 加载 BGE-M3 的逻辑替换为 `FlagEmbedding`(BGE-M3 官方 SDK,原生支持 dense+sparse+colbert 一次出):

```python
# 原(可能是):
# from sentence_transformers import SentenceTransformer
# _embedder = SentenceTransformer("BAAI/bge-m3")

# 改为:
from FlagEmbedding import BGEM3FlagModel
import json
import hashlib
import threading
from typing import List, Dict, Tuple, Optional

_bge_m3_model = None
_bge_m3_lock = threading.Lock()

def get_bge_m3():
    """延迟加载 BGE-M3,支持 dense + sparse + colbert 一次前向"""
    global _bge_m3_model
    if _bge_m3_model is None:
        with _bge_m3_lock:
            if _bge_m3_model is None:
                _bge_m3_model = BGEM3FlagModel(
                    "BAAI/bge-m3",
                    use_fp16=True,   # 加速;CPU 环境可设 False
                )
    return _bge_m3_model


def encode_doc(text: str) -> Dict:
    """编码文档:同时产出 dense 和 sparse"""
    model = get_bge_m3()
    out = model.encode(
        [text],
        return_dense=True,
        return_sparse=True,
        return_colbert_vecs=False,   # colbert 暂时不用,留作未来扩展
    )
    return {
        "dense": out["dense_vecs"][0].tolist(),
        "sparse": {str(k): float(v) for k, v in out["lexical_weights"][0].items()},
    }


def encode_query(text: str) -> Dict:
    """编码查询:同上"""
    return encode_doc(text)
```

> **依赖说明**:`pip install -U FlagEmbedding`。该库与 sentence-transformers 不冲突;cross-encoder 重排(`rerank.py`)可保持现状用 sentence-transformers 的 `CrossEncoder`。

#### 2.2.2 索引函数 `index_document` 改造

```python
def _chunk_text(text: str, max_chars: int) -> List[str]:
    """简单结构化切块。优先按段落 (\n\n) 切,过长再按句号切。
    当前归档摘要通常 <1200 字,会返回 [text] 一块(即整篇当 chunk)。
    """
    if len(text) <= max_chars:
        return [text.strip()]

    # 按段落切
    paras = [p.strip() for p in text.split("\n\n") if p.strip()]
    chunks, buf = [], ""
    for p in paras:
        if len(buf) + len(p) + 2 <= max_chars:
            buf = (buf + "\n\n" + p).strip()
        else:
            if buf:
                chunks.append(buf)
            # 单段超长则按句号兜底切
            if len(p) > max_chars:
                sents = p.replace("。", "。\n").split("\n")
                tmp = ""
                for s in sents:
                    if len(tmp) + len(s) <= max_chars:
                        tmp += s
                    else:
                        if tmp: chunks.append(tmp)
                        tmp = s
                if tmp: chunks.append(tmp)
                buf = ""
            else:
                buf = p
    if buf:
        chunks.append(buf)
    return chunks


def _generate_contextual_header(
    full_doc_text: str,
    chunk_text: str,
    topic: str,
    category: str,
) -> str:
    """调 Summarizer LLM 为单个 chunk 生成一句上下文头。
    遵循 Anthropic Contextual Retrieval:说清楚这是关于什么、在文档里处于什么位置。
    """
    from deep_research.summarizer import call_summarizer_llm  # 复用既有 LLM 客户端

    prompt = f"""<document>
{full_doc_text}
</document>

<chunk>
{chunk_text}
</chunk>

为了改进检索,请用 1-2 句话(不超过 80 字)写一个"上下文锚点",说明:
1. 这个 chunk 是关于什么的
2. 它在整个文档(主题:{topic};分类:{category})里讨论的是哪个侧面
3. 包含哪些关键实体/概念名(模型名、技术名、机构名等,如有)

直接输出这一两句话,不要任何前缀、引号或解释。"""

    try:
        header = call_summarizer_llm(prompt, max_tokens=200).strip()
        return header
    except Exception as e:
        # 优雅降级:生成失败就用一个最小占位
        return f"关于「{topic}」(分类:{category})的研究内容片段。"


def index_document(file_path: str, category: str, topic: str, date_str: str):
    """索引一个归档文档。对外签名保持兼容(若旧版只传 file_path,补默认即可)。"""
    import os
    from deep_research import config as cfg

    with open(file_path, "r", encoding="utf-8") as f:
        full_text = f.read()

    parent_id = hashlib.md5(file_path.encode()).hexdigest()

    # 1. 切块(短文档→1 块)
    chunks = _chunk_text(full_text, cfg.CHUNK_MAX_CHARS)

    # 2. 为每块生成 contextual header(可关)
    headers = []
    for c in chunks:
        if cfg.CONTEXTUAL_RETRIEVAL_ENABLED:
            headers.append(_generate_contextual_header(full_text, c, topic, category))
        else:
            headers.append("")

    # 3. 编码并 upsert
    collection = get_collection()  # 你现有的 Chroma collection 获取函数

    ids, docs, embeds, metas = [], [], [], []
    for idx, (chunk, header) in enumerate(zip(chunks, headers)):
        text_to_embed = (header + "\n\n" + chunk) if header else chunk
        enc = encode_doc(text_to_embed)

        chunk_id = f"{parent_id}_{idx}"
        ids.append(chunk_id)
        docs.append(chunk)   # 注意:Chroma 里存原文 chunk,header 不存进 document
        embeds.append(enc["dense"])
        metas.append({
            "parent_id": parent_id,
            "chunk_index": idx,
            "chunk_total": len(chunks),
            "source_path": file_path,
            "category": category,
            "topic": topic,
            "date": date_str,
            "contextual_header": header,
            "sparse_weights": json.dumps(enc["sparse"], ensure_ascii=False),
            "indexed_with_contextual": cfg.CONTEXTUAL_RETRIEVAL_ENABLED,
        })

    # 复用你现有的并发锁 / Windows 重试机制
    with _chroma_lock:
        for attempt in range(3):
            try:
                collection.upsert(ids=ids, documents=docs, embeddings=embeds, metadatas=metas)
                break
            except Exception as e:
                if attempt == 2:
                    raise
                import time; time.sleep(0.5 * (2 ** attempt))
    return len(chunks)
```

#### 2.2.3 查询函数 `search_kb` 改造(混合检索 + 重排 + 父文档去重)

```python
def _sparse_score(q_sparse: Dict[str, float], d_sparse: Dict[str, float]) -> float:
    """BGE-M3 lexical_weights 之间的稀疏点积"""
    if not q_sparse or not d_sparse:
        return 0.0
    common = set(q_sparse.keys()) & set(d_sparse.keys())
    return sum(q_sparse[t] * d_sparse[t] for t in common)


def _rrf_fuse(dense_ranking: List[str], sparse_ranking: List[str], k: int) -> List[Tuple[str, float]]:
    """Reciprocal Rank Fusion。输入两路按相关度降序的 chunk_id 列表,输出融合后排序"""
    scores: Dict[str, float] = {}
    for rank, cid in enumerate(dense_ranking):
        scores[cid] = scores.get(cid, 0.0) + 1.0 / (k + rank + 1)
    for rank, cid in enumerate(sparse_ranking):
        scores[cid] = scores.get(cid, 0.0) + 1.0 / (k + rank + 1)
    return sorted(scores.items(), key=lambda x: -x[1])


def search_kb(query: str, top_k: int = 3, category: Optional[str] = None) -> List[Dict]:
    """主入口:hybrid → rerank → 父文档去重 → top_k"""
    from deep_research import config as cfg

    # 1. 编码查询
    q_enc = encode_query(query)

    # 2. dense 召回 top-K 候选
    where = {"category": category} if category else None
    collection = get_collection()
    dense_res = collection.query(
        query_embeddings=[q_enc["dense"]],
        n_results=cfg.KB_CANDIDATE_K,
        where=where,
    )

    if not dense_res["ids"] or not dense_res["ids"][0]:
        return []

    cand_ids = dense_res["ids"][0]
    cand_docs = dense_res["documents"][0]
    cand_metas = dense_res["metadatas"][0]
    cand_dists = dense_res["distances"][0]

    id_to_payload = {
        cid: {"doc": d, "meta": m, "dense_dist": dist}
        for cid, d, m, dist in zip(cand_ids, cand_docs, cand_metas, cand_dists)
    }

    # 3. 混合 or 纯 dense
    if cfg.HYBRID_RETRIEVAL_ENABLED:
        sparse_pairs = []
        for cid, payload in id_to_payload.items():
            d_sparse = json.loads(payload["meta"].get("sparse_weights", "{}"))
            s = _sparse_score(q_enc["sparse"], d_sparse)
            sparse_pairs.append((cid, s))
        sparse_ranking = [cid for cid, _ in sorted(sparse_pairs, key=lambda x: -x[1])]
        dense_ranking = cand_ids  # Chroma 已按距离升序返回 = 相关度降序
        fused = _rrf_fuse(dense_ranking, sparse_ranking, k=cfg.HYBRID_RRF_K)
        ranked_ids = [cid for cid, _ in fused]
    else:
        ranked_ids = cand_ids

    # 4. 重排(可关)
    if cfg.KB_RERANK_ENABLED:
        from deep_research.rerank import get_reranker  # 你现成的 cross-encoder loader
        reranker = get_reranker()
        pairs = [(query, id_to_payload[cid]["doc"]) for cid in ranked_ids]
        scores = reranker.predict(pairs)
        ranked_ids = [cid for cid, _ in sorted(zip(ranked_ids, scores), key=lambda x: -x[1])]

    # 5. 父文档去重(同一 parent_id 只保留最高排名那块,避免一篇刷屏)
    seen_parents = set()
    final = []
    for cid in ranked_ids:
        meta = id_to_payload[cid]["meta"]
        pid = meta["parent_id"]
        if pid in seen_parents:
            continue
        seen_parents.add(pid)
        final.append({
            "text": id_to_payload[cid]["doc"],
            "category": meta.get("category", ""),
            "date": meta.get("date", ""),
            "topic": meta.get("topic", ""),
            "contextual_header": meta.get("contextual_header", ""),
            "score": 1.0 - id_to_payload[cid]["dense_dist"],  # 兼容旧接口
        })
        if len(final) >= top_k:
            break

    return final
```

### 2.3 `tools.py` 的 `search_knowledge_base` 工具适配

只要旧函数签名调用的是 `search_kb(query, top_k)`,基本不用改外层。把返回的格式化字符串里**新增 `contextual_header`** 一行(给研究员更清楚的语境):

```python
@tool
def search_knowledge_base(query: str, category: Optional[str] = None) -> str:
    from deep_research import config as cfg
    results = search_kb(query, top_k=cfg.KB_FINAL_TOP_K, category=category)
    if not results:
        return "【知识库无相关结果】"

    out = []
    for i, r in enumerate(results, 1):
        header_line = f"【上下文】{r['contextual_header']}\n" if r.get("contextual_header") else ""
        out.append(
            f"--- 内部历史研究 [{i}] ---\n"
            f"分类: {r['category']} | 日期: {r['date']} | 相关度: {r['score']:.3f}\n"
            f"{header_line}"
            f"{r['text']}\n"
        )
    return "\n".join(out)
```

### 2.4 `summarizer.py`:暴露一个 `call_summarizer_llm` 入口

如果你现在的 summarizer 是一个大函数,把它内部对 LLM 的调用拆出来一个可复用入口:

```python
def call_summarizer_llm(prompt: str, max_tokens: int = 2048) -> str:
    """对外暴露,供 knowledge_base 生成 contextual header 等场景复用"""
    # ...复用你现有的 DeepSeek OpenAI 兼容客户端...
    # 注意:contextual header 生成属于轻量任务,可强制 reasoning_effort="high",
    # 或者干脆禁 thinking 提速:extra_body={"thinking": {"type": "disabled"}}
    response = client.chat.completions.create(
        model=cfg.SUMMARIZE_MODEL,
        messages=[{"role": "user", "content": prompt}],
        max_tokens=max_tokens,
        extra_body={"thinking": {"type": "disabled"}},  # contextual header 不需要思考
    )
    return response.choices[0].message.content
```

### 2.5 `build_index.py` 兼容老库的迁移

老库里的文档没有 `sparse_weights` / `contextual_header` / `parent_id` / `chunk_index` 这些字段。Claude Code 加一个**一次性迁移命令**:

```python
# build_index.py 新增子命令
def rebuild_all():
    """删除并重建整个向量库。会用新的 contextual + sparse 字段。"""
    import shutil, os
    from deep_research import config as cfg
    from deep_research.knowledge_base import index_document

    if os.path.exists(cfg.VECTOR_STORE_DIR):
        shutil.rmtree(cfg.VECTOR_STORE_DIR)

    count = 0
    for category_dir in os.listdir(cfg.HISTORY_DB_DIR):
        full_cat = os.path.join(cfg.HISTORY_DB_DIR, category_dir)
        if not os.path.isdir(full_cat):
            continue
        for fn in os.listdir(full_cat):
            if not fn.endswith(".txt"):
                continue
            path = os.path.join(full_cat, fn)
            # 从文件名提取日期 + 课题
            date_str = fn[:10] if len(fn) >= 10 else "unknown"
            topic = fn[11:-4] if len(fn) > 14 else fn[:-4]
            index_document(path, category=category_dir, topic=topic, date_str=date_str)
            count += 1
    print(f"重建完成:索引 {count} 个文档")


if __name__ == "__main__":
    import sys
    if "--rebuild" in sys.argv:
        rebuild_all()
    else:
        # 原行为
        ...
```

执行一次:`python build_index.py --rebuild`

---

## 3. 推理深度:reasoning_effort 控制 + 透传验证

### 3.1 `agent.py` / `subagents.py`:模型工厂分角色

把所有"`ChatOpenAI(...)`"实例化集中到一个工厂函数。**关键:不同角色拿不同的 `reasoning_effort`。**

```python
# agent.py(或新建 deep_research/model_factory.py)
from langchain_openai import ChatOpenAI
from deep_research import config as cfg


def make_chat_model(role: str = "default") -> ChatOpenAI:
    """
    role: "supervisor" | "researcher" | "critic" | "default"
    """
    effort_map = {
        "supervisor": cfg.REASONING_EFFORT_SUPERVISOR,
        "researcher": cfg.REASONING_EFFORT_RESEARCHER,
        "critic": cfg.REASONING_EFFORT_CRITIC,
    }
    effort = effort_map.get(role, "high")

    extra_body = {}
    if cfg.THINKING_ENABLED:
        extra_body["thinking"] = {"type": "enabled"}

    model_kwargs = {
        "extra_body": extra_body,
    }
    if cfg.THINKING_ENABLED:
        # 注意:thinking 模式下 temperature/top_p/penalty 静默忽略,
        # 这里不设它们,避免迷惑。
        pass

    return ChatOpenAI(
        model=cfg.AGENT_MODEL,
        api_key=cfg.DEEPSEEK_API_KEY,
        base_url=cfg.DEEPSEEK_BASE_URL,
        timeout=cfg.REQUEST_TIMEOUT,
        max_tokens=cfg.THINKING_MAX_OUTPUT_TOKENS if cfg.THINKING_ENABLED else 4096,
        reasoning_effort=effort,
        model_kwargs=model_kwargs,
    )
```

然后在组装 Supervisor / Researcher 的地方分别用 `make_chat_model("supervisor")` / `make_chat_model("researcher")` / `make_chat_model("critic")`。

### 3.2 ⚠️ 关键:验证 reasoning_content 透传(可能是"思考浅"的真正原因)

DeepSeek 官方文档明确:**thinking 模式下,工具调用场景的 `reasoning_content` 必须在后续每一轮请求里回传**。如果 LangChain 的 ChatOpenAI 在工具循环里把它丢了,模型每一轮等于失忆重来——这会让 agent 看起来"怎么都想不深"。

**Claude Code 需要执行的诊断步骤**(写一个 `scripts/diagnose_reasoning_passback.py`):

```python
"""
诊断 reasoning_content 是否在工具调用循环中被保留。
跑法:python scripts/diagnose_reasoning_passback.py
"""
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, AIMessage, ToolMessage
from langchain_core.tools import tool
from deep_research import config as cfg


@tool
def dummy_search(query: str) -> str:
    """假搜索工具,用于触发工具调用"""
    return f"关于'{query}'的搜索结果:42"


llm = ChatOpenAI(
    model=cfg.AGENT_MODEL,
    api_key=cfg.DEEPSEEK_API_KEY,
    base_url=cfg.DEEPSEEK_BASE_URL,
    reasoning_effort="max",
    extra_body={"thinking": {"type": "enabled"}},
    max_tokens=8000,
).bind_tools([dummy_search])

# 第一轮
msg1 = llm.invoke([HumanMessage(content="请搜索一下'宇宙的意义是什么',然后告诉我答案")])
print("=== 第一轮 AIMessage ===")
print("content:", msg1.content[:200] if msg1.content else "(空)")
print("additional_kwargs keys:", list(msg1.additional_kwargs.keys()))
print("reasoning_content present:", "reasoning_content" in msg1.additional_kwargs)
print("tool_calls:", msg1.tool_calls)

# 模拟工具返回
tool_msg = ToolMessage(
    content="42",
    tool_call_id=msg1.tool_calls[0]["id"] if msg1.tool_calls else "x",
)

# 第二轮:把 msg1 + tool_msg 喂回去
msg2 = llm.invoke([
    HumanMessage(content="请搜索一下'宇宙的意义是什么',然后告诉我答案"),
    msg1,
    tool_msg,
])
print("\n=== 第二轮 AIMessage ===")
print("content:", msg2.content[:300] if msg2.content else "(空)")
print("如果第二轮报错或 content 异常 → 框架没透传 reasoning_content")
```

**根据诊断结果**:

- ✅ 如果通过(第二轮正常):什么都不用动。
- ❌ 如果第二轮报错(报 `reasoning_content must be passed`)或质量明显塌:**实现一个消息预处理钩子**,在每次发送请求前把 `additional_kwargs["reasoning_content"]` 显式塞进 OpenAI 协议的 assistant message。最干净的做法是写一个 `BaseChatModel` 子类包装一下,在 `_generate` / `_stream` 前注入。如果 deepagents 不允许自定义模型类,退而求其次:把 `extra_body` 设为 `{"thinking": {"type": "enabled"}, "interleaved": {"field": "reasoning_content"}}`(部分 LiteLLM 兼容栈支持这个 `interleaved` 字段)。

> **给 Claude Code 的提示**:这一步不要跳过。如果跳过,后面所有"max 档"的努力可能因为透传问题白做。

---

## 4. Critic 反思回路

### 4.1 `subagents.py` 新增 critic 子智能体定义

```python
from deep_research.prompts import CRITIC_PROMPT
from deep_research.model_factory import make_chat_model

critic_subagent = {
    "name": "critic",
    "description": (
        "对 /report.md 和 /notes 做批判性审查。识别证据薄弱处、未覆盖的维度、"
        "矛盾未标注、引用不到位等问题。返回结构化的缺陷清单和补研究建议。"
        "不进行新的搜索;只读现有产物。"
    ),
    "prompt": CRITIC_PROMPT,
    "tools": ["read_file", "ls"],   # 只给读权限
    # 如果你的框架支持指定模型:
    # "model": make_chat_model("critic"),
}

# 把它加进 SUBAGENTS 列表
SUBAGENTS = [researcher_1, researcher_2, researcher_3, critic_subagent]
```

### 4.2 `prompts.py` 新增 CRITIC_PROMPT

```python
CRITIC_PROMPT = """你是「批判审查员」,任务是对当前研究产出做严格的质量审查。
你**不能**做新的搜索,只能读取 /workspace 下的现有文件。

## 你的输入
- /report.md(报告初稿)
- /notes/*.md(研究员的笔记)
- /research_summary.txt(若已生成)

## 你的输出格式(必须严格遵守)

```
[CRITIC_REPORT]
总体评分: X/10(整数)

### 1. 证据薄弱点(每条注明出处段落)
- 问题:...
  位置:report.md 第 X 节 / 第 Y 段
  补救建议:需要补搜什么 → 建议查询:"..."

### 2. 未覆盖的关键维度
- 维度:...(具体说明这个维度对该课题为什么重要)
  补救建议:派一个 researcher 调研,任务简报:
    目标:...
    范围:in: ... ; out: ...
    推荐工具:...
    预算:N 次搜索

### 3. 内部矛盾 / 来源冲突
- 段落 A 说 X,段落 B 说 Y,且没有标注分歧:位置 ...
  补救建议:在 X 节加交叉验证段,或派 researcher 复核

### 4. 引用 / 格式问题
- ...(编号缺失、URL 贴正文、来源未注明等)

### 5. 报告长度/结构问题(如适用)
- ...

### 是否需要补研究 (REQUIRES_REWORK)
true / false
(若为 true,Supervisor 必须根据上面"补救建议"派出新 task。
 若评分 >= 8 且无关键维度缺失,可设为 false。)
```

## 审查原则

1. 严格但不挑刺:只列**会影响读者结论**的问题。鸡毛蒜皮的措辞别动。
2. 每个问题必须给出**具体位置 + 具体补救动作**,不要只说"不够深入"。
3. 如果某个论点的支撑只来自一个二手来源,标为"证据薄弱"。
4. 如果某个对比/范式讨论里有一个公认重要的方向被漏掉,标为"未覆盖维度"。
5. 永远在最后给一个明确的 REQUIRES_REWORK: true/false。
"""
```

### 4.3 Supervisor 调用 critic 的流程(写进 SUPERVISOR_PROMPT,见 §5)

逻辑:

```
报告初稿完成 (write_file /report.md)
   ↓
if CRITIC_ENABLED:
   task("critic", "请审查 /report.md 和 /notes")
   ↓
   读取 critic 返回的 [CRITIC_REPORT]
   ↓
   if REQUIRES_REWORK and rounds < CRITIC_MAX_ROUNDS:
       基于 critic 的"补救建议"派出新的 researcher task(可并行多个)
       ↓
       归并新笔记 → 修订 /report.md
       ↓
       (可选)再来一轮 critic
   else:
       通过 → 写 /research_summary.txt
```

### 4.4 `agent.py` 把 critic 注册进 Supervisor

确认在组装时把 `critic_subagent` 也加进 deepagents 的 subagents 列表里。Supervisor 通过 `task("critic", ...)` 自然调用。**不需要在代码层写 if/else**——`CRITIC_ENABLED` 通过 prompt 注入控制:

```python
# agent.py 里组装 Supervisor 时
supervisor_prompt = SUPERVISOR_PROMPT.format(
    critic_block=(CRITIC_INSTRUCTIONS if cfg.CRITIC_ENABLED else ""),
    hitl_block=(HITL_INSTRUCTIONS if cfg.INTERACTIVE_PLAN_APPROVAL else ""),
    max_researchers=cfg.SUBAGENT_MAX_CONCURRENCY,
    search_limit=cfg.RESEARCHER_SEARCH_LIMIT,
)
```

---

## 5. 任务分配脚手架(prompt 重写)

`prompts.py` 整体重写。两个主 prompt + 两个可选注入块。

### 5.1 `SUPERVISOR_PROMPT`(重写,使用 .format 占位符)

```python
SUPERVISOR_PROMPT = """你是「研究总监」,负责一个深度研究项目的全过程编排。
你**自己不做任何搜索**——所有信息收集委托给 researcher 子智能体。
你的全部价值在于:规划、分配、质量把关、最终成文。

# 阶段总览

1. 制定计划 (write_todos + 任务简报)
2. {hitl_block_marker_1}  ← 若启用 HITL,则有计划审批
3. 并行委托 researcher(数量动态决定)
4. 归档笔记 + 查漏补缺
5. 分节撰写报告
6. {critic_block_marker_1}  ← 若启用 critic,则做批判+修订
7. 自我批判 + 写 /research_summary.txt

---

# 阶段 1:制定计划

## 1.1 决定研究员数量(动态!)

根据课题复杂度,选择 1-{max_researchers} 个 researcher:

- **1 个**:简单事实查询(如"X 公司 2025 年营收")
- **2-4 个**:对比/范式类("A vs B 的差异","X 领域主流方法")
- **5 个(上限)**:复杂多维研究("X 领域全貌:技术+生态+商业+趋势")

不要永远派 3 个。**简单问题派多了 = 浪费 + 重复;复杂问题派少了 = 漏维度。**

## 1.2 MECE 分解

把课题拆成若干子问题,必须满足:
- **互斥 (Mutually Exclusive)**:子问题之间不能有显著重叠。如果两个子问题让两个 researcher 大概率搜同一批资料,合并它们。
- **穷尽 (Collectively Exhaustive)**:子问题合起来必须覆盖课题的所有关键维度。问自己:"如果只看这 N 个子问题的答案,读者对原课题理解全面吗?"

## 1.3 写 todos(write_todos)

简洁列出子问题清单:
```
1. [子问题 1 简述]
2. [子问题 2 简述]
...
```

## 1.4 为每个子问题写「任务简报」(关键!)

派 task() 之前,必须为每个 researcher 准备一份结构化简报。简报作为 task() 的 description 参数,**完整字段如下**:

```
[任务简报]
目标 (Objective):
  一句话说清楚这个 researcher 要回答的精确问题。
  例:"对比 LLaVA、Qwen-VL、InternVL 在视觉编码器选型与对齐方式上的差异。"

范围 (Scope):
  In:  ✅ 在这个 researcher 的工作范围内的内容(具体到点)
  Out: ❌ 不要碰的内容(这块由其它 researcher 负责或不需要)
  例:
    In:  视觉编码器架构、与文本侧的对齐机制、训练数据规模量级
    Out: 部署成本、商业授权、基准分数排行(由 researcher-2 负责)

推荐工具优先级:
  例:"先 search_knowledge_base 一次 → search_openalex(架构论文)→ web_fetch 模型卡 → web_search 补充博客分析"

预算:
  最多 {search_limit} 次网络搜索(KB 检索不计)

输出格式:
  - [发现 1]: 内容(URL/DOI)
  - [发现 2]: ...
  - [关键来源]: 列出 3-5 个最值得引用的源
  - [充分性自评]: 是否覆盖了 In-scope 的所有点 / 还有什么没弄清楚
```

**反例(以前的烂简报)**:
- "调研 LLaVA"  ← 太宽,没边界
- "找一下视觉语言模型的成功案例"  ← 太模糊,可能与别的子问题重叠

---

{hitl_block}

---

# 阶段 3:并行委托

在**同一条消息中**调用 N 次 task()(N = 你在 1.1 决定的数量),一次性派出全部 researcher。
每个 task() 的 description 就是你在 1.4 写的完整任务简报。

# 阶段 4:归档笔记 + 查漏

researcher 返回后,把内容用 write_file 写到 /notes/researcher-N.md。
然后 `ls /notes` 检查,通读所有笔记并问自己:
- 是否每个 In-scope 点都被覆盖?
- researcher 之间有没有矛盾未澄清?
- 有没有关键维度没人碰?

如果有,**再派一个 task() 定向补研究**(不要重复派全部)。

# 阶段 5:分节撰写报告

读 `/skills/academic-report/SKILL.md`,然后分 4 节增量写入 /report.md:
- 第 1 节:摘要 + 研究背景
- 第 2 节:核心发现(含对比表)
- 第 3 节:分析与讨论(矛盾标注、局限性)
- 第 4 节:结论 + 参考来源 (编号制 [1][2]...)

**绝不**在正文中贴长 URL;来源全部走编号制,在末尾参考来源章节统一列。

---

{critic_block}

---

# 阶段 7:自我批判 + 归档摘要

通读 /report.md,在末尾追加一段「Supervisor 自评」(不计入正文):
- 至少指出 1 处可以更深入的地方
- 至少指出 1 处证据相对薄弱的地方

然后写 /research_summary.txt:不含分类标签,200-500 字浓缩摘要,用于后续 RAG 入库。

---

# 工具速查

- write_todos(items): 列计划
- task(subagent_name, description): 派研究员;**注意 subagent_name 取值:researcher 或 critic**
- write_file(path, content): 写文件
- read_file(path): 读文件
- ls(dir): 列目录

# 引用铁律

- 所有外部引用必须走编号制 [N]
- 正文里**绝不**直接贴 URL
- 每个编号在末尾参考来源章节有一行完整条目(标题 + 作者/机构 + URL/DOI + 访问日期)
"""
```

### 5.2 `HITL_INSTRUCTIONS` 和 `CRITIC_INSTRUCTIONS`(条件注入块)

```python
HITL_INSTRUCTIONS = """
# 阶段 2:计划审批(HITL)

在阶段 1 完成后、阶段 3 派 researcher 之前,**必须**调用工具 `request_plan_approval`,
传入参数:
  - plan_summary:对课题的整体研究路径一句话描述
  - todos:阶段 1.3 写的 todos 列表(原样)
  - briefs:每个 researcher 的简报合并文本

用户可能的回复:
  - "approve" / "ok" / "继续":直接进入阶段 3
  - 修改建议(任何其它输入):你必须根据建议**修订 todos 和简报**,
    然后**再次调用 `request_plan_approval`** 让用户复核。
  - "abort":立即停止,不要做任何 task() 调用。

最多迭代 {plan_revisions} 轮。
"""

CRITIC_INSTRUCTIONS = """
# 阶段 6:Critic 反思回路

完成阶段 5 报告初稿后:

1. 调用 task("critic", "请审查 /report.md 和 /notes/ 下所有笔记,按 CRITIC_PROMPT 输出 [CRITIC_REPORT]")
2. 读取 critic 返回的报告,找到 REQUIRES_REWORK 字段
3. 如果 REQUIRES_REWORK = true:
   a. 根据 critic 的"补救建议",派出 1-3 个新的 researcher task()(不是重派全部,只补缺)
   b. 每个新 task 用 critic 给出的简报作为 description
   c. 等 researcher 返回,把新内容并入 /notes
   d. 修订 /report.md 相关章节(可分节增量写)
   e. 本轮反思结束
4. 如果 REQUIRES_REWORK = false:直接进入阶段 7

本回路最多 {critic_max_rounds} 轮。
"""
```

注意 `agent.py` 里 `.format(...)` 填入 `hitl_block_marker_1` / `hitl_block` / `critic_block_marker_1` / `critic_block`,占位符在不启用时填空字符串。

### 5.3 `RESEARCHER_PROMPT`(重写,加 OODA + 充分性自检)

```python
RESEARCHER_PROMPT = """你是 researcher,Supervisor 派你完成一份「任务简报」里规定的子调研。

# 你拿到的输入
任务简报里有:目标、范围 In/Out、推荐工具优先级、搜索预算、输出格式。
**严格遵守 In/Out 范围**——范围外的内容不要碰,即使有趣;由别的 researcher 负责。

# 工作循环(OODA,不要预先把所有查询列死)

不要一上来就拆 5 个固定查询然后机械执行。
按 OODA 循环工作:

1. **Observe(观察)**:目前已经搜到了什么?哪些 In-scope 的点已经清楚了?哪些还模糊?
2. **Orient(定向)**:还缺什么?该用哪个工具?学术论文 → OpenAlex/Crossref;产品/动态 → web_search;
   已有结论复用 → search_knowledge_base(只查一次,不计预算)。
3. **Decide(决策)**:写下一个具体、窄的查询。
4. **Act(行动)**:调用工具,读结果。

读完结果后**立刻回到 Observe**,根据新信息决定下一步。
不要"为查满 8 次而查"——查到够了就停。
不要"查满了就停"——还差关键点就继续(直到撞上预算上限)。

# 搜索预算

最多 {search_limit} 次网络搜索(web_search + search_openalex + search_crossref 合计)。
search_knowledge_base 不计入。

# 充分性自检(强制!)

每用满 1/3 的预算时,问自己:
- 任务简报的 In-scope 点,**每一条**都有支撑了吗?
- 我准备返回的内容,对 Supervisor 写出该子问题的章节够用吗?
- 是否还有关键论文/官方文档我没读到?

如果发现某个 In-scope 点没支撑,**优先补它**,不要去搜锦上添花的东西。

# 输出格式(严格)

工作结束后,返回结构化摘要:

```
[进度] 用了 N 次搜索 / {search_limit} 预算

[核心发现]
- 发现 1:具体论点(URL 或 DOI)
- 发现 2:...
- 发现 N:...

[关键来源]
1. 标题 — 作者/机构 — URL/DOI — 日期
2. ...

[充分性自评]
- In-scope 覆盖情况:✅ 点 A / ✅ 点 B / ⚠️ 点 C(原因:...)
- 我没能确认的事:...(若无,写"无")
- 建议 Supervisor 注意:...(若无,写"无")

[完成]
```

# 工具使用要点

- search_knowledge_base:**第一步**先查一次。命中(score > 0.5)就用上,标注为"内部历史结论,需复核"。
- web_fetch:如果 3 次失败就放弃这个 URL,换别的源。
- 学术内容优先 OpenAlex / Crossref,避免低质量内容农场。
- 给查询加年份(2024 / 2025 / 2026),除非是历史性问题。

# 严禁

- ❌ 范围外的内容(即使发现了也不要写)
- ❌ 没有 URL/DOI 的论断(除非显式标注"无来源,个人推理")
- ❌ 整段复制原文(超过 15 字)→ 全部 paraphrase
"""
```

---

## 6. Human-in-the-Loop 计划审批

### 6.1 在 `tools.py` 新增 `request_plan_approval` 工具

```python
from langchain_core.tools import tool

@tool
def request_plan_approval(plan_summary: str, todos: str, briefs: str) -> str:
    """
    暂停研究流程,把当前计划展示给用户,等用户批准或给出修改建议。

    参数:
      plan_summary: 一句话整体研究路径
      todos:       子问题清单(write_todos 的内容)
      briefs:      所有 researcher 的任务简报合并文本

    返回:
      用户输入的字符串。约定:
        - "approve" / "ok" / "继续" / 空回车 → Supervisor 直接进入阶段 3
        - 任何其它内容 → 视为修改建议,Supervisor 必须据此修订并再次调用本工具
        - "abort" / "stop" / "取消" → Supervisor 必须立即停止
    """
    print("\n" + "=" * 60)
    print("【计划审批 HITL】")
    print("=" * 60)
    print(f"\n📋 研究路径:\n{plan_summary}\n")
    print(f"📌 子问题清单:\n{todos}\n")
    print(f"📦 任务简报:\n{briefs}\n")
    print("-" * 60)
    print("请输入:")
    print("  • 回车 / 'approve' / 'ok' → 批准并继续")
    print("  • 任意修改建议 → 让 Supervisor 修订")
    print("  • 'abort' → 取消整个研究")
    print("-" * 60)

    try:
        user_input = input(">>> ").strip()
    except (EOFError, KeyboardInterrupt):
        return "abort"

    if not user_input or user_input.lower() in {"approve", "ok", "yes", "y", "继续", "通过"}:
        return "APPROVED"
    if user_input.lower() in {"abort", "stop", "cancel", "取消", "终止"}:
        return "ABORTED"
    return f"REVISE: {user_input}"
```

### 6.2 把工具注册到 Supervisor

`agent.py` 组装 Supervisor 时,工具列表加入 `request_plan_approval`(**只给 Supervisor,不要给 researcher**):

```python
supervisor_tools = [
    write_todos, task, write_file, read_file, ls,
]
if cfg.INTERACTIVE_PLAN_APPROVAL:
    supervisor_tools.append(request_plan_approval)
```

### 6.3 SUPERVISOR_PROMPT 里的 HITL 注入块已在 §5.2 写好

确认 `agent.py` 的 prompt 渲染:

```python
hitl_block_text = HITL_INSTRUCTIONS.format(
    plan_revisions=cfg.PLAN_APPROVAL_MAX_REVISIONS
) if cfg.INTERACTIVE_PLAN_APPROVAL else ""

supervisor_prompt = SUPERVISOR_PROMPT.format(
    max_researchers=cfg.SUBAGENT_MAX_CONCURRENCY,
    search_limit=cfg.RESEARCHER_SEARCH_LIMIT,
    hitl_block=hitl_block_text,
    hitl_block_marker_1="计划审批" if cfg.INTERACTIVE_PLAN_APPROVAL else "(未启用)",
    critic_block=(CRITIC_INSTRUCTIONS.format(critic_max_rounds=cfg.CRITIC_MAX_ROUNDS)
                  if cfg.CRITIC_ENABLED else ""),
    critic_block_marker_1="Critic 反思" if cfg.CRITIC_ENABLED else "(未启用)",
)
```

### 6.4 异步/流式输出注意

如果你的 `run_test.py` 用了 `astream_events` / `astream`,`input()` 阻塞会卡住事件循环。两种处理:

- **方案 A(推荐)**:把 `request_plan_approval` 内部的 `input()` 包到一个线程里:
  ```python
  import asyncio
  loop = asyncio.get_event_loop()
  user_input = loop.run_in_executor(None, input, ">>> ")
  ```
  但更简单的方案是用同步 `input()` + 在 agent 的 stream 配置里允许工具同步执行(deepagents/LangGraph 默认行为通常 OK)。

- **方案 B**:把整个 run 改成同步 (`agent.invoke(...)`),HITL 启用时不走流式。可以通过 CLI 检测:`--interactive-plan` 启用时自动切到 sync 模式。

Claude Code 实操时先用方案 A,跑通后看是否需要 B。

---

## 7. CLI 完整设计速查

```bash
# 基础
python run_test.py "课题"

# 长思考(等价于 supervisor/researcher/critic 全部 max)
python run_test.py "课题" --long-thinking

# 短思考(全部 high,省 token)
python run_test.py "课题" --short-thinking

# 精细控制
python run_test.py "课题" --reasoning-effort max --researcher-effort high

# 深度模式:长思考 + critic + HITL 审批
python run_test.py "课题" --long-thinking --enable-critic --interactive-plan

# 调宽预算
python run_test.py "复杂课题" --max-searches 20 --max-researchers 5

# 调试 RAG
python run_test.py "课题" --no-hybrid-kb --debug
python run_test.py "课题" --no-rerank-kb
python run_test.py "课题" --no-contextual-rag

# 重建向量库(老库迁移到新 schema)
python build_index.py --rebuild
```

---

## 8. Smoke Tests / 验收清单

Claude Code 实施完成后,逐项跑通:

### 8.1 配置 & CLI
- [ ] `python run_test.py --help` 显示所有新 flag
- [ ] `--long-thinking` 启动后,日志确认 Supervisor/Researcher 的 reasoning_effort = "max"
- [ ] `--short-thinking` 启动后,所有 effort = "high"

### 8.2 RAG 升级
- [ ] `python build_index.py --rebuild` 跑通,无报错,新 metadata 字段就位
- [ ] 检查 Chroma 里某条记录的 metadata,有 `sparse_weights`、`contextual_header`、`parent_id`、`chunk_index`
- [ ] 跑一次研究,在 debug 模式下打印 `search_kb` 调用,确认走了 dense+sparse+rerank 三步
- [ ] `--no-hybrid-kb` 时只走 dense(对照)
- [ ] `--no-contextual-rag` 时索引新文档,该文档 metadata 里 `contextual_header` 为空

### 8.3 推理深度
- [ ] 跑 `scripts/diagnose_reasoning_passback.py`,确认结果(过/不过)
- [ ] 若过:`--long-thinking` 比 `--short-thinking` 在同一课题上,看 thinking 内容明显变长(debug 模式可见 `reasoning_content`)
- [ ] 若不过:实现透传 fix 后,再验

### 8.4 Critic
- [ ] `--enable-critic` 时,日志里能看到 `task("critic", ...)` 调用
- [ ] critic 返回包含 `[CRITIC_REPORT]` 块
- [ ] 当 REQUIRES_REWORK=true 时,看到 Supervisor 派出新的补研究 task
- [ ] 当 REQUIRES_REWORK=false 时,直接进入归档阶段

### 8.5 HITL
- [ ] `--interactive-plan` 时,Supervisor 出计划后会暂停等输入
- [ ] 输入回车 → 直接继续
- [ ] 输入"把子问题 2 改成 X" → Supervisor 据此修订,再次询问
- [ ] 输入"abort" → 整个 run 立即终止,不产 report
- [ ] 不加 `--interactive-plan` 时,完全不弹出审批(向后兼容)

### 8.6 端到端
- [ ] 跑一次"老用法"(`python run_test.py "课题"`)不加任何 flag,行为与旧版基本一致(只是 KB 检索质量更好)
- [ ] 跑一次完整深度模式(`--long-thinking --enable-critic --interactive-plan --max-searches 20`),总耗时 20-40 分钟,产出报告字数比旧版增加 30% 以上,引用数翻倍

---

## 9. 实施顺序建议给 Claude Code 的总命令

```
按以下顺序提交 commit:

commit 1: feat(config): 新增推理/RAG/HITL/Critic 配置项 + CLI 解析
  - deep_research/config.py
  - run_test.py 的 parse_cli_args / apply_cli_to_config

commit 2: feat(rag): BGE-M3 hybrid + contextual retrieval + KB rerank
  - deep_research/knowledge_base.py(主要工作)
  - deep_research/summarizer.py(暴露 call_summarizer_llm)
  - deep_research/tools.py(search_knowledge_base 输出格式更新)
  - build_index.py(--rebuild 子命令)

commit 3: feat(model): 模型工厂分角色 + reasoning_effort 控制
  - deep_research/model_factory.py(新文件)或 agent.py 内函数
  - deep_research/agent.py(消费工厂)
  - deep_research/subagents.py(消费工厂)
  - scripts/diagnose_reasoning_passback.py(诊断脚本)

commit 4: feat(prompts): 重写 SUPERVISOR / RESEARCHER prompt + 新增 CRITIC
  - deep_research/prompts.py 全文重写

commit 5: feat(critic): 新增 critic 子智能体 + 注册
  - deep_research/subagents.py
  - deep_research/agent.py

commit 6: feat(hitl): request_plan_approval 工具 + Supervisor 注册
  - deep_research/tools.py
  - deep_research/agent.py
  - (可能)run_test.py 同步模式分支

commit 7: test: smoke tests + 文档
  - scripts/ 下的小测试
  - README 更新 CLI 速查
```

---

## 10. 已知风险与回滚预案

| 风险 | 触发 | 回滚方式 |
|------|------|---------|
| 新 RAG 性能反而下降 | 6 文档小库下 RRF + rerank 可能略嘈杂 | `--no-hybrid-kb --no-rerank-kb` 退回旧行为 |
| FlagEmbedding 与现有 sentence-transformers 冲突 | import 顺序 / CUDA 版本 | 把 cross-encoder 也迁到 FlagEmbedding(它有自己的 FlagReranker);或保持两套并存 |
| reasoning_content 透传失败 | LangChain DeepSeek 适配器问题 | 见 §3.2 兜底方案;最坏情况 `--short-thinking` 跑 high 档,仍是推理模型 |
| HITL 在异步流式下死锁 | input() 卡 event loop | §6.4 方案 B,HITL 启用时强制同步 |
| Critic 把简单课题判为 REQUIRES_REWORK=true 浪费 token | critic prompt 太严 | `--critic-rounds 0`(等于关掉),或调 CRITIC_PROMPT 的"严格但不挑刺"加强 |
| max 档 token 消耗 ~3-5x | 成本敏感场景 | `--short-thinking` 或精细只对 supervisor 用 max |

---

## 11. 一句话总结

把推理调到 max、把搜索停止从计数改成充分性、给 critic 加一道关、给 Supervisor 一份正经的分配脚本(MECE + 任务简报 + 动态数量),再让 RAG 用上 BGE-M3 本来就会的 sparse、复用现成的 cross-encoder、利用现成的 Summarizer 给每个 chunk 加上下文头——这就是这次改进的全部。架构没动,组件全是你现有的,只是把它们用对了。
