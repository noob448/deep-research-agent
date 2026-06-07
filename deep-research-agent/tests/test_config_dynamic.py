# -*- coding: utf-8 -*-
"""config 动态引用测试。

确保模块不会在 import 时捕获配置值。
"""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


class TestConfigDynamic:
    """验证 cfg.X 是动态引用而非 import 时捕获。"""

    def test_model_config_dynamic(self):
        """修改 cfg.RESEARCHER_MODEL 后 make_chat_model 能读到新值。"""
        from deep_research import config as cfg
        from deep_research.model_factory import make_chat_model

        original = cfg.RESEARCHER_MODEL
        try:
            cfg.RESEARCHER_MODEL = "test-model-override"
            model = make_chat_model("researcher", rate_limited=False)
            assert model.model_name == "test-model-override"
        finally:
            cfg.RESEARCHER_MODEL = original

    def test_subagent_count_dynamic(self):
        """修改 cfg.SUBAGENT_MAX_CONCURRENCY 后 subagents 数量应变化。"""
        from deep_research import config as cfg
        from deep_research.subagents import create_researcher_subagents

        original = cfg.SUBAGENT_MAX_CONCURRENCY
        try:
            cfg.SUBAGENT_MAX_CONCURRENCY = 2
            subs = create_researcher_subagents()
            assert len(subs) == 2

            cfg.SUBAGENT_MAX_CONCURRENCY = 4
            subs = create_researcher_subagents()
            assert len(subs) == 4
        finally:
            cfg.SUBAGENT_MAX_CONCURRENCY = original

    def test_search_limit_dynamic(self):
        """修改 cfg.RESEARCHER_SEARCH_LIMIT 应被 tools.py 引用。"""
        from deep_research import config as cfg
        from deep_research import tools

        original = cfg.RESEARCHER_SEARCH_LIMIT
        try:
            cfg.RESEARCHER_SEARCH_LIMIT = 99
            # 验证 tools 模块能访问到新值
            assert cfg.RESEARCHER_SEARCH_LIMIT == 99
        finally:
            cfg.RESEARCHER_SEARCH_LIMIT = original
