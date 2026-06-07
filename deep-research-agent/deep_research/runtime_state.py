# -*- coding: utf-8 -*-
"""运行状态层：run 目录隔离、进度文件、事件日志、断点恢复。

每次研究生成一个独立 run 目录:
  runs/<run_id>/
  ├── workspace/     ← 该次研究的独立工作区
  ├── sources/       ← 来源全文保存（P1 启用）
  └── state/         ← research_progress.json + events.jsonl + ledgers

用法:
  from .runtime_state import init_run, get_run, record_event, save_progress
"""

from __future__ import annotations

import json
import os
import shutil
import uuid
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Literal

from . import config as cfg

# ── 当前 run 上下文（模块级单例）──────────────────────
_current_run: RunContext | None = None


@dataclass
class RunContext:
    """一次研究的完整运行上下文。"""
    run_id: str
    topic: str | None
    run_dir: Path
    workspace_dir: Path
    sources_dir: Path
    state_dir: Path
    resumed: bool = False
    created_at: str | None = None


# ── 公开 API ──────────────────────────────────────────

def init_run(
    topic: str | None = None,
    run_id: str | None = None,
    resume: bool = False,
) -> RunContext:
    """创建或恢复一次研究运行。

    Args:
        topic: 研究课题（新 run 必填，resume 时可从 progress 读取）。
        run_id: 运行标识符。None 时自动生成（时间戳）。
        resume: True 时恢复已有 run，不删除已有文件。

    Returns:
        RunContext 实例（同时设为模块级当前 run）。
    """
    global _current_run

    # ── 解析 run_id ──────────────────────────────────────
    if resume:
        if run_id is None or run_id == "latest":
            run_id = _resolve_latest_run()
        if run_id is None:
            raise FileNotFoundError(
                "无法找到可恢复的 run。请先用 --run-id <id> 创建一次运行。"
            )
        run_dir = cfg.RUNS_DIR / run_id
        if not run_dir.exists():
            raise FileNotFoundError(
                f"Run 目录不存在: {run_dir}\n"
                f"可用 runs: {', '.join(_list_run_ids()) or '(无)'}"
            )
    else:
        if run_id is None:
            run_id = _generate_run_id()
        run_dir = cfg.RUNS_DIR / run_id
        if run_dir.exists():
            # 不覆盖已有 run，追加后缀
            run_id = f"{run_id}_{uuid.uuid4().hex[:6]}"
            run_dir = cfg.RUNS_DIR / run_id

    # ── 创建目录结构 ────────────────────────────────────
    workspace_dir = run_dir / "workspace"
    sources_dir = run_dir / "sources"
    state_dir = run_dir / "state"

    created_at = datetime.now(timezone.utc).isoformat()

    if resume:
        # 恢复模式：只确保目录存在，不删除任何文件
        workspace_dir.mkdir(parents=True, exist_ok=True)
        (workspace_dir / "notes").mkdir(exist_ok=True)
        sources_dir.mkdir(parents=True, exist_ok=True)
        state_dir.mkdir(parents=True, exist_ok=True)

        # 尝试从 progress 读取 topic
        progress = _load_progress_file(state_dir)
        if topic is None:
            topic = progress.get("topic")
    else:
        # 新 run：清空该 run 下的 workspace（如果存在），state 和 sources 全新创建
        if workspace_dir.exists():
            _rmtree_safe(workspace_dir)
        workspace_dir.mkdir(parents=True, exist_ok=True)
        (workspace_dir / "notes").mkdir(exist_ok=True)

        if sources_dir.exists():
            _rmtree_safe(sources_dir)
        sources_dir.mkdir(parents=True, exist_ok=True)

        if state_dir.exists():
            _rmtree_safe(state_dir)
        state_dir.mkdir(parents=True, exist_ok=True)

        # 写入初始 progress
        _init_progress(state_dir, run_id, topic, created_at)

    _current_run = RunContext(
        run_id=run_id,
        topic=topic,
        run_dir=run_dir,
        workspace_dir=workspace_dir,
        sources_dir=sources_dir,
        state_dir=state_dir,
        resumed=resume,
        created_at=created_at,
    )

    # 记录事件
    event_type = "run_resumed" if resume else "run_started"
    record_event(event_type, payload={
        "topic": topic,
        "run_id": run_id,
        "resumed": resume,
    })

    return _current_run


def get_run() -> RunContext:
    """返回当前 run 上下文。如果未初始化，自动创建默认 run。"""
    global _current_run
    if _current_run is None:
        _current_run = init_run(topic=None, run_id=None, resume=False)
    return _current_run


def get_workspace_dir() -> Path:
    return get_run().workspace_dir


def get_sources_dir() -> Path:
    return get_run().sources_dir


def get_state_dir() -> Path:
    return get_run().state_dir


# ── 事件日志 ──────────────────────────────────────────

def record_event(
    event_type: str,
    payload: dict[str, Any] | None = None,
    agent: str | None = None,
) -> None:
    """追加一条事件到当前 run 的 events.jsonl。

    Args:
        event_type: 事件类型（如 tool_call, phase_changed, run_completed）。
        payload: 事件附加数据。
        agent: 触发事件的 Agent 名称（如 researcher-1）。
    """
    run = get_run()
    event = {
        "ts": datetime.now(timezone.utc).isoformat(),
        "run_id": run.run_id,
        "event_type": event_type,
    }
    if agent:
        event["agent"] = agent
    if payload:
        event["payload"] = payload
    append_jsonl(cfg.EVENT_LOG_FILENAME, event)


# ── 进度文件 ──────────────────────────────────────────

def load_progress() -> dict[str, Any]:
    """读取当前 run 的 research_progress.json。"""
    return _load_progress_file(get_run().state_dir)


def save_progress(progress: dict[str, Any]) -> None:
    """原子写入 research_progress.json（完整替换）。"""
    progress["updated_at"] = datetime.now(timezone.utc).isoformat()
    atomic_write_json(get_run().state_dir / cfg.PROGRESS_FILENAME, progress)


def update_progress(**updates: Any) -> None:
    """增量更新 progress 字段。

    用法: update_progress(phase="researching", status="running")
    """
    progress = load_progress()
    progress.update(updates)
    save_progress(progress)


# ── JSONL 工具 ────────────────────────────────────────

def append_jsonl(filename: str, item: dict[str, Any]) -> None:
    """向指定 JSONL 文件追加一行 JSON。"""
    path = get_run().state_dir / filename
    line = json.dumps(item, ensure_ascii=False) + "\n"
    with open(path, "a", encoding="utf-8") as f:
        f.write(line)


# ── 原子写 JSON ───────────────────────────────────────

def atomic_write_json(path: Path, data: dict[str, Any]) -> None:
    """通过临时文件 + os.replace 实现原子写 JSON。"""
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(
        json.dumps(data, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    os.replace(tmp, path)


# ── Run 列表 ──────────────────────────────────────────

def list_runs() -> list[dict[str, Any]]:
    """列出所有 run 的摘要信息（按创建时间倒序）。"""
    if not cfg.RUNS_DIR.exists():
        return []
    result = []
    for d in sorted(cfg.RUNS_DIR.iterdir(), reverse=True):
        if not d.is_dir() or d.name.startswith("."):
            continue
        state_dir = d / "state"
        progress = _load_progress_file(state_dir)
        has_report = (d / "workspace" / "report.md").exists()
        has_docx = (d / "workspace" / "report.docx").exists()
        result.append({
            "run_id": d.name,
            "topic": progress.get("topic", "(unknown)"),
            "phase": progress.get("phase", "unknown"),
            "status": progress.get("status", "unknown"),
            "created_at": progress.get("created_at", ""),
            "updated_at": progress.get("updated_at", ""),
            "has_report": has_report,
            "has_docx": has_docx,
        })
    return result


def _list_run_ids() -> list[str]:
    """列出所有 run_id。"""
    if not cfg.RUNS_DIR.exists():
        return []
    return sorted(
        [d.name for d in cfg.RUNS_DIR.iterdir()
         if d.is_dir() and not d.name.startswith(".")],
        reverse=True,
    )


# ── 内部辅助 ──────────────────────────────────────────

def _generate_run_id() -> str:
    """生成默认 run_id（时间戳格式）。"""
    return datetime.now().strftime(cfg.DEFAULT_RUN_ID_FORMAT)


def _resolve_latest_run() -> str | None:
    """找到最近创建的 run_id。"""
    ids = _list_run_ids()
    return ids[0] if ids else None


def _rmtree_safe(path: Path) -> None:
    """安全删除目录树（带 Windows 重试）。"""
    import time as _time
    for _retry in range(3):
        try:
            shutil.rmtree(path)
            return
        except PermissionError:
            if _retry < 2:
                _time.sleep(0.5)
            else:
                # 降级：只清子文件
                for child in path.iterdir():
                    try:
                        if child.is_dir():
                            shutil.rmtree(child, ignore_errors=True)
                        else:
                            child.unlink(missing_ok=True)
                    except Exception:
                        pass


def _load_progress_file(state_dir: Path) -> dict[str, Any]:
    """从 state_dir 读取 progress 文件（不存在则返回空 dict）。"""
    path = state_dir / cfg.PROGRESS_FILENAME
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {}


def _init_progress(
    state_dir: Path,
    run_id: str,
    topic: str | None,
    created_at: str,
) -> None:
    """写入初始 research_progress.json。"""
    progress = {
        "schema_version": cfg.STATE_SCHEMA_VERSION,
        "run_id": run_id,
        "topic": topic,
        "phase": "initialized",
        "created_at": created_at,
        "updated_at": created_at,
        "status": "running",
        "tasks": [],
        "completed_researchers": [],
        "pending_researchers": [],
        "notes_files": [],
        "source_count": 0,
        "claim_count": 0,
        "verification": {
            "enabled": False,
            "verified": 0,
            "unsupported": 0,
            "partial": 0,
            "contradicted": 0,
        },
        "report_status": {
            "outline_done": False,
            "draft_done": False,
            "critic_done": False,
            "verified": False,
            "docx_done": False,
        },
        "errors": [],
    }
    atomic_write_json(state_dir / cfg.PROGRESS_FILENAME, progress)
