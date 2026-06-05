"""
定义 researcher 子智能体。

每个子智能体拥有独立的上下文窗口——这是隔离机制的核心。
注意：web_search 和 web_fetch 只在这里注册，supervisor 不能直接搜索。

工具日志自动带 researcher 编号（通过 tools.py 中的 ContextVar 懒分配）。
"""

from . import config as cfg
from .model_factory import make_chat_model
from .tools import web_search, web_fetch, search_openalex, search_crossref, search_knowledge_base
from .prompts import RESEARCHER_PROMPT, CRITIC_PROMPT


def create_researcher_subagents() -> list[dict]:
    """创建 3 个独立命名的研究员子智能体（researcher-1/2/3）。

    每个子智能体有唯一名称，这样 langgraph 运行时的 lc_agent_name
    可以区分它们，工具日志会自动带正确的编号。

    返回 SubAgent 字典列表，供 create_deep_agent 的 subagents 参数使用。
    """
    # ── 按配置开关构建工具列表 ──────────────────────────────
    base_tools = [web_search, web_fetch]
    if cfg.USE_OPENALEX:
        base_tools.append(search_openalex)
    if cfg.USE_CROSSREF:
        base_tools.append(search_crossref)
    if cfg.RAG_ENABLED:
        base_tools.append(search_knowledge_base)

    specs = []
    for i in range(1, cfg.SUBAGENT_MAX_CONCURRENCY + 1):
        name = f"researcher-{i}"
        researcher_model = make_chat_model("researcher")

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


def create_critic_subagent() -> dict | None:
    """创建 critic 审查子智能体（仅 cfg.CRITIC_ENABLED 时启用）。

    Critic 只给读权限（read_file + ls），不进行新搜索。
    """
    if not cfg.CRITIC_ENABLED:
        return None
    return {
        "name": "critic",
        "description": (
            "对 /report.md 和 /notes 做批判性审查。识别证据薄弱处、未覆盖的维度、"
            "矛盾未标注、引用不到位等问题。返回结构化的缺陷清单和补研究建议。"
            "不进行新的搜索;只读现有产物。"
        ),
        "system_prompt": CRITIC_PROMPT,
        "tools": [],  # FilesystemMiddleware 自动注入 read_file / ls
        "model": make_chat_model("critic"),
    }
