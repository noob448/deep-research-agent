# -*- coding: utf-8 -*-
"""本地向量知识库：用 BGE-M3 嵌入历史研究摘要，存入本地 Chroma 持久化。

设计与 rerank.py 一致：模型与集合均 lazy-load + lru_cache 缓存。
内存占用：BGE-M3(~1.2GB) + bge-reranker(~300MB) 同时加载约 1.5-2GB。
语料已是 Summarizer 浓缩后的摘要（200-900 字），一篇 = 一个向量，不做切块。
"""

import hashlib
import threading
from functools import lru_cache
from pathlib import Path

from .config import (
    EMBEDDING_MODEL,
    VECTOR_STORE_DIR,
    VECTOR_COLLECTION,
    RAG_TOP_K,
)

# 线程锁：保护 Chroma 集合的并发初始化（Windows 下多 researcher 同时访问会竞态）
_collection_lock = threading.Lock()


@lru_cache(maxsize=1)
def _get_embedder():
    """延迟加载本地嵌入模型 BGE-M3（首次调用约 1.2GB 下载，之后缓存）。

    HF_ENDPOINT 已在 config.py 导入时设置为 https://hf-mirror.com。
    """
    from sentence_transformers import SentenceTransformer
    return SentenceTransformer(EMBEDDING_MODEL)


@lru_cache(maxsize=1)
def _get_collection():
    """延迟创建/打开本地 Chroma 持久化集合（cosine 相似度）。

    使用线程锁保护，修复 Windows 下多 researcher 并发访问时的
    'RustBindingsAPI' object has no attribute 'bindings' 竞态错误。
    """
    import chromadb
    import time as _time
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


def _embed(texts: list[str]) -> list:
    """文本列表 → 归一化向量列表。"""
    model = _get_embedder()
    vecs = model.encode(texts, normalize_embeddings=True)
    return [v.tolist() for v in vecs]


def _parse_metadata(file_path: Path) -> dict:
    """从 history-database/<分类>/<日期>_<课题>.txt 路径解析元数据。"""
    category = file_path.parent.name
    stem = file_path.stem
    date, _, topic = stem.partition("_")
    return {
        "category": category,
        "date": date,
        "topic": topic or stem,
        "path": str(file_path),
    }


def index_document(file_path) -> str:
    """将单个历史研究 txt 嵌入并 upsert 到向量库（幂等，重复运行不重复入库）。

    用文件路径 MD5 作为稳定 ID，再次索引同一文件只会覆盖，不会产生重复向量。
    """
    file_path = Path(file_path)
    if not file_path.exists():
        return f"文件不存在：{file_path}"
    text = file_path.read_text(encoding="utf-8").strip()
    if not text:
        return f"文件为空，跳过：{file_path}"

    meta = _parse_metadata(file_path)
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


def search_kb(query: str, top_k: int = None, category: str = None) -> list[dict]:
    """检索向量知识库，返回 [{text, category, date, topic, score}, ...]。

    category 不为空时只在指定分类内检索（实现"选择性查询"）。
    """
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
            "score": round(1 - dist, 3),  # cosine 距离 → 相似度
        })
    return out


def get_document_count() -> int:
    """返回向量库中当前的文档总数。"""
    try:
        return _get_collection().count()
    except Exception:
        return 0
