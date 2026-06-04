# -*- coding: utf-8 -*-
"""本地向量知识库 v2.0：混合检索 + 上下文检索 + KB 重排。

升级点：
- BGE-M3 改用 FlagEmbedding 官方 SDK，一次前向出 dense+sparse+colbert
- 混合检索: dense(BGE-M3) + sparse(lexical_weights) + RRF 融合
- 上下文检索: 索引前调 Summarizer LLM 给每个 chunk 生成 context header
- KB 重排: dense 召回 top-20 → sparse → RRF → cross-encoder → top-3
- 父文档去重: 同一归档文件多 chunk 只保留最高排名那条

内存: BGE-M3(~1.2GB) + bge-reranker(~300MB) 同时加载约 1.5-2GB
"""

import json
import hashlib
import threading
import time as _time
from pathlib import Path
from typing import Optional

from .config import (
    EMBEDDING_MODEL,
    VECTOR_STORE_DIR,
    VECTOR_COLLECTION,
    RAG_TOP_K,
    RAG_ENABLED,
    HYBRID_RETRIEVAL_ENABLED,
    HYBRID_RRF_K,
    KB_CANDIDATE_K,
    KB_RERANK_ENABLED,
    KB_FINAL_TOP_K,
    CONTEXTUAL_RETRIEVAL_ENABLED,
    CHUNK_MAX_CHARS,
)

# ── 线程安全 ────────────────────────────────────────────
_bge_lock = threading.Lock()
_collection_lock = threading.Lock()
_bge_model = None


# ── BGE-M3 模型加载 (双模式) ────────────────────────────

def _get_sentence_transformer():
    """sentence-transformers 加载 BGE-M3（dense 嵌入，已有本地缓存）。"""
    from sentence_transformers import SentenceTransformer
    return SentenceTransformer(EMBEDDING_MODEL)


_bge_flag = None

def _get_flag_model():
    """FlagEmbedding 加载 BGE-M3（sparse lexical_weights）。
    首次需联网下载 ~1.2GB，失败时返回 None，退化为纯 dense 模式。
    """
    global _bge_flag
    if _bge_flag is None:
        with _bge_lock:
            if _bge_flag is None:
                try:
                    from FlagEmbedding import BGEM3FlagModel
                    _bge_flag = BGEM3FlagModel(EMBEDDING_MODEL, use_fp16=True)
                except Exception:
                    _bge_flag = False  # 标记为不可用
    return _bge_flag if _bge_flag is not False else None


def encode_doc(text: str) -> dict:
    """编码文档/查询: dense (sentence-transformers) + optional sparse (FlagEmbedding)。"""
    st_model = _get_sentence_transformer()
    dense = st_model.encode([text], normalize_embeddings=True)[0].tolist()

    sparse = {}
    if HYBRID_RETRIEVAL_ENABLED:
        flag = _get_flag_model()
        if flag is not None:
            try:
                out = flag.encode([text], return_dense=False, return_sparse=True, return_colbert_vecs=False)
                sparse = {str(k): float(v) for k, v in out["lexical_weights"][0].items()}
            except Exception:
                pass  # sparse 失败 → 退化为纯 dense
    return {"dense": dense, "sparse": sparse}


# ── Chroma 集合 ─────────────────────────────────────────

def _get_collection():
    """线程安全的 Chroma 持久化集合（cosine 相似度），带 Windows 重试。"""
    import chromadb
    with _collection_lock:
        for attempt in range(3):
            try:
                VECTOR_STORE_DIR.mkdir(parents=True, exist_ok=True)
                client = chromadb.PersistentClient(path=str(VECTOR_STORE_DIR))
                return client.get_or_create_collection(
                    name=VECTOR_COLLECTION,
                    metadata={"hnsw:space": "cosine"},
                )
            except Exception as e:
                if attempt < 2:
                    _time.sleep(0.5)
                    continue
                raise e


# ── 辅助函数 ────────────────────────────────────────────

def _parse_metadata(file_path: Path) -> dict:
    """从 history-database/<分类>/<日期>_<课题>.txt 解析元数据。"""
    category = file_path.parent.name
    stem = file_path.stem
    date, _, topic = stem.partition("_")
    return {"category": category, "date": date, "topic": topic or stem, "path": str(file_path)}


def _chunk_text(text: str, max_chars: int) -> list:
    """简单结构化切块。短文档 → 1 块；长文档 → 按段落/句号切。"""
    if len(text) <= max_chars:
        return [text.strip()]
    paras = [p.strip() for p in text.split("\n\n") if p.strip()]
    chunks, buf = [], ""
    for p in paras:
        if len(buf) + len(p) + 2 <= max_chars:
            buf = (buf + "\n\n" + p).strip()
        else:
            if buf:
                chunks.append(buf)
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


def _generate_contextual_header(full_text: str, chunk_text: str, topic: str, category: str) -> str:
    """调 Summarizer LLM 为单个 chunk 生成上下文锚点。
    优雅降级: LLM 调用失败 → 返回基于元数据的简单锚点。
    """
    from deep_research.summarizer import call_summarizer_llm
    prompt = f"""<document>
{full_text}
</document>

<chunk>
{chunk_text}
</chunk>

请用 1-2 句话（不超过 80 字）写一个上下文锚点，说明这个 chunk 是关于什么的，
在文档（主题: {topic}; 分类: {category}）里讨论的是哪个侧面，包含哪些关键实体/概念名。
直接输出，不要加前缀、引号或解释。"""
    try:
        return call_summarizer_llm(prompt, max_tokens=200).strip()
    except Exception:
        # 降级: 使用最小占位，不影响后续流程
        return ""


def _sparse_score(q_sparse: dict, d_sparse: dict) -> float:
    """BGE-M3 lexical_weights 间稀疏点积。"""
    if not q_sparse or not d_sparse:
        return 0.0
    common = set(q_sparse.keys()) & set(d_sparse.keys())
    return sum(q_sparse[t] * d_sparse[t] for t in common)


def _rrf_fuse(dense_ranking: list, sparse_ranking: list, k: int) -> list:
    """Reciprocal Rank Fusion: 融合 dense 和 sparse 两路排序。"""
    scores = {}
    for rank, cid in enumerate(dense_ranking):
        scores[cid] = scores.get(cid, 0.0) + 1.0 / (k + rank + 1)
    for rank, cid in enumerate(sparse_ranking):
        scores[cid] = scores.get(cid, 0.0) + 1.0 / (k + rank + 1)
    return [cid for cid, _ in sorted(scores.items(), key=lambda x: -x[1])]


# ── 公开 API ────────────────────────────────────────────

def index_document(file_path: str, category: str = None, topic: str = None, date_str: str = None) -> int:
    """索引一个归档文档。短文档整篇当 chunk，长文档按 CHUNK_MAX_CHARS 切块。

    新 schema 元数据: parent_id, chunk_index, sparse_weights, contextual_header
    旧版调用 (只传 file_path) 仍兼容，此时从路径自动解析 category/topic/date。
    """
    file_path = Path(file_path)
    if not file_path.exists():
        return 0
    text = file_path.read_text(encoding="utf-8").strip()
    if not text:
        return 0

    # 兼容旧签名
    if category is None or topic is None or date_str is None:
        meta = _parse_metadata(file_path)
        category = category or meta["category"]
        topic = topic or meta["topic"]
        date_str = date_str or meta["date"]

    parent_id = hashlib.md5(str(file_path).encode("utf-8")).hexdigest()
    chunks = _chunk_text(text, CHUNK_MAX_CHARS)
    headers = []
    for c in chunks:
        if CONTEXTUAL_RETRIEVAL_ENABLED:
            headers.append(_generate_contextual_header(text, c, topic, category))
        else:
            headers.append("")

    collection = _get_collection()
    ids, docs, embeds, metas = [], [], [], []
    for idx, (chunk, header) in enumerate(zip(chunks, headers)):
        text_to_embed = (header + "\n\n" + chunk) if header else chunk
        enc = encode_doc(text_to_embed)
        ids.append(f"{parent_id}_{idx}")
        docs.append(chunk)  # 存原文 chunk，header 不存
        embeds.append(enc["dense"])
        metas.append({
            "parent_id": parent_id,
            "chunk_index": idx,
            "chunk_total": len(chunks),
            "source_path": str(file_path),
            "category": category,
            "topic": topic,
            "date": date_str,
            "contextual_header": header,
            "sparse_weights": json.dumps(enc["sparse"], ensure_ascii=False),
            "indexed_with_contextual": CONTEXTUAL_RETRIEVAL_ENABLED,
        })

    with _collection_lock:
        for attempt in range(3):
            try:
                collection.upsert(ids=ids, documents=docs, embeddings=embeds, metadatas=metas)
                break
            except Exception as e:
                if attempt == 2: raise
                _time.sleep(0.5 * (2 ** attempt))
    return len(chunks)


def search_kb(query: str, top_k: int = None, category: Optional[str] = None) -> list[dict]:
    """混合检索主入口: dense 召回 → sparse 计分 → RRF 融合 → cross-encoder 重排 → 父文档去重 → top_k。"""
    top_k = top_k or KB_FINAL_TOP_K

    q_enc = encode_doc(query)
    where = {"category": category} if category else None
    collection = _get_collection()
    if collection.count() == 0:
        return []

    dense_res = collection.query(
        query_embeddings=[q_enc["dense"]],
        n_results=KB_CANDIDATE_K,
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

    # 混合 or 纯 dense
    if HYBRID_RETRIEVAL_ENABLED:
        sparse_pairs = []
        for cid, payload in id_to_payload.items():
            d_sparse = json.loads(payload["meta"].get("sparse_weights", "{}"))
            s = _sparse_score(q_enc["sparse"], d_sparse)
            sparse_pairs.append((cid, s))
        sparse_ranking = [cid for cid, _ in sorted(sparse_pairs, key=lambda x: -x[1])]
        ranked_ids = _rrf_fuse(cand_ids, sparse_ranking, k=HYBRID_RRF_K)
    else:
        ranked_ids = cand_ids

    # KB 重排
    if KB_RERANK_ENABLED:
        from deep_research.rerank import _get_reranker
        try:
            reranker = _get_reranker()
            pairs = [(query, id_to_payload[cid]["doc"]) for cid in ranked_ids]
            scores = reranker.predict(pairs)
            ranked_ids = [cid for cid, _ in sorted(zip(ranked_ids, scores), key=lambda x: -x[1])]
        except Exception:
            pass  # 重排失败就保持原序

    # 父文档去重
    seen_parents = set()
    final = []
    for cid in ranked_ids:
        meta = id_to_payload[cid]["meta"]
        pid = meta.get("parent_id", cid)
        if pid in seen_parents:
            continue
        seen_parents.add(pid)
        final.append({
            "text": id_to_payload[cid]["doc"],
            "category": meta.get("category", ""),
            "date": meta.get("date", ""),
            "topic": meta.get("topic", ""),
            "contextual_header": meta.get("contextual_header", ""),
            "score": round(1.0 - id_to_payload[cid]["dense_dist"], 3),
        })
        if len(final) >= top_k:
            break
    return final


def get_document_count() -> int:
    """向量库中文档总数（chunk 数，非文件数）。"""
    try:
        return _get_collection().count()
    except Exception:
        return 0
