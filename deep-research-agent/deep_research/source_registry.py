# -*- coding: utf-8 -*-
"""来源注册表：URL 规范化、source_id 生成、全文保存、去重。

每个网页/论文被注册为一个 SourceRecord，全文保存到 run 的 /sources/ 目录。
工具返回轻量摘要（source_id + snippet），避免原始正文污染 Agent 上下文。

P1 实现 — 建立证据账本基础，为 P2 Claim Verifier 提供可追溯的原始来源。
"""

from __future__ import annotations

import hashlib
import json
import re
import time
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit, urlunsplit, parse_qsl, urlencode, urlparse

from . import config as cfg
from .runtime_state import get_run, append_jsonl


# ── 跟踪参数（将被移除）──────────────────────────────
_TRACKING_PARAMS = {
    "utm_source", "utm_medium", "utm_campaign", "utm_term", "utm_content",
    "fbclid", "gclid", "dclid", "gclsrc", "msclkid",
    "ref", "ref_src", "ref_url",
    "_ga", "_gl", "_hsenc", "_hsmi",
    "mc_cid", "mc_eid",
}


@dataclass
class SourceRecord:
    """一个注册来源的完整记录。"""
    source_id: str
    url: str
    canonical_url: str | None = None
    doi: str | None = None
    title: str | None = None
    authors: list[str] | None = None
    published_at: str | None = None
    fetched_at: str | None = None
    source_type: str = "unknown"       # web | paper | academic_abstract | search_result
    quality_score: float | None = None
    saved_path: str | None = None      # 相对于 run_dir 的路径
    content_chars: int = 0
    query: str | None = None           # 触发该来源的搜索查询
    tool: str | None = None            # 产生该来源的工具名
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        # 过滤 None 值保持 ledger 简洁
        return {k: v for k, v in d.items() if v is not None}


# ── URL 规范化 ────────────────────────────────────────

def canonicalize_url(url: str) -> str:
    """移除跟踪参数、标准化 scheme/host、去除 fragment。

    保留 DOI、arXiv ID 等关键路径信息。
    """
    try:
        parsed = urlsplit(url)
    except Exception:
        return url

    # scheme 小写
    scheme = parsed.scheme.lower() if parsed.scheme else "https"
    # host 小写
    netloc = parsed.netloc.lower() if parsed.netloc else ""
    # 路径标准化：移除末尾 /
    path = parsed.path.rstrip("/") if parsed.path else ""

    # 移除跟踪参数
    if parsed.query:
        qs_pairs = [(k, v) for k, v in parse_qsl(parsed.query) if k.lower() not in _TRACKING_PARAMS]
        query = urlencode(qs_pairs) if qs_pairs else ""
    else:
        query = ""

    # 去除 fragment（除了 arXiv 等特殊锚点）
    fragment = ""
    if "arxiv" in netloc:
        fragment = parsed.fragment if parsed.fragment else ""

    return urlunsplit((scheme, netloc, path, query, fragment))


# ── Source ID 生成 ────────────────────────────────────

def make_source_id(
    url: str | None = None,
    doi: str | None = None,
    title: str | None = None,
) -> str:
    """生成稳定的 source_id。

    优先级: DOI > canonical URL > title > hash
    """
    # DOI 优先（学术论文的全局唯一标识）
    if doi:
        doi_clean = doi.strip().lower().replace("https://doi.org/", "").replace("http://doi.org/", "")
        h = hashlib.md5(f"doi:{doi_clean}".encode()).hexdigest()[:6]
        return f"src_{h}"

    # canonical URL
    if url:
        canonical = canonicalize_url(url)
        h = hashlib.md5(canonical.encode()).hexdigest()[:6]
        return f"src_{h}"

    # title fallback
    if title:
        h = hashlib.md5(title.strip().lower().encode()).hexdigest()[:6]
        return f"src_{h}"

    # absolute fallback (should rarely happen)
    h = hashlib.md5(str(time.time()).encode()).hexdigest()[:6]
    return f"src_{h}"


# ── 全文保存 ──────────────────────────────────────────

def save_source_text(source_id: str, text: str) -> Path:
    """将来源全文保存到 run 的 /sources/<source_id>.txt。"""
    run = get_run()
    dest = run.sources_dir / f"{source_id}.txt"
    dest.write_text(text, encoding="utf-8")
    return dest


# ── 去重检查 ──────────────────────────────────────────

def _find_existing_source(
    url: str | None = None,
    doi: str | None = None,
    canonical_url: str | None = None,
) -> dict | None:
    """在 sources.jsonl 中查找匹配的已有来源。

    匹配顺序: DOI > canonical_url > URL
    """
    run = get_run()
    ledger = run.state_dir / cfg.SOURCES_LEDGER_FILENAME
    if not ledger.exists():
        return None

    doi_norm = doi.strip().lower().replace("https://doi.org/", "") if doi else None
    canon = canonical_url or (canonicalize_url(url) if url else None)

    try:
        for line in ledger.read_text(encoding="utf-8").strip().split("\n"):
            if not line:
                continue
            try:
                rec = json.loads(line)
            except json.JSONDecodeError:
                continue

            # DOI 匹配
            if doi_norm and rec.get("doi"):
                existing_doi = rec["doi"].strip().lower().replace("https://doi.org/", "")
                if existing_doi == doi_norm:
                    return rec

            # canonical URL 匹配
            if canon and rec.get("canonical_url"):
                if rec["canonical_url"] == canon:
                    return rec

            # 原始 URL 匹配
            if url and rec.get("url"):
                if rec["url"] == url:
                    return rec
    except Exception:
        pass

    return None


# ── 主入口：注册来源 ──────────────────────────────────

def register_source(
    *,
    url: str,
    text: str = "",
    title: str | None = None,
    doi: str | None = None,
    authors: list[str] | None = None,
    published_at: str | None = None,
    source_type: str = "unknown",
    query: str | None = None,
    tool: str | None = None,
    metadata: dict[str, Any] | None = None,
) -> SourceRecord:
    """注册一个来源。自动去重——同一 DOI/canonical URL 不会重复保存全文。

    Args:
        url: 来源 URL。
        text: 全文内容（为空时不保存文件，如 search_result 类型）。
        title: 来源标题。
        doi: 学术论文 DOI。
        source_type: "web" | "paper" | "academic_abstract" | "search_result"。
        query: 触发该来源的搜索查询。
        tool: 产生该来源的工具名（web_fetch / search_openalex 等）。

    Returns:
        SourceRecord（已保存的或新创建的）。
    """
    from datetime import datetime, timezone

    canonical = canonicalize_url(url)
    source_id = make_source_id(url=url, doi=doi, title=title)
    fetched_at = datetime.now(timezone.utc).isoformat()

    # ── 去重检查 ──────────────────────────────────────
    existing = _find_existing_source(url=url, doi=doi, canonical_url=canonical)
    if existing:
        # 已有来源，返回已有记录（不重复保存全文）
        return SourceRecord(
            source_id=existing.get("source_id", source_id),
            url=existing.get("url", url),
            canonical_url=existing.get("canonical_url", canonical),
            doi=existing.get("doi", doi),
            title=existing.get("title", title),
            authors=existing.get("authors", authors),
            published_at=existing.get("published_at", published_at),
            fetched_at=fetched_at,
            source_type=existing.get("source_type", source_type),
            saved_path=existing.get("saved_path"),
            content_chars=existing.get("content_chars", 0),
            query=query,
            tool=tool,
        )

    # ── 保存全文 ──────────────────────────────────────
    saved_path = None
    content_chars = 0
    if text.strip():
        dest = save_source_text(source_id, text)
        saved_path = f"/sources/{source_id}.txt"
        content_chars = len(text)

    record = SourceRecord(
        source_id=source_id,
        url=url,
        canonical_url=canonical,
        doi=doi,
        title=title,
        authors=authors,
        published_at=published_at,
        fetched_at=fetched_at,
        source_type=source_type,
        saved_path=saved_path,
        content_chars=content_chars,
        query=query,
        tool=tool,
        metadata=metadata or {},
    )

    # ── 追加到 sources.jsonl ─────────────────────────
    append_jsonl(cfg.SOURCES_LEDGER_FILENAME, record.to_dict())

    # 记录事件
    from .runtime_state import record_event
    record_event("source_registered", {
        "source_id": source_id,
        "url": url[:200],
        "source_type": source_type,
        "content_chars": content_chars,
    })

    return record


# ── 格式化工具返回 ────────────────────────────────────

def format_source_tool_response(
    record: SourceRecord,
    snippet: str = "",
    extra: dict[str, Any] | None = None,
) -> str:
    """生成工具返回给 Agent 的轻量摘要。

    格式:
      [SOURCE_SAVED]
      source_id: src_xxx
      url: https://...
      saved_to: /sources/src_xxx.txt
      content_chars: N
      关键片段: ...
    """
    parts = []
    if record.saved_path:
        parts.append(f"[SOURCE_SAVED]")
    else:
        parts.append(f"[SOURCE_REGISTERED]")
    parts.append(f"source_id: {record.source_id}")
    parts.append(f"url: {record.url}")
    if record.saved_path:
        parts.append(f"saved_to: {record.saved_path}")
        parts.append(f"content_chars: {record.content_chars}")
    if record.title:
        parts.append(f"title: {record.title}")
    if record.doi:
        parts.append(f"DOI: {record.doi}")
    if snippet:
        parts.append(f"\n关键片段:\n{snippet}")
    if extra:
        for k, v in extra.items():
            parts.append(f"{k}: {v}")
    parts.append(f"\n使用建议:")
    parts.append(f"- 后续引用请使用 source_id: {record.source_id}")
    if record.saved_path:
        parts.append(f"- 如需核验证据，请 read_file('{record.saved_path}')")
    return "\n".join(parts)


def get_source_count() -> int:
    """返回当前 run 的已注册来源数。"""
    run = get_run()
    ledger = run.state_dir / cfg.SOURCES_LEDGER_FILENAME
    if not ledger.exists():
        return 0
    try:
        return sum(1 for line in ledger.read_text(encoding="utf-8").strip().split("\n") if line)
    except Exception:
        return 0
