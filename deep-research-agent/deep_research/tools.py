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

from .config import (
    SEARCH_MAX_RESULTS, FETCH_CHAR_LIMIT, FETCH_TIMEOUT,
    RERANK_ENABLED, RERANK_TOP_K,
    USE_OPENALEX, USE_CROSSREF, ARXIV_MIRROR, ACADEMIC_MAILTO,
    RAG_ENABLED, RAG_TOP_K,
)

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
    _log(f"[搜索] {query[:100]}")
    try:
        with DDGS() as ddgs:
            results = list(ddgs.text(query, max_results=SEARCH_MAX_RESULTS))

        if not results:
            _log(f"[搜索] 无结果")
            return f"搜索 '{query}' 没有返回结果。"

        _log(f"[搜索] 找到 {len(results)} 条结果（重排前）")

        # ── 重排：多搜回 → 精排 → 少留 ──
        if RERANK_ENABLED and len(results) > RERANK_TOP_K:
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
            lines.append(f"{i}. {title}")
            lines.append(f"   URL: {href}")
            lines.append(f"   摘要: {body}\n")

        return "\n".join(lines)

    except Exception as e:
        _log(f"[搜索] 失败: {e}")
        return f"搜索失败: {type(e).__name__}: {e}"


@tool
def web_fetch(url: str) -> str:
    """获取单个网页的完整文本内容。失败时自动重试最多3次。

    使用时机：
    - 搜索返回的摘要不够详细，需要深入阅读某篇文章
    - 需要从特定来源获取完整信息
    - 需要文章的精确引用或数据

    获取后立即将关键内容提炼到 /notes/ 文件中，不要将整页原文留在上下文中。
    内容会被截断以避免超出上下文窗口。
    """
    # arXiv 镜像加速（国内网络环境）
    if ARXIV_MIRROR:
        url = url.replace("arxiv.org", ARXIV_MIRROR)

    # 缩短 URL 用于显示
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
                read=FETCH_TIMEOUT,
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
            text = _html_to_text(html)
            _log(f"[抓取] 成功，{len(text)} 字符")

            if len(text) > FETCH_CHAR_LIMIT:
                text = text[:FETCH_CHAR_LIMIT] + (
                    f"\n\n[... 内容已截断，原文共 {len(text)} 字符 ...]"
                )

            return f"来源: {url}\n\n{text}"

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

    _log(f"[学术搜索] {query[:100]}")

    base = "https://api.openalex.org/works?"
    params = {
        "search": query,
        "per-page": str(max_results),
    }
    if ACADEMIC_MAILTO:
        params["mailto"] = ACADEMIC_MAILTO

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
        return f"OpenAlex 检索失败（网络或服务问题）：{type(e).__name__}: {e}"

    works = data.get("results", [])
    if not works:
        _log(f"[学术搜索] 无结果")
        return "OpenAlex 未找到相关论文。请尝试更换更具体的学术关键词。"

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

        out_lines.append(f"标题: {title}")
        out_lines.append(f"年份: {year}")
        out_lines.append(f"作者: {', '.join(filter(None, authors))}")
        out_lines.append(f"链接: {url}")
        out_lines.append(f"摘要: {abstract}")
        out_lines.append("")

    return "\n".join(out_lines)


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

    _log(f"[元数据] {query[:100]}")

    params = {
        "query": query,
        "rows": str(max_results),
    }
    if ACADEMIC_MAILTO:
        params["mailto"] = ACADEMIC_MAILTO

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
        return f"Crossref 检索失败：{type(e).__name__}: {e}"

    items = data.get("message", {}).get("items", [])
    if not items:
        _log(f"[元数据] 无结果")
        return "Crossref 未找到相关条目。"

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

        out_lines.append(f"标题: {title}")
        out_lines.append(f"期刊: {journal}")
        out_lines.append(f"年份: {year}")
        out_lines.append(f"DOI: {doi}")
        out_lines.append(f"链接: {url_item}")
        out_lines.append(f"作者: {', '.join(filter(None, authors))}")
        out_lines.append("")

    return "\n".join(out_lines)


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
    if not RAG_ENABLED:
        return "知识库未启用。"

    try:
        from .knowledge_base import search_kb
        results = search_kb(query, top_k=RAG_TOP_K)
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
