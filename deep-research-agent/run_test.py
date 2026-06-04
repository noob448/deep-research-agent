"""深度研究测试 — 实时进度反馈"""
import sys, os, time, warnings
warnings.filterwarnings("ignore")

# ⚠️ 必须在所有 agent 相关导入之前设置，否则 huggingface_hub 缓存旧 endpoint
os.environ.setdefault("HF_ENDPOINT", "https://hf-mirror.com")

# Fix Windows encoding
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

from deep_research.agent import create_supervisor_agent
from deep_research.config import (
    WORKSPACE_DIR, RECURSION_LIMIT, DEBUG,
    REASONING_EFFORT_SUPERVISOR, REASONING_EFFORT_RESEARCHER,
    RESEARCHER_SEARCH_LIMIT, SUBAGENT_MAX_CONCURRENCY,
    THINKING_ENABLED,
)
# convert_report 延迟导入——避免 docx 环境问题阻塞启动


# ── CLI 解析 ────────────────────────────────────────────

def parse_cli_args():
    import argparse
    parser = argparse.ArgumentParser(
        description="Deep Research Agent — 多智能体深度研究系统"
    )
    parser.add_argument("topic", nargs="?", default=None, help="研究课题")
    parser.add_argument("--reasoning-effort", choices=["high","max"], default=None, help="Supervisor 推理档位")
    parser.add_argument("--researcher-effort", choices=["high","max"], default=None, help="Researcher 推理档位")
    parser.add_argument("--long-thinking", action="store_true", help="便捷: 全部 max")
    parser.add_argument("--short-thinking", action="store_true", help="便捷: 全部 high")
    parser.add_argument("--enable-critic", action="store_true", help="开启 critic 反思回路")
    parser.add_argument("--critic-rounds", type=int, default=None, help="critic 最多轮数")
    parser.add_argument("--interactive-plan", action="store_true", help="开启 HITL 计划审批")
    parser.add_argument("--max-searches", type=int, default=None, help="研究员搜索上限")
    parser.add_argument("--max-researchers", type=int, default=None, help="并发 researcher 上限")
    parser.add_argument("--no-hybrid-kb", action="store_true", help="关闭混合检索")
    parser.add_argument("--no-rerank-kb", action="store_true", help="关闭 KB 重排")
    parser.add_argument("--no-contextual-rag", action="store_true", help="关闭上下文检索")
    parser.add_argument("--debug", action="store_true", help="打印 thinking 内容等详情")
    return parser.parse_args()


def apply_cli_to_config(args):
    from deep_research import config as cfg
    if args.long_thinking:
        cfg.REASONING_EFFORT_SUPERVISOR = "max"
        cfg.REASONING_EFFORT_RESEARCHER = "max"
        cfg.REASONING_EFFORT_CRITIC = "max"
    elif args.short_thinking:
        cfg.REASONING_EFFORT_SUPERVISOR = "high"
        cfg.REASONING_EFFORT_RESEARCHER = "high"
        cfg.REASONING_EFFORT_CRITIC = "high"
    if args.reasoning_effort: cfg.REASONING_EFFORT_SUPERVISOR = args.reasoning_effort
    if args.researcher_effort: cfg.REASONING_EFFORT_RESEARCHER = args.researcher_effort
    if args.enable_critic: cfg.CRITIC_ENABLED = True
    if args.critic_rounds is not None: cfg.CRITIC_MAX_ROUNDS = args.critic_rounds
    if args.interactive_plan: cfg.INTERACTIVE_PLAN_APPROVAL = True
    if args.max_searches is not None: cfg.RESEARCHER_SEARCH_LIMIT = args.max_searches
    if args.max_researchers is not None: cfg.SUBAGENT_MAX_CONCURRENCY = args.max_researchers
    if args.no_hybrid_kb: cfg.HYBRID_RETRIEVAL_ENABLED = False
    if args.no_rerank_kb: cfg.KB_RERANK_ENABLED = False
    if args.no_contextual_rag: cfg.CONTEXTUAL_RETRIEVAL_ENABLED = False
    cfg.DEBUG = bool(args.debug)


# ── 入口 ────────────────────────────────────────────────

_cli_args = parse_cli_args()
apply_cli_to_config(_cli_args)

TOPIC = _cli_args.topic or input("请输入研究课题: ").strip()
TS_START = time.time()

def elapsed():
    m, s = divmod(int(time.time() - TS_START), 60)
    return f"[{m:02d}:{s:02d}]"

def stage_label(text):
    """打印阶段标题"""
    print(f'\n{"="*60}')
    print(f'  {text}')
    print(f'{"="*60}', flush=True)

# ── 创建 Agent ──────────────────────────────────
print(f'{elapsed()} >>> 正在初始化 Deep Research Agent...', flush=True)
print(f'{elapsed()}     Supervisor: {REASONING_EFFORT_SUPERVISOR}档 | Researcher: {REASONING_EFFORT_RESEARCHER}档', flush=True)
thinking_status = "ON" if THINKING_ENABLED else "OFF"
print(f'{elapsed()}     Researcher x{SUBAGENT_MAX_CONCURRENCY} | 搜索上限: {RESEARCHER_SEARCH_LIMIT}次 | '
      f'Thinking: {thinking_status}', flush=True)
if DEBUG:
    print(f'{elapsed()}     [DEBUG] 调试模式开启', flush=True)
agent = create_supervisor_agent()
print(f'{elapsed()} >>> Agent 就绪，开始研究', flush=True)
print(f'{elapsed()}     课题: {TOPIC}', flush=True)

# ── 运行研究循环 ───────────────────────────────
step = 0
last_msg_count = 0
researcher_count = 0
stage = 'init'
stage_shown = set()  # 每个阶段只显示一次标题
notes_seen = set()

def once_stage(name, text):
    """每个阶段只打印一次标题"""
    if name not in stage_shown:
        stage_shown.add(name)
        stage_label(text)

try:
    for event in agent.stream(
        {'messages': [{'role': 'user', 'content': TOPIC}]},
        stream_mode='values',
        config={'recursion_limit': RECURSION_LIMIT},
    ):
        step += 1
        msgs = event.get('messages', [])
        new_msgs = msgs[last_msg_count:]
        last_msg_count = len(msgs)

        for msg in new_msgs:
            mt = type(msg).__name__
            content = str(msg.content) if hasattr(msg, 'content') and msg.content else ''

            # ── Tool Calls ──
            if hasattr(msg, 'tool_calls') and msg.tool_calls:
                for tc in msg.tool_calls:
                    name = tc.get('name', '?')
                    args = tc.get('args', {})

                    if name == 'write_todos':
                        todos = args.get('todos', [])
                        stage = 'plan'
                        once_stage('plan', f'阶段 1/4: 制定计划 ({len(todos)} 个子问题)')
                        # 只在首次展示子问题列表
                        if 'plan' not in stage_shown or len(todos) > 0:
                            pass  # 列表已展示，后续更新不重复打印
                        for i, t in enumerate(todos[:8], 1):
                            status = t.get('status', '?')
                            icon = '>' if status == 'in_progress' else ' '
                            print(f'     [{icon}] {i}. {t.get("content", "")}', flush=True)

                    elif name == 'task':
                        desc = args.get('description', '')
                        note_file = ''
                        if '/notes/' in desc:
                            note_file = desc.split('/notes/')[1].split('.md')[0].strip()
                            note_file = f' -> /notes/{note_file}.md'
                        researcher_count += 1
                        once_stage('delegate', '阶段 2/4: 并行委托研究员')
                        print(f'{elapsed()}   >>> 派出 Researcher #{researcher_count}: {desc[:120]}...{note_file}', flush=True)

                    elif name == 'read_file':
                        fp = args.get('file_path', '')
                        once_stage('review', '阶段 3/4: 阅读笔记与检查')
                        print(f'{elapsed()}   >> 阅读笔记: {fp}', flush=True)

                    elif name == 'write_file':
                        fp = args.get('file_path', '')
                        if 'report.md' in fp:
                            once_stage('report', '阶段 4/4: 撰写最终报告')
                            print(f'{elapsed()}   >>> 正在写入: {fp}', flush=True)
                        else:
                            print(f'{elapsed()}   >> 写入笔记: {fp}', flush=True)

                    elif name == 'ls':
                        once_stage('review', '阶段 3/4: 检查研究产出')
                        print(f'{elapsed()}   >> 列出文件: {args.get("path", "/")}', flush=True)

                    else:
                        args_str = str(args)
                        if len(args_str) > 150:
                            args_str = args_str[:150] + '...'
                        print(f'{elapsed()}   TOOL {name}: {args_str}', flush=True)

            # ── Tool Results (关键信息) ──
            elif mt == 'ToolMessage' and content:
                # 检测 researcher 进度汇报
                if '[进度]' in content:
                    for line in content.split('\n'):
                        if '[进度]' in line:
                            print(f'{elapsed()}     [进度] {line.split("[进度]")[1].strip()[:150]}', flush=True)
                elif '[完成]' in content:
                    print(f'{elapsed()}   <<< Researcher 完成!', flush=True)
                    # 提取前 200 字符展示
                    brief = content.replace('\n', ' ')[:250]
                    if brief:
                        print(f'{elapsed()}       {brief}', flush=True)
                elif 'Error' in content and len(content) < 300:
                    print(f'{elapsed()}   !! 错误: {content[:200]}', flush=True)
                elif '/notes/' in content and len(content) > 100:
                    # 可能包含笔记写入确认
                    brief = content.replace('\n', ' ')[:200]
                    print(f'{elapsed()}   << {brief}', flush=True)

            # ── AI 文本输出 ──
            elif mt == 'AIMessage' and len(content) > 15:
                # 只在有意义时展示
                short = content.replace('\n', ' ')[:400]
                if any(kw in short for kw in ['阶段', '完成', '报告', '计划', '研究', '进度']):
                    print(f'{elapsed()} [AI] {short}', flush=True)

            # ── 错误 ──
            elif mt == 'ToolMessage' and 'Error' in content:
                print(f'{elapsed()} !! ERR: {content[:200]}', flush=True)

except KeyboardInterrupt:
    print(f'\n{elapsed()} >>> 用户中断', flush=True)
except Exception as e:
    print(f'\n{elapsed()} >>> 错误: {type(e).__name__}: {e}', flush=True)

# ── 最终汇总 ───────────────────────────────────
total_time = time.time() - TS_START
m, s = divmod(int(total_time), 60)
print(f'\n{"="*60}')
print(f'  运行结束 | 总步数: {step} | 耗时: {m}分{s}秒')
print(f'{"="*60}', flush=True)

# 检查产出
print(f'\n  Workspace 内容:', flush=True)
for f in sorted(WORKSPACE_DIR.rglob('*')):
    if f.is_file():
        rel = str(f.relative_to(WORKSPACE_DIR))
        try:
            size = len(f.read_text(encoding='utf-8'))
            icon = 'REPORT' if 'report.md' in rel else 'NOTE' if 'notes/' in rel else 'SKILL'
            print(f'    [{icon}] {rel} ({size:,} chars)', flush=True)
        except:
            print(f'    [??] {rel}', flush=True)


def _archive_to_history(workspace: 'Path', topic: str):
    """将研究摘要归档到 history-database 目录。

    流程：
    1. 扫描已有分类文件夹
    2. 调 Summarizer LLM 做分类决策 + 内容浓缩
    3. 写入浓缩后的版本（非原文）
    """
    from datetime import date

    summary_file = workspace / 'research_summary.txt'
    if not summary_file.exists():
        print(f'  [WARN] 未找到 research_summary.txt，跳过历史归档', flush=True)
        return

    content = summary_file.read_text(encoding='utf-8')

    def _safe(s):
        return s.replace('/','-').replace('\\','-').replace(':','-').replace('?','').replace('"','')[:50].strip()

    # ── 扫描已有分类 ────────────────────────────────────
    history_base = workspace.parent / 'history-database'
    history_base.mkdir(parents=True, exist_ok=True)
    existing_categories = sorted([
        d.name for d in history_base.iterdir()
        if d.is_dir() and not d.name.startswith('.')
    ])

    # ── 调 LLM 做分类 + 浓缩 ────────────────────────────
    try:
        from deep_research.summarizer import condense_and_categorize
        print(f'  [归档] 正在浓缩并分类（已有 {len(existing_categories)} 个分类文件夹）...', flush=True)
        result = condense_and_categorize(content, existing_categories)
        category = _safe(result.get("category", "未分类"))
        condensed_content = result.get("condensed_summary", content)
        print(f'  [归档] 分类结果: {category}', flush=True)
    except Exception as e:
        print(f'  [WARN] Summarizer 调用失败，使用原文 + 未分类: {e}', flush=True)
        category = '未分类'
        condensed_content = content

    # ── 写入历史数据库 ───────────────────────────────────
    category_dir = history_base / category
    category_dir.mkdir(parents=True, exist_ok=True)

    today = date.today().isoformat()
    safe_topic = _safe(topic)
    filename = f'{today}_{safe_topic}.txt'
    filepath = category_dir / filename

    filepath.write_text(condensed_content, encoding='utf-8')
    print(f'  [OK] 研究摘要已归档: history-database/{category}/{filename} '
          f'(原文 {len(content):,} 字 → 浓缩 {len(condensed_content):,} 字)', flush=True)
    return filepath  # 返回路径供后续增量索引


# 尝试生成 docx
report = WORKSPACE_DIR / 'report.md'
if report.exists():
    try:
        from deep_research.report import convert_report
        docx = convert_report()
        print(f'\n  [OK] 报告已生成: {docx}', flush=True)
    except Exception as e:
        print(f'\n  [WARN] docx 生成失败: {e}', flush=True)
        print(f'         修复方法: pip uninstall docx -y && pip install python-docx', flush=True)

    # ── 归档到历史数据库 ──────────────────────────────
    archived_path = _archive_to_history(WORKSPACE_DIR, TOPIC)

    # ── 增量索引到向量知识库 ─────────────────────────
    if archived_path:
        try:
            from deep_research.knowledge_base import index_document, get_document_count
            print(f'  [知识库] {index_document(archived_path)}', flush=True)
            print(f'  [知识库] 当前向量库文档总数: {get_document_count()}', flush=True)
        except Exception as e:
            print(f'  [知识库] 索引失败（不影响主流程）: {e}', flush=True)
else:
    print(f'\n  [WARN] 未生成 report.md（研究未完成）', flush=True)
