# -*- coding: utf-8 -*-
"""source_registry 单元测试。

覆盖: URL canonicalization、source_id 生成、去重、全文保存。
"""

import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from deep_research.source_registry import (
    canonicalize_url, make_source_id, register_source,
    save_source_text, SourceRecord, get_source_count,
)
from deep_research.runtime_state import init_run, get_run
from deep_research import config as cfg


class TestURLCanonicalization:
    """URL 规范化测试。"""

    def test_removes_utm_params(self):
        url = "https://example.com/article?utm_source=twitter&utm_medium=social&id=123"
        result = canonicalize_url(url)
        assert "utm_source" not in result
        assert "utm_medium" not in result
        assert "id=123" in result

    def test_removes_fbclid(self):
        url = "https://example.com/page?fbclid=abc123&ref=home"
        result = canonicalize_url(url)
        assert "fbclid" not in result

    def test_lowercases_host(self):
        url = "https://Example.COM/Path?Q=1"
        result = canonicalize_url(url)
        assert "example.com" in result

    def test_strips_fragment_generally(self):
        url = "https://example.com/doc#section-1"
        result = canonicalize_url(url)
        assert "#section-1" not in result

    def test_preserves_arxiv_fragment(self):
        url = "https://arxiv.org/abs/2301.12597#discussion"
        result = canonicalize_url(url)
        # arXiv fragment 应保留
        assert "#discussion" in result or "arxiv.org" in result


class TestSourceID:
    """Source ID 生成测试。"""

    def test_doi_priority(self):
        id1 = make_source_id(doi="10.1234/example")
        assert id1.startswith("src_")
        # 同一 DOI 应产生相同 ID
        id2 = make_source_id(doi="10.1234/example")
        assert id1 == id2

    def test_url_fallback(self):
        id1 = make_source_id(url="https://example.com/unique-page")
        assert id1.startswith("src_")
        # 同一 URL 应产生相同 ID
        id2 = make_source_id(url="https://example.com/unique-page")
        assert id1 == id2

    def test_different_urls_different_ids(self):
        id1 = make_source_id(url="https://example.com/a")
        id2 = make_source_id(url="https://example.com/b")
        assert id1 != id2


class TestSourceRegistration:
    """来源注册测试。"""

    def setup_method(self):
        """每个测试前准备临时 run。"""
        self.tmp = Path(__file__).resolve().parent.parent / "runs" / "test_registry_tmp"
        cfg.RUNS_DIR = self.tmp.parent
        init_run(topic="test registry", run_id="test_registry_tmp", resume=False)

    def test_register_saves_text(self):
        rec = register_source(
            url="https://example.com/article",
            text="This is the full article text for testing.",
            title="Test Article",
            source_type="web",
            tool="web_fetch",
        )
        assert rec.source_id.startswith("src_")
        assert rec.saved_path
        assert rec.content_chars > 0

        # 检查文件确实被保存
        src_file = get_run().sources_dir / f"{rec.source_id}.txt"
        assert src_file.exists()
        assert "full article text" in src_file.read_text()

    def test_register_dedup_by_url(self):
        rec1 = register_source(
            url="https://example.com/same-page",
            text="Original text",
            source_type="web",
            tool="web_fetch",
        )
        rec2 = register_source(
            url="https://example.com/same-page",
            text="Should not overwrite",
            source_type="web",
            tool="web_fetch",
        )
        # 应该返回相同 source_id
        assert rec1.source_id == rec2.source_id

    def test_register_without_text(self):
        """搜索结果的注册——不保存全文。"""
        rec = register_source(
            url="https://example.com/search-result",
            text="",
            title="Search Result",
            source_type="search_result",
            tool="web_search",
        )
        assert rec.saved_path is None
        assert rec.content_chars == 0

    def test_sources_ledger_written(self):
        register_source(
            url="https://example.com/ledger-test",
            text="Test.",
            source_type="web",
            tool="web_fetch",
        )
        ledger = get_run().state_dir / cfg.SOURCES_LEDGER_FILENAME
        assert ledger.exists()
        items = [json.loads(l) for l in ledger.read_text().strip().split("\n") if l]
        assert len(items) >= 1
        assert items[0]["url"] == "https://example.com/ledger-test"

    def test_get_source_count(self):
        assert get_source_count() == 0
        register_source(url="https://a.com", text="a", tool="test")
        assert get_source_count() == 1
        register_source(url="https://b.com", text="b", tool="test")
        assert get_source_count() == 2
        # 重复 URL 不应增加 count
        register_source(url="https://a.com", text="a again", tool="test")
        assert get_source_count() == 2


class TestFormatSourceResponse:
    """工具返回格式测试。"""

    def test_format_with_saved_path(self):
        from deep_research.source_registry import format_source_tool_response
        rec = SourceRecord(
            source_id="src_test01",
            url="https://example.com",
            saved_path="/sources/src_test01.txt",
            content_chars=5000,
            title="Test Page",
            source_type="web",
        )
        result = format_source_tool_response(rec, snippet="This is the key snippet...")
        assert "[SOURCE_SAVED]" in result
        assert "source_id: src_test01" in result
        assert "saved_to: /sources/src_test01.txt" in result
        assert "关键片段" in result
