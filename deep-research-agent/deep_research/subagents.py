"""
定义 researcher 子智能体。

每个子智能体拥有独立的上下文窗口——这是隔离机制的核心。
注意：web_search 和 web_fetch 只在这里注册，supervisor 不能直接搜索。

工具日志自动带 researcher 编号（通过 tools.py 中的 ContextVar 懒分配）。
"""

from langchain_openai import ChatOpenAI

from .config import (
    AGENT_MODEL,
    DEEPSEEK_API_KEY,
    DEEPSEEK_BASE_URL,
    REQUEST_TIMEOUT,
    MAX_RETRIES,
    USE_OPENALEX,
    USE_CROSSREF,
    RAG_ENABLED,
)
from .tools import web_search, web_fetch, search_openalex, search_crossref, search_knowledge_base
from .prompts import RESEARCHER_PROMPT


def create_researcher_subagents() -> list[dict]:
    """创建 3 个独立命名的研究员子智能体（researcher-1/2/3）。

    每个子智能体有唯一名称，这样 langgraph 运行时的 lc_agent_name
    可以区分它们，工具日志会自动带正确的编号。

    返回 SubAgent 字典列表，供 create_deep_agent 的 subagents 参数使用。
    """
    # ── 按配置开关构建工具列表 ──────────────────────────────
    base_tools = [web_search, web_fetch]
    if USE_OPENALEX:
        base_tools.append(search_openalex)
    if USE_CROSSREF:
        base_tools.append(search_crossref)
    if RAG_ENABLED:
        base_tools.append(search_knowledge_base)

    specs = []
    for i in range(1, 4):
        name = f"researcher-{i}"
        researcher_model = ChatOpenAI(
            model=AGENT_MODEL,
            api_key=DEEPSEEK_API_KEY,
            base_url=DEEPSEEK_BASE_URL,
            timeout=REQUEST_TIMEOUT,
            max_retries=MAX_RETRIES,
        )

        specs.append({
            "name": name,
            "description": (
                "负责搜索和收集信息的子智能体。"
                "当你需要查找某个具体问题的答案、收集事实、"
                "或深入了解某个主题时，将任务委托给 researcher。"
                "researcher 会搜索网页、阅读文章、提炼要点，"
                "并将关键发现总结后直接返回给主管。"
            ),
            "system_prompt": RESEARCHER_PROMPT,
            "tools": base_tools,
            "model": researcher_model,
        })
    return specs
