"""
研究者子智能体的搜索工具：web_search 和 web_fetch。

所有工具在调用时都会实时打印到终端，带 researcher 编号标签。
通过 langgraph.config.get_config() 获取当前 agent 名称来识别 researcher。
"""

import sys
import time
import httpx
from langchain_core.tools import tool
try:
    from ddgs import DDGS
except ImportError:
    from duckduckgo_search import DDGS  # 旧版包名兼容

from . import config as cfg

# ── 搜索预算追踪（每个 researcher 独立计数，只影响自己，不影响他人）──
_search_budget = {}     # {agent_name: count}
_search_cache = {}      # {agent_name: {query_hash: True}}  每个 researcher 独立的去重缓存
_research_start_time = None     # 研究开始时间戳，由 run_test.py 设置
_research_timeout_seconds = 0   # 超时秒数，0=不限
BUDGET_EXCEEDED_MSG = (
    "⛔ 搜索预算已用尽（{limit}次）。请**立即停止所有搜索**，不要尝试其他搜索工具。"
    "现在直接整理已有发现，按 [核心发现] + [关键来源] + [充分性自评] 格式返回最终结果，不要拖延。"
)
DUPLICATE_MSG = (
    "[!] 你已搜索过相同或高度相似的查询。请换一个不同的角度或更具体的措辞，不要重复。"
    "（此条不计入搜索预算）"
)
TIMEOUT_BLOCK_MSG = (
    "⏰ 研究时限已到（{minutes}分钟）！立即停止所有搜索，"
    "直接整理已有发现返回。不要再调用任何搜索工具。"
)

# ── 上下文输出预算追踪（P1：每个 researcher 独立累计）──
_tool_output_chars: dict[str, int] = {}
CONTEXT_SOFT_WARN_MSG = (
    "\n\n⚠️ 上下文软限制已触发（累计输出 ~{total_k:.0f}K 字符）。"
    "请优先提炼发现到 /notes/，避免继续抓取大页面。最多再做 1 次必要搜索。"
)
CONTEXT_HARD_STOP_MSG = (
    "\n\n⛔ 上下文硬限制已触发（累计输出 ~{total_k:.0f}K 字符）！"
    "请**立即停止搜索**，基于已有 source_id 和笔记返回最终结构化发现。"
    "不要再调用任何搜索或抓取工具。"
)


def set_research_timeout(minutes: int):
    """由 run_test.py 在 Agent 启动前调用，设置硬时限。0=不限。"""
    global _research_start_time, _research_timeout_seconds
    if minutes > 0:
        _research_start_time = time.time()
        _research_timeout_seconds = minutes * 60
    else:
        _research_start_time = None
        _research_timeout_seconds = 0


def _check_time_limit() -> str | None:
    """检查是否超过研究时限。返回 None=未超时，返回 str=拦截消息。"""
    if _research_start_time is None or _research_timeout_seconds <= 0:
        return None
    elapsed = time.time() - _research_start_time
    if elapsed >= _research_timeout_seconds:
        return TIMEOUT_BLOCK_MSG.format(minutes=_research_timeout_seconds // 60)
    return None


def _check_search_budget(query: str = "") -> str | None:
    """检查预算是否已用完 + 时限是否已到 + 去重检查（不递增计数）。"""
    # 时限检查优先
    time_block = _check_time_limit()
    if time_block:
        return time_block

    tag = _get_tag()
    count = _search_budget.get(tag, 0)
    if count >= cfg.RESEARCHER_SEARCH_LIMIT:
        blocked = _search_budget.get(f"{tag}_blocked", 0) + 1
        _search_budget[f"{tag}_blocked"] = blocked
        if blocked >= 3:
            return (
                f"⛔ 你已经连续 {blocked} 次尝试搜索但预算已用尽。"
                f"**请立即返回最终结果，不要再调用任何搜索工具。**"
            )
        return BUDGET_EXCEEDED_MSG.format(limit=cfg.RESEARCHER_SEARCH_LIMIT)

    # 去重检查（按 researcher 隔离）
    if query:
        qhash = query.strip().lower()
        tag_cache = _search_cache.setdefault(tag, {})
        if qhash in tag_cache:
            _log(f"[去重] 重复查询，跳过: {query[:80]}")
            return DUPLICATE_MSG

    return None  # 预算充足且非重复


def _commit_search(query: str = ""):
    """提交一次搜索计数（在搜索成功后调用）。
    cfg.COUNT_FAILED_SEARCHES=True 时始终计数，False 时仅成功计数。
    """
    tag = _get_tag()
    # 标记去重缓存
    if query:
        qhash = query.strip().lower()
        tag_cache = _search_cache.setdefault(tag, {})
        tag_cache[qhash] = True
    # 递增计数
    _search_budget[tag] = _search_budget.get(tag, 0) + 1


def _track_tool_output(text: str, tool_name: str = "", query_or_url: str = "") -> str:
    """追踪每个 researcher 的累计工具输出量，超限时追加警告，并加 [TOOL_OBSERVATION] 包装。

    Returns:
        处理后的文本（含 [TOOL_OBSERVATION] 包装和可能的预算警告）。
    """
    tag = _get_tag()
    n = len(text or "")
    _tool_output_chars[tag] = _tool_output_chars.get(tag, 0) + n
    total = _tool_output_chars[tag]

    # ── [TOOL_OBSERVATION] 标准化包装 ──
    header = "[TOOL_OBSERVATION]"
    if tool_name:
        header += f"\ntool: {tool_name}"
    if query_or_url:
        is_url = query_or_url.startswith("http://") or query_or_url.startswith("https://")
        key = "url" if is_url else "query"
        header += f"\n{key}: {query_or_url}"
    wrapped = f"{header}\n\n{text}"

    if total >= cfg.TOOL_OUTPUT_HARD_CHAR_LIMIT_PER_AGENT:
        return wrapped + CONTEXT_HARD_STOP_MSG.format(total_k=total / 1000)
    if total >= cfg.TOOL_OUTPUT_SOFT_CHAR_LIMIT_PER_AGENT:
        return wrapped + CONTEXT_SOFT_WARN_MSG.format(total_k=total / 1000)
    return wrapped

# web_fetch 重试配置
MAX_FETCH_RETRIES = 3
RETRY_BACKOFF_BASE = 1.5

# ── Researcher 身份追踪 ──────────────────────────────
# 通过 langgraph 的 get_config() 获取运行时上下文中的 agent_name。

def _get_tag() -> str:
    """从 LangGraph 运行时获取当前 agent 名称作为标签。"""
    try:
        from langgraph.config import get_config
        config = get_config()
        # metadata 中有 lc_agent_name，configurable 中也有
        agent_name = (
            config.get("metadata", {}).get("lc_agent_name", "")
            or config.get("configurable", {}).get("lc_agent_name", "")
            or config.get("metadata", {}).get("run_name", "")
            or "researcher"
        )
        return agent_name
    except Exception:
        return "researcher"


def _log(msg: str):
    """实时输出日志，自动带 researcher 编号"""
    tag = _get_tag()
    try:
        print(f"  [{tag}] {msg}", file=sys.__stdout__, flush=True)
    except Exception:
        print(f"  [{tag}] {msg}", flush=True)


@tool
def web_search(query: str) -> str:
    """搜索网页，返回标题 + 摘要列表。

    使用时机：
    - 需要了解某个主题的概况
    - 寻找多个信息来源
    - 验证某个事实是否存在

    重要：收到搜索结果后，立即用 write_file 将关键发现保存到 /notes/<topic>.md，
    只保留提炼后的要点，不要将原始搜索输出全部留在上下文中。
    """
    budget_block = _check_search_budget(query)
    if budget_block:
        return budget_block
    _log(f"[搜索] {query[:100]}")
    try:
        with DDGS() as ddgs:
            results = list(ddgs.text(query, max_results=cfg.SEARCH_MAX_RESULTS))

        if not results:
            _log(f"[搜索] 无结果")
            if cfg.COUNT_FAILED_SEARCHES:
                _commit_search(query)
            return f"搜索 '{query}' 没有返回结果。"

        # 搜索成功 → 计数
        _commit_search(query)
        _log(f"[搜索] 找到 {len(results)} 条结果（重排前）")

        # ── 重排：多搜回 → 精排 → 少留 ──
        if cfg.RERANK_ENABLED and len(results) > cfg.RERANK_TOP_K:
            try:
                from .rerank import rerank_results
                results = rerank_results(query, results)
                _log(f"[重排] 保留最相关 {len(results)} 条")
            except Exception as e:
                _log(f"[重排] 失败（使用原始顺序）: {e}")

        for i, r in enumerate(results, 1):
            title = r.get("title", "无标题")[:80]
            _log(f"        #{i} {title}")

        lines = [f"搜索: {query}\n"]
        for i, r in enumerate(results, 1):
            title = r.get("title", "无标题")
            href = r.get("href", "")
            body = r.get("body", "无摘要")

            # ── P1: 注册搜索结果为轻量 source ────────────
            source_id = ""
            if cfg.ENABLE_SOURCE_REGISTRY and href:
                try:
                    from .source_registry import register_source
                    rec = register_source(
                        url=href,
                        text="",  # 搜索摘要不保存全文
                        title=title,
                        source_type="search_result",
                        query=query,
                        tool="web_search",
                    )
                    source_id = f"source_id: {rec.source_id}"
                except Exception:
                    pass

            lines.append(f"{i}. {title}")
            if source_id:
                lines.append(f"   {source_id}")
            lines.append(f"   URL: {href}")
            lines.append(f"   摘要: {body}\n")

        return _track_tool_output("\n".join(lines), tool_name="web_search", query_or_url=query)

    except Exception as e:
        _log(f"[搜索] 失败: {e}")
        if cfg.COUNT_FAILED_SEARCHES:
            _commit_search(query)
        return f"搜索失败: {type(e).__name__}: {e}"


@tool
def web_fetch(url: str) -> str:
    """获取单个网页内容。全文保存到 /sources/，工具返回轻量摘要（source_id + snippet）。

    使用时机：
    - 搜索返回的摘要不够详细，需要深入阅读某篇文章
    - 需要从特定来源获取完整信息
    - 需要文章的精确引用或数据

    获取后全文已自动保存。你只需引用 source_id，不要将整页原文留在上下文中。
    """
    # arXiv 镜像加速（国内网络环境）
    if cfg.ARXIV_MIRROR:
        url = url.replace("arxiv.org", cfg.ARXIV_MIRROR)

    short_url = url[:80] + "..." if len(url) > 80 else url
    _log(f"[抓取] {short_url}")

    last_error = None

    for attempt in range(1, MAX_FETCH_RETRIES + 1):
        try:
            headers = {
                "User-Agent": (
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/120.0.0.0 Safari/537.36"
                )
            }
            timeout_config = httpx.Timeout(
                connect=5.0,
                read=cfg.FETCH_TIMEOUT,
                write=5.0,
                pool=5.0,
            )
            with httpx.Client(
                timeout=timeout_config,
                follow_redirects=True,
            ) as client:
                response = client.get(url, headers=headers)
                response.raise_for_status()

            html = response.text
            text = _extract_main_content(html)
            _log(f"[抓取] 成功，{len(text)} 字符")

            # ── P1: 注册 source + 保存全文 ──────────────────
            if cfg.ENABLE_SOURCE_REGISTRY:
                try:
                    from .source_registry import register_source, format_source_tool_response

                    # 尝试从 HTML 提取标题
                    import re as _re
                    title_match = _re.search(r"<title>(.+?)</title>", html, _re.IGNORECASE)
                    page_title = title_match.group(1).strip() if title_match else None

                    record = register_source(
                        url=url,
                        text=text if cfg.WEB_FETCH_FULLTEXT_SAVE else "",
                        title=page_title,
                        source_type="web",
                        tool="web_fetch",
                    )

                    # 返回给 Agent 的 snippet（截断到 inline limit）
                    snippet = text[:cfg.WEB_FETCH_INLINE_CHAR_LIMIT]
                    if len(text) > cfg.WEB_FETCH_INLINE_CHAR_LIMIT:
                        snippet += f"\n[... 全文共 {len(text)} 字符，已保存到 {record.saved_path}]"

                    result = format_source_tool_response(record, snippet)
                    return _track_tool_output(result, tool_name="web_fetch", query_or_url=url)
                except Exception as e:
                    _log(f"[source_registry] 失败（降级返回原文）: {e}")
                    # 降级：返回截断后的原文
                    if len(text) > cfg.FETCH_CHAR_LIMIT:
                        text = text[:cfg.FETCH_CHAR_LIMIT] + (
                            f"\n\n[... 内容已截断，原文共 {len(text)} 字符 ...]"
                        )
                    return _track_tool_output(f"来源: {url}\n\n{text}", tool_name="web_fetch", query_or_url=url)

            # 未启用 source registry 时的旧行为
            if len(text) > cfg.FETCH_CHAR_LIMIT:
                text = text[:cfg.FETCH_CHAR_LIMIT] + (
                    f"\n\n[... 内容已截断，原文共 {len(text)} 字符 ...]"
                )
            return _track_tool_output(f"来源: {url}\n\n{text}", tool_name="web_fetch", query_or_url=url)

        except Exception as e:
            last_error = e
            if attempt < MAX_FETCH_RETRIES:
                wait = RETRY_BACKOFF_BASE ** attempt
                _log(f"[抓取] 第{attempt}次失败，{wait:.1f}s后重试: {e}")
                time.sleep(wait)
                continue
            _log(f"[抓取] 重试{MAX_FETCH_RETRIES}次均失败: {e}")
            return (
                f"获取页面失败（已重试 {MAX_FETCH_RETRIES} 次）: "
                f"{type(e).__name__}: {e}"
            )

    return f"获取页面失败: {type(last_error).__name__}: {last_error}"


def _extract_main_content(html: str) -> str:
    """正文抽取：trafilatura → readability → regex fallback（优雅降级）。"""
    text = None

    # 1. trafilatura（最优）
    if cfg.USE_TRAFILATURA:
        try:
            import trafilatura
            text = trafilatura.extract(html, include_comments=False, include_tables=True)
            if text:
                text = text.strip()
        except Exception:
            pass

    # 2. readability-lxml fallback
    if (not text) and cfg.USE_READABILITY_FALLBACK:
        try:
            from readability import Document as ReadabilityDoc
            doc = ReadabilityDoc(html)
            text = doc.summary()
            if text:
                text = _html_to_text(text)
        except Exception:
            pass

    # 3. 正则 fallback（保证始终有结果）
    if not text:
        text = _html_to_text(html)

    return text.strip()


def _html_to_text(html: str) -> str:
    """简易 HTML → 纯文本转换（不依赖 BeautifulSoup）。"""
    import re

    # 移除 script 和 style 标签及其内容
    html = re.sub(
        r"<(script|style|noscript|iframe|svg)[^>]*>.*?</\1>",
        "",
        html,
        flags=re.DOTALL | re.IGNORECASE,
    )
    # 移除 HTML 注释
    html = re.sub(r"<!--.*?-->", "", html, flags=re.DOTALL)
    # 将块级元素替换为换行
    html = re.sub(
        r"</?(div|p|h[1-6]|li|tr|article|section|header|footer|main|nav|aside|table|ul|ol|dl|dd|dt|pre|blockquote|figure|figcaption|address)[^>]*>",
        "\n",
        html,
        flags=re.IGNORECASE,
    )
    # br → 换行
    html = re.sub(r"<br[^>]*>", "\n", html, flags=re.IGNORECASE)
    # 移除所有剩余标签
    html = re.sub(r"<[^>]+>", "", html)
    # 解码 HTML 实体
    html = html.replace("&amp;", "&").replace("&lt;", "<").replace("&gt;", ">")
    html = html.replace("&quot;", '"').replace("&#39;", "'").replace("&nbsp;", " ")
    # 压缩连续空白/空行
    html = re.sub(r"[ \t]+", " ", html)
    html = re.sub(r"\n{3,}", "\n\n", html)

    return html.strip()


# ── OpenAlex 摘要还原 ───────────────────────────────────
# OpenAlex 的摘要以倒排索引存储，需还原为正常文本。

def _reconstruct_abstract(inverted_index: dict) -> str:
    """将 OpenAlex 的 abstract_inverted_index 还原为正常文本。"""
    if not inverted_index:
        return "（无摘要）"
    positions = {}
    for word, idx_list in inverted_index.items():
        for i in idx_list:
            positions[i] = word
    return " ".join(positions[i] for i in sorted(positions))


# ── 学术搜索工具 ────────────────────────────────────────

@tool
def search_openalex(query: str, max_results: int = 5) -> str:
    """检索 OpenAlex 学术文献库（免费，覆盖 2.4 亿+ 中外论文）。

    使用时机：
    - 课题偏学术/理论，需要同行评审的论文作为一手来源
    - 需要验证某个学术概念的定义或原始出处
    - 需要查找特定研究领域的最新论文

    返回标题、年份、作者、摘要和链接。结果可直接用于报告引用。
    注意：OpenAlex 偏向英文文献，中文论文覆盖较少。
    """
    import json
    import urllib.parse
    import urllib.request

    budget_block = _check_search_budget(query)
    if budget_block:
        return budget_block
    _log(f"[学术搜索] {query[:100]}")

    base = "https://api.openalex.org/works?"
    params = {
        "search": query,
        "per-page": str(max_results),
    }
    if cfg.ACADEMIC_MAILTO:
        params["mailto"] = cfg.ACADEMIC_MAILTO

    qs = urllib.parse.urlencode(params)
    req = urllib.request.Request(
        base + qs,
        headers={"User-Agent": "deep-research-agent/1.0"},
    )

    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            data = json.loads(resp.read().decode("utf-8"))
    except Exception as e:
        _log(f"[学术搜索] 失败: {e}")
        if cfg.COUNT_FAILED_SEARCHES:
            _commit_search(query)
        return f"OpenAlex 检索失败（网络或服务问题）：{type(e).__name__}: {e}"

    works = data.get("results", [])
    if not works:
        _log(f"[学术搜索] 无结果")
        if cfg.COUNT_FAILED_SEARCHES:
            _commit_search(query)
        return "OpenAlex 未找到相关论文。请尝试更换更具体的学术关键词。"

    # 搜索成功 → 计数
    _commit_search(query)
    _log(f"[学术搜索] 找到 {len(works)} 篇论文")

    for i, w in enumerate(works, 1):
        title = w.get("title") or w.get("display_name") or "（无标题）"
        _log(f"        #{i} {title[:80]}")

    out_lines = [f"学术搜索: {query}\n"]
    for w in works:
        title = w.get("title") or w.get("display_name") or "（无标题）"
        year = w.get("publication_year", "")
        doi = w.get("doi") or ""
        loc = w.get("primary_location") or {}
        url = loc.get("landing_page_url") or doi or ""
        authors = [
            a.get("author", {}).get("display_name", "")
            for a in (w.get("authorships") or [])[:5]
        ]
        abstract = _reconstruct_abstract(w.get("abstract_inverted_index"))
        if len(abstract) > 500:
            abstract = abstract[:500] + "..."

        # ── P1: 注册论文 source ────────────────────────────
        source_id = ""
        if cfg.ENABLE_SOURCE_REGISTRY:
            try:
                from .source_registry import register_source
                rec = register_source(
                    url=url,
                    text=abstract,  # 学术摘要保存为 source text
                    title=title,
                    doi=doi if doi else None,
                    authors=authors if authors else None,
                    published_at=str(year) if year else None,
                    source_type="paper",
                    query=query,
                    tool="search_openalex",
                )
                source_id = f"source_id: {rec.source_id}"
            except Exception:
                pass

        out_lines.append(f"标题: {title}")
        if source_id:
            out_lines.append(f"  {source_id}")
        out_lines.append(f"年份: {year}")
        out_lines.append(f"作者: {', '.join(filter(None, authors))}")
        out_lines.append(f"链接: {url}")
        if doi:
            out_lines.append(f"DOI: {doi}")
        out_lines.append(f"摘要: {abstract}")
        out_lines.append("")

    return _track_tool_output("\n".join(out_lines), tool_name="search_openalex", query_or_url=query)


@tool
def search_crossref(query: str, max_results: int = 5) -> str:
    """检索 Crossref 学术元数据库（免费），获取论文的规范引用信息。

    使用时机：
    - 需要确认论文的准确 DOI、期刊名、出版年份
    - web_search 或 search_openalex 找到的论文缺少规范元数据时
    - 需要按引用格式列出参考文献

    返回标题、DOI、期刊、年份、作者。适合补充引用信息，不适合全文检索。
    """
    import json
    import urllib.parse
    import urllib.request

    budget_block = _check_search_budget(query)
    if budget_block:
        return budget_block
    _log(f"[元数据] {query[:100]}")

    params = {
        "query": query,
        "rows": str(max_results),
    }
    if cfg.ACADEMIC_MAILTO:
        params["mailto"] = cfg.ACADEMIC_MAILTO

    qs = urllib.parse.urlencode(params)
    url = f"https://api.crossref.org/works?{qs}"
    req = urllib.request.Request(
        url,
        headers={"User-Agent": "deep-research-agent/1.0"},
    )

    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            data = json.loads(resp.read().decode("utf-8"))
    except Exception as e:
        _log(f"[元数据] 失败: {e}")
        if cfg.COUNT_FAILED_SEARCHES:
            _commit_search(query)
        return f"Crossref 检索失败：{type(e).__name__}: {e}"

    items = data.get("message", {}).get("items", [])
    if not items:
        _log(f"[元数据] 无结果")
        if cfg.COUNT_FAILED_SEARCHES:
            _commit_search(query)
        return "Crossref 未找到相关条目。"

    # 搜索成功 → 计数
    _commit_search(query)

    _log(f"[元数据] 找到 {len(items)} 条")

    out_lines = [f"元数据搜索: {query}\n"]
    for it in items:
        title = (it.get("title") or ["（无标题）"])[0]
        doi = it.get("DOI", "")
        url_item = it.get("URL", "")
        year = ""
        try:
            year = it.get("published", {}).get("date-parts", [[None]])[0][0] or ""
        except Exception:
            pass
        journal = ""
        try:
            journal = it.get("container-title", [""])[0] or ""
        except Exception:
            pass
        authors = [
            f"{a.get('given','')} {a.get('family','')}".strip()
            for a in (it.get("author") or [])[:5]
        ]

        # ── P1: 注册论文 source ────────────────────────────
        source_id = ""
        if cfg.ENABLE_SOURCE_REGISTRY:
            try:
                from .source_registry import register_source
                rec = register_source(
                    url=url_item,
                    text="",
                    title=title,
                    doi=doi if doi else None,
                    authors=authors if authors else None,
                    published_at=str(year) if year else None,
                    source_type="paper",
                    query=query,
                    tool="search_crossref",
                )
                source_id = f"source_id: {rec.source_id}"
            except Exception:
                pass

        out_lines.append(f"标题: {title}")
        if source_id:
            out_lines.append(f"  {source_id}")
        out_lines.append(f"期刊: {journal}")
        out_lines.append(f"年份: {year}")
        out_lines.append(f"DOI: {doi}")
        out_lines.append(f"链接: {url_item}")
        out_lines.append(f"作者: {', '.join(filter(None, authors))}")
        out_lines.append("")

    return _track_tool_output("\n".join(out_lines), tool_name="search_crossref", query_or_url=query)


# ── 国内来源搜索 ────────────────────────────────────────

@tool
def search_cn(query: str, source: str = "all") -> str:
    """搜索中文来源网站（知乎、百度百科、百度学术等），通过 DuckDuckGo 的 site: 过滤器实现。

    使用时机：
    - 中文论文/学位论文: source="xueshu"（百度学术索引）
    - 中文技术讨论/实践经验: source="zhihu"（知乎高质量长文）
    - 中文事实/定义/背景: source="baike"（百度百科）
    - 不确定/全都要: source="all"（同时搜索以上全部）

    Args:
        query: 搜索查询（中文效果最佳，不需加 site: 前缀）
        source: 来源选择 — "zhihu" | "baike" | "xueshu" | "all"(默认)

    搜索结果经过重排和 source 注册，返回轻量摘要（含 source_id）。
    计入搜索预算（与 web_search 共享上限）。
    """
    budget_block = _check_search_budget(query)
    if budget_block:
        return budget_block

    sources = cfg.CN_SOURCES
    if source not in sources and source != "all":
        return f"不支持的中文来源: {source}。可选: {', '.join(sources.keys())}, all"

    site_names = list(sources.keys()) if source == "all" else [source]
    site_filters = [sources[n] for n in site_names]
    site_query = " OR ".join(site_filters)
    full_query = f"{query} {site_query}"

    _log(f"[中文搜索:{source}] {query[:80]}")

    try:
        with DDGS() as ddgs:
            results = list(ddgs.text(full_query, max_results=cfg.CN_SEARCH_MAX_RESULTS))
    except Exception as e:
        _log(f"[中文搜索] DDGS 调用失败: {e}")
        if cfg.COUNT_FAILED_SEARCHES:
            _commit_search(query)
        return f"中文来源搜索失败: {type(e).__name__}: {e}"

    if not results:
        _log(f"[中文搜索] 无结果")
        if cfg.COUNT_FAILED_SEARCHES:
            _commit_search(query)
        return f"中文来源 '{source}' 未找到关于 '{query}' 的结果。请尝试更简洁的关键词或切换来源。"

    # 搜索成功 → 计数
    _commit_search(query)
    _log(f"[中文搜索] 找到 {len(results)} 条结果（重排前）")

    # ── 重排 ──
    if cfg.RERANK_ENABLED and len(results) > cfg.RERANK_TOP_K:
        try:
            from .rerank import rerank_results
            results = rerank_results(query, results)
            _log(f"[中文搜索] 重排后保留 {len(results)} 条")
        except Exception:
            pass

    # ── 格式化输出 ──
    src_label = {"zhihu": "知乎", "baike": "百度百科", "xueshu": "百度学术"}
    lines = [f"中文来源搜索 ({', '.join(src_label.get(n, n) for n in site_names)}): {query}\n"]

    for i, r in enumerate(results, 1):
        title = r.get("title", "无标题")
        href = r.get("href", "")
        body = r.get("body", "无摘要")

        source_id = ""
        if cfg.ENABLE_SOURCE_REGISTRY and href:
            try:
                from .source_registry import register_source
                source_type_map = {"zhihu": "community", "baike": "encyclopedia", "xueshu": "paper"}
                stype = source_type_map.get(source, "web") if source != "all" else "web"
                rec = register_source(
                    url=href,
                    text="",
                    title=title,
                    source_type=stype,
                    query=query,
                    tool="search_cn",
                )
                source_id = f"source_id: {rec.source_id}"
            except Exception:
                pass

        lines.append(f"{i}. {title}")
        if source_id:
            lines.append(f"   {source_id}")
        lines.append(f"   URL: {href}")
        lines.append(f"   摘要: {body}\n")

    return _track_tool_output("\n".join(lines), tool_name="search_cn", query_or_url=query)


# ── 本地知识库检索 ──────────────────────────────────────

@tool
def search_knowledge_base(query: str) -> str:
    """检索本项目已完成研究的本地知识库（免费、快速、不计入网络搜索上限）。

    使用时机：
    - 开始研究一个子问题之前，先查一次看本项目过去是否已有相关积累
    - 查询结果可作为研究背景和起点，但时效性强的结论必须再用网络搜索核实

    返回内容标注为「内部历史研究·已浓缩」——这些是过去某时点的结论，可能已过时。
    不计入 8 次网络搜索上限。
    """
    if not cfg.RAG_ENABLED:
        return "知识库未启用。"

    try:
        from .knowledge_base import search_kb
        results = search_kb(query, top_k=cfg.RAG_TOP_K)
    except Exception as e:
        _log(f"[知识库] 检索失败: {e}")
        return f"知识库检索失败（不影响其他搜索）：{e}"

    if not results:
        return "知识库中暂无相关历史研究。"

    _log(f"[知识库] 找到 {len(results)} 条历史研究")

    blocks = []
    for r in results:
        header_line = f"【上下文】{r.get('contextual_header', '')}\n" if r.get('contextual_header') else ""
        blocks.append(
            f"--- 内部历史研究 [{r['score']:.3f}] ---\n"
            f"分类: {r['category']} | 日期: {r['date']} | 课题: {r['topic']}\n"
            f"{header_line}"
            f"{r['text']}"
        )
    return "\n\n".join(blocks)


# ── HITL 计划审批工具 ────────────────────────────────────

@tool
def request_plan_approval(plan_summary: str, todos: str, briefs: str) -> str:
    """暂停并展示研究计划等待用户审批。启用 --interactive-plan 后可用。
    Supervisor 在阶段 1 完成后必须调用此工具。
    参数: plan_summary(一句话路径), todos(子问题清单), briefs(简报合并)
    返回: APPROVED(批准) / ABORTED(取消) / REVISE: <建议>(修订)
    """
    print("\n" + "=" * 60)
    print("  计划审批 HITL")
    print("=" * 60)
    print(f"\n研究路径: {plan_summary}\n")
    print(f"子问题清单:\n{todos}\n")
    print(f"任务简报:\n{briefs}\n")
    print("-" * 60)
    print("  [回车] 批准  |  输入建议  |  abort → 取消")
    print("-" * 60)
    try:
        user_input = input(">>> ").strip()
    except (EOFError, KeyboardInterrupt):
        return "ABORTED"
    if not user_input or user_input.lower() in {"approve", "ok", "yes", "y", "继续", "通过"}:
        return "APPROVED"
    if user_input.lower() in {"abort", "stop", "cancel", "取消", "终止"}:
        return "ABORTED"
    return f"REVISE: {user_input}"
