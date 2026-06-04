# -*- coding: utf-8 -*-
"""研究摘要的分类与浓缩模块。

报告完成后，将研究摘要和已有分类列表一起发给 LLM，由 LLM 自主决定：
1. 复用已有分类文件夹，或创建新分类
2. 将摘要浓缩为精炼版本（无硬编码规则，全由 LLM 判断）

Python 层只做胶水：读取目录 → 调 API → 写入结果。
"""

from langchain_openai import ChatOpenAI

from .config import (
    DEEPSEEK_API_KEY,
    DEEPSEEK_BASE_URL,
    SUMMARIZE_MODEL,
    REQUEST_TIMEOUT,
    MAX_RETRIES,
)


# ── 复用 LLM 调用入口 ──────────────────────────────────

def call_summarizer_llm(prompt: str, max_tokens: int = 2048) -> str:
    """对外暴露的 LLM 调用入口，供 knowledge_base 生成 contextual header 等复用。
    禁 thinking 提速（contextual header 不需要深度推理）。
    """
    model = ChatOpenAI(
        model=SUMMARIZE_MODEL,
        api_key=DEEPSEEK_API_KEY,
        base_url=DEEPSEEK_BASE_URL,
        timeout=REQUEST_TIMEOUT,
        max_retries=MAX_RETRIES,
        temperature=0.3,
        max_tokens=max_tokens,
        model_kwargs={"extra_body": {"thinking": {"type": "disabled"}}},
    )
    response = model.invoke(prompt)
    return response.content if hasattr(response, "content") else str(response)


def condense_and_categorize(research_content: str, existing_categories: list[str]) -> dict:
    """将研究摘要浓缩并确定归档分类。

    Args:
        research_content: research_summary.txt 的完整内容
        existing_categories: history-database 下已有的文件夹名称列表，如
            ["AI Agent架构", "AI Agent, 记忆系统, LLM 基础设施"]

    Returns:
        {"category": "归档文件夹名", "condensed_summary": "浓缩后的研究摘要"}
    """
    target_length = max(len(research_content) // 4, 200)

    existing_text = _format_categories(existing_categories)

    prompt = f"""你是一个研究归档助手。你的任务是对研究摘要做两件事：**分类** 和 **浓缩**。

## 当前已有的分类文件夹

{existing_text}

## 要求

### 1. 分类
- 阅读下面的研究摘要，判断它是否适合放入上述已有文件夹。
- **如果匹配已有文件夹**：直接返回该文件夹的完整名称（一字不差）。
- **如果不匹配任何已有文件夹**：创建一个新的分类名。用 2-3 个宽泛的关键词，逗号分隔，例如 "AI Agent, 记忆系统"。
- 只返回分类名称本身，不要额外解释。

### 2. 浓缩
- 将研究摘要浓缩为精炼版本，目标长度约 {target_length} 字。
- 保留核心发现、关键结论、最重要的 3-5 个来源。
- 去掉冗余描述，但保持可读性。

## 输出格式

严格按以下格式输出（不要改动标签）：

[CATEGORY]
你的分类决定（已有文件夹名或新分类名）
[/CATEGORY]

[SUMMARY]
浓缩后的研究摘要
[/SUMMARY]

## 研究摘要

{research_content}"""

    model = ChatOpenAI(
        model=SUMMARIZE_MODEL,
        api_key=DEEPSEEK_API_KEY,
        base_url=DEEPSEEK_BASE_URL,
        timeout=REQUEST_TIMEOUT,
        max_retries=MAX_RETRIES,
        temperature=0.3,  # 低温度，保证分类稳定
    )

    response = model.invoke(prompt)
    text = response.content if hasattr(response, "content") else str(response)

    category = _extract_tag(text, "CATEGORY")
    condensed = _extract_tag(text, "SUMMARY")

    if not category:
        category = "未分类"
    if not condensed:
        condensed = research_content

    return {"category": category.strip(), "condensed_summary": condensed.strip()}


def _format_categories(categories: list[str]) -> str:
    """格式化已有分类列表为 prompt 可读形式。"""
    if not categories:
        return "（目前还没有任何分类文件夹，你需要创建第一个。）"
    lines = [f"- {c}" for c in sorted(categories)]
    return "\n".join(lines)


def _extract_tag(text: str, tag: str) -> str:
    """从 LLM 输出中提取 [TAG]...[/TAG] 之间的内容。"""
    start_marker = f"[{tag}]"
    end_marker = f"[/{tag}]"
    try:
        start = text.index(start_marker) + len(start_marker)
        end = text.index(end_marker)
        return text[start:end].strip()
    except ValueError:
        return ""
