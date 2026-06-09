# -*- coding: utf-8 -*-
"""Flask 桥接服务：接收前端请求 → 启动 agent → SSE 实时推流 → 提供下载。

启动: python server.py
端口: 5000
"""

import os
import sys
import json
import queue
import threading
import subprocess
from pathlib import Path

from flask import Flask, Response, request, send_file, send_from_directory, jsonify
from flask_cors import CORS

# 确保项目路径
PROJECT_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(PROJECT_ROOT))

DIST_DIR = PROJECT_ROOT / "web" / "dist"

app = Flask(__name__)
CORS(app)

# 运行中的任务
_running_tasks = {}


def _run_agent(topic: str, task_id: str, effort: str, output_queue: queue.Queue, proc_holder: dict):
    """在子线程中启动 agent，逐行捕获 stdout 放入队列。"""
    cmd = [sys.executable, "run_test.py", topic]
    if effort == "deep":
        cmd.append("--long-thinking")
    elif effort == "max":
        cmd.extend(["--long-thinking", "--enable-critic"])
    elif effort == "fast":
        cmd.append("--short-thinking")
    try:
        proc = subprocess.Popen(
            cmd,
            cwd=str(PROJECT_ROOT),
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            encoding="utf-8",
            errors="replace",
            bufsize=1,
        )
        proc_holder["proc"] = proc
        for line in proc.stdout:
            output_queue.put({"type": "log", "data": line.rstrip()})
        proc.wait()
        output_queue.put({"type": "done", "exit_code": proc.returncode})
    except Exception as e:
        output_queue.put({"type": "error", "data": str(e)})
    finally:
        output_queue.put(None)


@app.route("/api/research", methods=["POST"])
def start_research():
    """启动研究任务，返回 SSE 流。"""
    data = request.get_json(force=True)
    topic = data.get("topic", "").strip()
    effort = data.get("effort", "deep")
    if not topic:
        return jsonify({"error": "缺少 topic"}), 400

    from datetime import datetime
    run_id = datetime.now().strftime("%Y%m%d_%H%M%S")

    task_id = f"task_{len(_running_tasks) + 1}"
    output_queue = queue.Queue()
    proc_holder = {}
    thread = threading.Thread(target=_run_agent, args=(topic, task_id, effort, output_queue, proc_holder), daemon=True)
    thread.start()
    _running_tasks[task_id] = {"thread": thread, "queue": output_queue, "proc": proc_holder}

    def generate():
        try:
            yield f"data: {json.dumps({'type': 'start', 'task_id': task_id, 'run_id': run_id})}\n\n"
            while True:
                item = output_queue.get(timeout=600)  # 最长等 10 分钟无输出
                if item is None:
                    break
                yield f"data: {json.dumps(item, ensure_ascii=False)}\n\n"
            yield f"data: {json.dumps({'type': 'closed'})}\n\n"
        finally:
            _running_tasks.pop(task_id, None)

    return Response(generate(), mimetype="text/event-stream")


@app.route("/api/download/<filename>")
def download_file(filename):
    """下载 workspace 下的文件（report.md / report.docx / research_summary.txt）。"""
    allowed = {"report.md", "report.docx", "research_summary.txt"}
    if filename not in allowed:
        return jsonify({"error": "不允许下载该文件"}), 403

    file_path = PROJECT_ROOT / "workspace" / filename
    if not file_path.exists():
        return jsonify({"error": "文件不存在，请先完成研究"}), 404

    mimetype_map = {
        ".md": "text/markdown; charset=utf-8",
        ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        ".txt": "text/plain; charset=utf-8",
    }
    ext = file_path.suffix
    return send_file(
        str(file_path),
        mimetype=mimetype_map.get(ext, "application/octet-stream"),
        as_attachment=True,
        download_name=filename,
    )


@app.route("/")
def index():
    return send_file(str(DIST_DIR / "index.html"))


@app.route("/assets/<path:filename>")
def serve_assets(filename):
    return send_from_directory(str(DIST_DIR / "assets"), filename)


@app.route("/api/stop", methods=["POST"])
def stop_research():
    """终止当前所有正在运行的研究任务。"""
    stopped = 0
    for task_id, task in list(_running_tasks.items()):
        proc = task.get("proc", {}).get("proc")
        if proc and proc.poll() is None:
            proc.terminate()
            proc.wait(timeout=5)
            stopped += 1
        _running_tasks.pop(task_id, None)
    return jsonify({"stopped": stopped})


@app.route("/api/health")
def health():
    return jsonify({"status": "ok"})


@app.route("/api/version")
def version_info():
    """返回当前版本信息（git commit + 关键文件修改时间）。"""
    import os as _os
    info = {"status": "ok"}
    try:
        result = subprocess.run(
            ["git", "log", "-1", "--format=%H|%h|%ci|%s"],
            capture_output=True, text=True, timeout=5,
            cwd=str(PROJECT_ROOT), encoding="utf-8", errors="replace",
        )
        if result.returncode == 0:
            parts = result.stdout.strip().split("|", 3)
            if len(parts) == 4:
                info["git"] = {"full_hash": parts[0], "short_hash": parts[1], "date": parts[2], "message": parts[3]}
    except Exception:
        info["git"] = None
    return jsonify(info)


@app.route("/api/runs")
def list_runs_api():
    """列出所有已记录的 run。"""
    try:
        runs_dir = PROJECT_ROOT / "runs"
        if not runs_dir.exists():
            return jsonify({"runs": []})
        runs = []
        for d in sorted(runs_dir.iterdir(), reverse=True):
            if d.is_dir() and not d.name.startswith("test"):
                progress_file = d / "state" / "research_progress.json"
                topic = ""
                status = "unknown"
                phase = ""
                has_report = (d / "workspace" / "report.md").exists()
                if progress_file.exists():
                    try:
                        p = json.loads(progress_file.read_text(encoding="utf-8"))
                        topic = p.get("topic", "")
                        phase = p.get("phase", "")
                        status = "completed" if phase == "completed" else ("running" if phase else "unknown")
                    except Exception:
                        pass
                runs.append({"run_id": d.name, "status": status, "phase": phase, "topic": topic[:80], "has_report": has_report})
        return jsonify({"runs": runs[:20]})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/runs/<run_id>")
def get_run(run_id):
    """返回指定 run 的详情。"""
    try:
        run_dir = PROJECT_ROOT / "runs" / run_id
        if not run_dir.exists():
            return jsonify({"error": "Run 不存在"}), 404
        progress_file = run_dir / "state" / "research_progress.json"
        progress = {}
        if progress_file.exists():
            progress = json.loads(progress_file.read_text(encoding="utf-8"))
        files = []
        for fn in ["report.md", "report.docx", "research_summary.txt"]:
            fp = run_dir / "workspace" / fn
            if fp.exists():
                files.append({"name": fn, "size": fp.stat().st_size})
        return jsonify({"run_id": run_id, "progress": progress, "files": files})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


def _find_latest_run_dir():
    """找到最新的 run 目录（降级方案）。"""
    runs_dir = PROJECT_ROOT / "runs"
    if not runs_dir.exists():
        return None
    dirs = sorted([d for d in runs_dir.iterdir() if d.is_dir() and not d.name.startswith("test")], reverse=True)
    return dirs[0] if dirs else None

def _find_file(run_id, relative_path):
    """按 run_id 找文件，失败则用最新 run，再失败返回 None。"""
    # 精确匹配
    path = PROJECT_ROOT / "runs" / run_id / relative_path
    if path.exists():
        return path
    # 最新 run 降级
    latest = _find_latest_run_dir()
    if latest:
        path = latest / relative_path
        if path.exists():
            return path
    # workspace 降级（strip "workspace/" 前缀避免路径重复）
    ws_relative = relative_path.replace("workspace/", "", 1) if relative_path.startswith("workspace/") else relative_path
    path = PROJECT_ROOT / "workspace" / ws_relative
    if path.exists():
        return path
    return None


@app.route("/api/runs/<run_id>/events")
def get_run_events(run_id):
    """返回指定 run 的 events.jsonl。"""
    try:
        path = _find_file(run_id, "state/events.jsonl")
        if not path:
            return jsonify({"events": [], "count": 0})
        events = []
        for line in path.read_text(encoding="utf-8").strip().split("\n"):
            if line:
                try:
                    events.append(json.loads(line))
                except Exception:
                    pass
        return jsonify({"events": events, "count": len(events)})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/runs/<run_id>/sources")
def get_run_sources(run_id):
    """返回指定 run 的 sources.jsonl。"""
    try:
        path = _find_file(run_id, "state/sources.jsonl")
        if not path:
            return jsonify({"sources": [], "count": 0})
        sources = []
        for line in path.read_text(encoding="utf-8").strip().split("\n"):
            if line:
                try:
                    sources.append(json.loads(line))
                except Exception:
                    pass
        return jsonify({"sources": sources, "count": len(sources)})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/runs/<run_id>/claims")
def get_run_claims(run_id):
    """返回指定 run 的 claims.jsonl。"""
    try:
        path = _find_file(run_id, "state/claims.jsonl")
        if not path:
            return jsonify({"claims": [], "count": 0})
        claims = []
        for line in path.read_text(encoding="utf-8").strip().split("\n"):
            if line:
                try:
                    claims.append(json.loads(line))
                except Exception:
                    pass
        return jsonify({"claims": claims, "count": len(claims)})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/runs/<run_id>/report")
def get_run_report(run_id):
    """返回指定 run 的 report.md。"""
    try:
        path = _find_file(run_id, "workspace/report.md")
        if not path:
            return jsonify({"error": "report.md 不存在"}), 404
        return jsonify({"report": path.read_text(encoding="utf-8"), "size": path.stat().st_size})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/download/<run_id>/<filename>")
def download_run_file(run_id, filename):
    """下载指定 run 的文件。"""
    allowed = {"report.md", "report.docx", "research_summary.txt"}
    if filename not in allowed:
        return jsonify({"error": "不允许下载该文件"}), 403
    file_path = PROJECT_ROOT / "runs" / run_id / "workspace" / filename
    if not file_path.exists():
        file_path = PROJECT_ROOT / "workspace" / filename
    if not file_path.exists():
        return jsonify({"error": "文件不存在"}), 404
    mime_map = {".md": "text/markdown; charset=utf-8", ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document", ".txt": "text/plain; charset=utf-8"}
    return send_file(str(file_path), mimetype=mime_map.get(file_path.suffix, "application/octet-stream"), as_attachment=True, download_name=filename)


@app.errorhandler(404)
def fallback(e):
    """Vue history 模式：未匹配的路径回退到 index.html"""
    if request.path.startswith("/api/"):
        return jsonify({"error": "Not found"}), 404
    return send_file(str(DIST_DIR / "index.html"))


if __name__ == "__main__":
    print("Deep Research Agent Server 启动: http://localhost:5001")
    app.run(host="0.0.0.0", port=5001, debug=False, threaded=True)
