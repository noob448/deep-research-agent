# -*- coding: utf-8 -*-
"""检索结果重排：先多搜回，再按与查询的相关性精排，只留 top_k。

多搜 → 精排 → 少留 是标准两段式检索策略：
1. web_search 多返回一些结果（8~10 条）
2. 用本地 reranker 按查询相关性重新打分
3. 只保留最相关的 top_k 条（默认 4 条）
"""

from functools import lru_cache

from .config import RERANK_MODEL, RERANK_TOP_K


@lru_cache(maxsize=1)
def _get_reranker():
    """延迟加载并缓存 reranker 模型（首次调用自动下载，约 300MB）。"""
    from sentence_transformers import CrossEncoder

    return CrossEncoder(RERANK_MODEL)


def rerank_results(query: str, results: list, top_k: int | None = None) -> list:
    """对搜索结果按与 query 的相关性重排，返回最相关的 top_k 条。

    Args:
        query: 搜索查询
        results: 形如 [{"title":..., "url":..., "body":...}, ...]（DDGS 格式）
        top_k: 保留条数，默认取 config.RERANK_TOP_K

    Returns:
        重排后的结果列表（长度 ≤ top_k）
    """
    if not results or len(results) <= 1:
        return results

    top_k = top_k or RERANK_TOP_K
    if top_k >= len(results):
        return results  # 不需要截断

    model = _get_reranker()

    # 用 body（摘要）作为重排依据
    pairs = [(query, r.get("body", r.get("content", ""))) for r in results]
    scores = model.predict(pairs)

    ranked = sorted(
        zip(results, scores),
        key=lambda pair: float(pair[1]),
        reverse=True,
    )
    return [r for r, _ in ranked[:top_k]]
