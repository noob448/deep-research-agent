#!/usr/bin/env python
"""
深度研究智能体 — 运行入口

用法:
    python examples/run.py "你的研究问题"

示例:
    python examples/run.py "量子计算对密码学的影响是什么？"
"""

import sys, time, warnings
from pathlib import Path
warnings.filterwarnings("ignore")

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from deep_research.agent import create_supervisor_agent
from deep_research.report import convert_report
from deep_research.config import WORKSPACE_DIR, RECURSION_LIMIT


def main():
    if len(sys.argv) < 2:
        print('用法: python examples/run.py "你的研究问题"')
        sys.exit(1)

    topic = sys.argv[1]
    t0 = time.time()

    print(f"""
╔══════════════════════════════════════════════════════╗
║          Deep Research Agent                        ║
║  Supervisor: deepseek-v4-pro (规划+委托+综合)       ║
║  Researcher x3: deepseek-v4-pro (搜索+提炼+笔记)    ║
╚══════════════════════════════════════════════════════╝
研究课题: {topic}
""")

    # 创建 agent
    print(">>> 初始化...", flush=True)
    agent = create_supervisor_agent()
    print(">>> 开始研究\n", flush=True)

    step = 0
    try:
        for event in agent.stream(
            {'messages': [{'role': 'user', 'content': topic}]},
            stream_mode='values',
            config={'recursion_limit': RECURSION_LIMIT},
        ):
            step += 1
            msgs = event.get('messages', [])
            for msg in msgs[-1:]:  # 只看最新消息
                _print_msg(msg, step)

    except KeyboardInterrupt:
        print('\n>>> 用户中断')
    except Exception as e:
        print(f'\n>>> 错误: {e}')

    elapsed = int(time.time() - t0)
    print(f'\n>>> 运行结束 | {step} 步 | {elapsed//60}分{elapsed%60}秒')

    # 产出
    report = WORKSPACE_DIR / 'report.md'
    if report.exists():
        print(f'>>> report.md: {len(report.read_text(encoding="utf-8")):,} chars')
        try:
            docx = convert_report()
            print(f'>>> {docx.name} 已生成')
        except Exception as e:
            print(f'>>> docx 失败: {e}')

    notes = list((WORKSPACE_DIR / 'notes').glob('*.md'))
    print(f'>>> 研究笔记: {len(notes)} 个')
    for n in notes:
        print(f'      {n.name} ({len(n.read_text(encoding="utf-8")):,} chars)')


def _print_msg(msg, step):
    mt = type(msg).__name__
    content = str(msg.content) if hasattr(msg, 'content') and msg.content else ''

    if hasattr(msg, 'tool_calls') and msg.tool_calls:
        for tc in msg.tool_calls:
            name = tc.get('name', '?')
            args = tc.get('args', {})
            if name == 'write_todos':
                n = len(args.get('todos', []))
                print(f'  [{step}] 制定计划: {n} 个子问题')
            elif name == 'task':
                desc = args.get('description', '')[:100]
                print(f'  [{step}] 派出研究员: {desc}...')
            elif name == 'write_file':
                fp = args.get('file_path', '')
                print(f'  [{step}] 写入文件: {fp}')
            elif name == 'read_file':
                print(f'  [{step}] 阅读: {args.get("file_path", "")}')
            else:
                print(f'  [{step}] {name}')

    elif mt == 'AIMessage' and len(content) > 20:
        short = content.replace('\n', ' ')[:300]
        print(f'  [{step}] AI: {short}')

    elif 'Error' in content:
        print(f'  [{step}] ERR: {content[:200]}')


if __name__ == '__main__':
    main()
