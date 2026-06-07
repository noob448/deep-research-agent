#!/usr/bin/env bash
# P0-P2 Smoke Test Script
# 验证: run 目录隔离、source 注册、事件日志、进度文件
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
cd "$PROJECT_DIR"

echo "=== Smoke Test: P0-P2 ==="
echo ""

# 1. 基础导入检查
echo "[1/5] 检查模块导入..."
python -c "
from deep_research.runtime_state import init_run, get_run, record_event, list_runs
from deep_research.source_registry import register_source, canonicalize_url
from deep_research.claim_verifier import extract_claims_from_report
from deep_research import config as cfg
print('  所有模块导入 OK')
"

# 2. 配置完整性检查
echo "[2/5] 检查配置..."
python -c "
from deep_research import config as cfg
required = [
    'RUNS_DIR', 'STATE_SCHEMA_VERSION', 'ENABLE_RUN_STATE',
    'SUPERVISOR_MODEL', 'RESEARCHER_MODEL', 'CRITIC_MODEL', 'SUMMARIZE_MODEL',
    'WEB_FETCH_INLINE_CHAR_LIMIT', 'TOOL_OUTPUT_SOFT_CHAR_LIMIT_PER_AGENT',
    'ENABLE_SOURCE_REGISTRY', 'REASONING_EFFORT_VERIFIER',
]
for attr in required:
    assert hasattr(cfg, attr), f'Missing config: {attr}'
print('  所有配置项存在')
"

# 3. 单元测试
echo "[3/5] 运行单元测试..."
python -m pytest tests/test_runtime_state.py tests/test_source_registry.py tests/test_config_dynamic.py -q
echo "  测试通过"

# 4. Run 目录隔离测试
echo "[4/5] 测试 run 目录..."
python -c "
from deep_research.runtime_state import init_run, get_run, load_progress, record_event
from deep_research import config as cfg
import tempfile, shutil

tmp = tempfile.mkdtemp()
try:
    cfg.RUNS_DIR = tmp / 'runs'
    run = init_run(topic='smoke test', run_id='ci_test', resume=False)

    # 检查目录结构
    assert run.workspace_dir.exists()
    assert run.sources_dir.exists()
    assert run.state_dir.exists()
    assert (run.workspace_dir / 'notes').exists()

    # 检查 progress
    p = load_progress()
    assert p['phase'] == 'initialized'
    assert p['topic'] == 'smoke test'

    # 检查 events
    record_event('test_event', {'key': 'val'})
    events = (run.state_dir / 'events.jsonl').read_text()
    assert 'test_event' in events

    print('  Run 目录隔离 OK')
finally:
    shutil.rmtree(tmp, ignore_errors=True)
"

# 5. Source 注册测试
echo "[5/5] 测试 source 注册..."
python -c "
from deep_research.runtime_state import init_run
from deep_research.source_registry import register_source, get_source_count
from deep_research import config as cfg
import tempfile, shutil

tmp = tempfile.mkdtemp()
try:
    cfg.RUNS_DIR = tmp / 'runs'
    init_run(topic='source test', run_id='ci_source', resume=False)

    rec = register_source(
        url='https://example.com/test',
        text='Test article content.',
        title='Test Article',
        source_type='web',
        tool='web_fetch',
    )
    assert rec.source_id.startswith('src_')
    assert get_source_count() == 1

    # 去重测试
    rec2 = register_source(url='https://example.com/test', text='dup', tool='test')
    assert rec2.source_id == rec.source_id
    assert get_source_count() == 1

    print('  Source 注册 OK')
finally:
    shutil.rmtree(tmp, ignore_errors=True)
"

echo ""
echo "=== Smoke Test: ALL PASSED ==="
