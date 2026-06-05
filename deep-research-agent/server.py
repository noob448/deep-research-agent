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

    task_id = f"task_{len(_running_tasks) + 1}"
    output_queue = queue.Queue()
    proc_holder = {}
    thread = threading.Thread(target=_run_agent, args=(topic, task_id, effort, output_queue, proc_holder), daemon=True)
    thread.start()
    _running_tasks[task_id] = {"thread": thread, "queue": output_queue, "proc": proc_holder}

    def generate():
        try:
            yield f"data: {json.dumps({'type': 'start', 'task_id': task_id})}\n\n"
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


@app.errorhandler(404)
def fallback(e):
    """Vue history 模式：未匹配的路径回退到 index.html"""
    if request.path.startswith("/api/"):
        return jsonify({"error": "Not found"}), 404
    return send_file(str(DIST_DIR / "index.html"))


if __name__ == "__main__":
    print("Deep Research Agent Server 启动: http://localhost:5001")
    app.run(host="0.0.0.0", port=5001, debug=False, threaded=True)
