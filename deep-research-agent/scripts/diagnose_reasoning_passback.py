# -*- coding: utf-8 -*-
"""诊断 reasoning_content 透传。
若报错或 content 异常 → LangChain 没透传 reasoning_content，需要 fix。
"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage
from langchain_core.tools import tool
from deep_research import config as cfg


@tool
def dummy_search(query: str) -> str:
    """假搜索"""
    return f"搜索结果: 42"


llm = ChatOpenAI(
    model=cfg.AGENT_MODEL,
    api_key=cfg.DEEPSEEK_API_KEY,
    base_url=cfg.DEEPSEEK_BASE_URL,
    reasoning_effort="max",
    model_kwargs={"extra_body": {"thinking": {"type": "enabled"}}},
    max_tokens=8000,
).bind_tools([dummy_search])

msg = llm.invoke([HumanMessage(content="请搜索'宇宙的意义'然后告诉我答案")])
print("reasoning_content present:", "reasoning_content" in msg.additional_kwargs)
print("tool_calls:", len(msg.tool_calls) if msg.tool_calls else 0)
print("PASS" if msg.tool_calls else "FAIL — no tool calls, reasoning may not be working")
