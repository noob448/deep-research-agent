# -*- coding: utf-8 -*-
"""模型工厂：按角色创建 ChatOpenAI 实例，控制 reasoning_effort、thinking 透传、API 并发限流。

不同角色的推理深度:
  supervisor = "max" (规划+综合，需要最深思考)
  researcher = "high" (工具调用频繁，max 档 token 回报率低; 并发量大)
  critic     = "max" (批判分析，需要仔细阅读)
  default    = "high"

并发限流:
  全局信号量限制同时进行的 API 调用数，防止 5+ Researcher 并行 max reasoning
  时触发 DeepSeek 限流或连接超时。semaphore(3) 表示最多 3 个并发请求。
"""

import threading
from langchain_openai import ChatOpenAI
from langchain_core.language_models.chat_models import BaseChatModel
from deep_research import config as cfg

# 全局并发信号量（与 researcher 数量解耦，保护 API 不被打爆）
_API_SEMAPHORE = threading.Semaphore(3)


class _RateLimitedChatOpenAI(ChatOpenAI):
    """ChatOpenAI 子类，在每次 API 调用前获取信号量，调用后释放。

    透明限流：不影响 LangChain/deepagents 的任何内部逻辑。
    """

    def invoke(self, *args, **kwargs):
        with _API_SEMAPHORE:
            return super().invoke(*args, **kwargs)

    async def ainvoke(self, *args, **kwargs):
        with _API_SEMAPHORE:
            return await super().ainvoke(*args, **kwargs)


def _model_for_role(role: str) -> str:
    """按角色返回应使用的模型名。"""
    return {
        "supervisor": cfg.SUPERVISOR_MODEL,
        "researcher": cfg.RESEARCHER_MODEL,
        "critic": cfg.CRITIC_MODEL,
        "verifier": cfg.VERIFIER_MODEL,
        "summarizer": cfg.SUMMARIZE_MODEL,
    }.get(role, cfg.DEFAULT_AGENT_MODEL)


def make_chat_model(role: str = "default", temperature: float = None, rate_limited: bool = True) -> BaseChatModel:
    """创建指定角色的 ChatOpenAI 模型实例。

    Args:
        role: "supervisor" | "researcher" | "critic" | "verifier" | "summarizer" | "default"
        temperature: 覆盖默认温度（thinking 模式下会被静默忽略）
        rate_limited: 是否受全局信号量限制（默认 True，只有内部非 agent 调用才关）
    """
    effort_map = {
        "supervisor": cfg.REASONING_EFFORT_SUPERVISOR,
        "researcher": cfg.REASONING_EFFORT_RESEARCHER,
        "critic": cfg.REASONING_EFFORT_CRITIC,
        "verifier": cfg.REASONING_EFFORT_VERIFIER,
    }
    effort = effort_map.get(role, "high")
    extra_body = {"thinking": {"type": "enabled"}} if cfg.THINKING_ENABLED else None

    cls = _RateLimitedChatOpenAI if rate_limited else ChatOpenAI
    model = _model_for_role(role)

    return cls(
        model=model,
        api_key=cfg.DEEPSEEK_API_KEY,
        base_url=cfg.DEEPSEEK_BASE_URL,
        timeout=cfg.REQUEST_TIMEOUT,
        max_retries=cfg.MAX_RETRIES,
        max_tokens=cfg.THINKING_MAX_OUTPUT_TOKENS if cfg.THINKING_ENABLED else 4096,
        reasoning_effort=effort,
        temperature=temperature if temperature is not None else 0.7,
        extra_body=extra_body,
    )
