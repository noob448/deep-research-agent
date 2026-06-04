# -*- coding: utf-8 -*-
"""模型工厂：按角色创建 ChatOpenAI 实例，控制 reasoning_effort 和 thinking 透传。

不同角色的推理深度:
  supervisor = "max" (规划+综合，需要最深思考)
  researcher = "high" (工具调用频繁，max 档 token 回报率低)
  critic     = "max" (批判分析，需要仔细阅读)
  default    = "high"
"""

from langchain_openai import ChatOpenAI
from deep_research import config as cfg


def make_chat_model(role: str = "default", temperature: float = None) -> ChatOpenAI:
    """创建指定角色的 ChatOpenAI 模型实例。

    Args:
        role: "supervisor" | "researcher" | "critic" | "default"
        temperature: 覆盖默认温度（thinking 模式下会被静默忽略）
    """
    effort_map = {
        "supervisor": cfg.REASONING_EFFORT_SUPERVISOR,
        "researcher": cfg.REASONING_EFFORT_RESEARCHER,
        "critic": cfg.REASONING_EFFORT_CRITIC,
    }
    effort = effort_map.get(role, "high")

    model_kwargs = {}
    if cfg.THINKING_ENABLED:
        model_kwargs["extra_body"] = {"thinking": {"type": "enabled"}}

    return ChatOpenAI(
        model=cfg.AGENT_MODEL,
        api_key=cfg.DEEPSEEK_API_KEY,
        base_url=cfg.DEEPSEEK_BASE_URL,
        timeout=cfg.REQUEST_TIMEOUT,
        max_retries=cfg.MAX_RETRIES,
        max_tokens=cfg.THINKING_MAX_OUTPUT_TOKENS if cfg.THINKING_ENABLED else 4096,
        reasoning_effort=effort,
        temperature=temperature if temperature is not None else 0.7,
        model_kwargs=model_kwargs,
    )
