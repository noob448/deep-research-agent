# -*- coding: utf-8 -*-
"""runtime_state 单元测试。

覆盖: init_run 创建目录、resume 不删除文件、save_progress 原子写、record_event 追加 JSONL。
"""

import json
import sys
from pathlib import Path

import pytest

# 确保项目路径
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from deep_research.runtime_state import (
    init_run, get_run, record_event,
    load_progress, save_progress, update_progress,
    append_jsonl, atomic_write_json,
    list_runs,
)
from deep_research import config as cfg


class TestInitRun:
    """测试 init_run 基本功能。"""

    def test_init_creates_directories(self, tmp_path):
        """新 run 应创建 workspace/sources/state 目录。"""
        cfg.RUNS_DIR = tmp_path / "runs"
        run = init_run(topic="test topic", run_id="test_001", resume=False)

        assert run.run_dir.exists()
        assert run.workspace_dir.exists()
        assert (run.workspace_dir / "notes").exists()
        assert run.sources_dir.exists()
        assert run.state_dir.exists()
        assert run.topic == "test topic"
        assert run.resumed is False

    def test_init_writes_progress(self, tmp_path):
        """新 run 应写入 research_progress.json。"""
        cfg.RUNS_DIR = tmp_path / "runs"
        init_run(topic="test", run_id="test_progress", resume=False)

        progress = load_progress()
        assert progress["run_id"] == "test_progress"
        assert progress["topic"] == "test"
        assert progress["phase"] == "initialized"
        assert progress["status"] == "running"
        assert progress["schema_version"] == cfg.STATE_SCHEMA_VERSION

    def test_resume_preserves_files(self, tmp_path):
        """Resume 不应删除已有 workspace 文件。"""
        cfg.RUNS_DIR = tmp_path / "runs"
        run1 = init_run(topic="test", run_id="test_resume", resume=False)
        # 创建一个测试文件
        test_file = run1.workspace_dir / "notes" / "test_note.md"
        test_file.write_text("existing content")

        # Resume
        run2 = init_run(topic=None, run_id="test_resume", resume=True)
        assert test_file.exists()
        assert test_file.read_text() == "existing content"
        assert run2.resumed is True

    def test_auto_generates_run_id(self, tmp_path):
        """不指定 run_id 时自动生成时间戳格式。"""
        cfg.RUNS_DIR = tmp_path / "runs"
        run = init_run(topic="auto id test")
        assert run.run_id
        # 时间戳格式: YYYYMMDD_HHMMSS
        assert len(run.run_id) >= 15  # minimum length for timestamp


class TestProgressIO:
    """测试进度文件的读写。"""

    def test_save_and_load_progress(self, tmp_path):
        cfg.RUNS_DIR = tmp_path / "runs"
        init_run(topic="test", run_id="test_io", resume=False)

        save_progress({"phase": "researching", "status": "running"})
        loaded = load_progress()
        assert loaded["phase"] == "researching"

    def test_update_progress_incremental(self, tmp_path):
        cfg.RUNS_DIR = tmp_path / "runs"
        init_run(topic="test", run_id="test_update", resume=False)

        update_progress(phase="planning")
        p1 = load_progress()
        assert p1["phase"] == "planning"

        update_progress(phase="researching", tasks=[{"id": 1}])
        p2 = load_progress()
        assert p2["phase"] == "researching"
        assert p2["tasks"] == [{"id": 1}]
        # topic 不应该丢失
        assert p2["topic"] == "test"

    def test_atomic_write_json(self, tmp_path):
        """原子写应该通过临时文件完成，不留下 .tmp 文件。"""
        path = tmp_path / "test.json"
        atomic_write_json(path, {"key": "value"})
        assert path.exists()
        assert json.loads(path.read_text()) == {"key": "value"}
        # 不应留下 tmp 文件
        assert not list(tmp_path.glob("*.tmp"))


class TestEventLog:
    """测试事件日志。"""

    def test_record_event_appends_jsonl(self, tmp_path):
        cfg.RUNS_DIR = tmp_path / "runs"
        init_run(topic="test", run_id="test_events", resume=False)

        record_event("test_event", {"foo": "bar"}, agent="test-agent")
        record_event("another_event", {"baz": 1})

        events_path = get_run().state_dir / cfg.EVENT_LOG_FILENAME
        assert events_path.exists()
        lines = events_path.read_text().strip().split("\n")
        # init_run 也会记录 run_started 事件，所以至少有 3 条
        assert len(lines) >= 3

        # 最后两条应该是我们手动记录的
        e1 = json.loads(lines[-2])
        assert e1["event_type"] == "test_event"
        assert e1["agent"] == "test-agent"
        assert e1["payload"] == {"foo": "bar"}

        e2 = json.loads(lines[-1])
        assert e2["event_type"] == "another_event"

    def test_append_jsonl_generic(self, tmp_path):
        cfg.RUNS_DIR = tmp_path / "runs"
        init_run(topic="test", run_id="test_jsonl", resume=False)

        append_jsonl("custom.jsonl", {"a": 1})
        append_jsonl("custom.jsonl", {"b": 2})

        path = get_run().state_dir / "custom.jsonl"
        lines = path.read_text().strip().split("\n")
        assert len(lines) == 2


class TestListRuns:
    """测试 run 列表功能。"""

    def test_list_runs_empty(self, tmp_path):
        cfg.RUNS_DIR = tmp_path / "runs"
        runs = list_runs()
        assert runs == []

    def test_list_runs_multiple(self, tmp_path):
        cfg.RUNS_DIR = tmp_path / "runs"
        init_run(topic="topic A", run_id="run_a", resume=False)
        init_run(topic="topic B", run_id="run_b", resume=False)

        runs = list_runs()
        assert len(runs) == 2
        topics = {r["topic"] for r in runs}
        assert "topic A" in topics
        assert "topic B" in topics
