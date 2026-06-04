"""
组装 supervisor 智能体。

使用 deepagents 框架的 create_deep_agent 将模型、提示词、
子智能体、文件系统后端和技能组合为一个可运行的 agent。
"""

import shutil

from .config import WORKSPACE_DIR, SKILLS_DIR
from .model_factory import make_chat_model
from .prompts import SUPERVISOR_PROMPT
from .subagents import create_researcher_subagents


def create_supervisor_agent():
    """创建 supervisor 深度研究智能体。

    返回配置好的 agent 实例，可以直接调用 agent.invoke() 或 agent.stream()。
    """
    # ── 确保工作区目录存在 ──────────────────────────────────
    _prepare_workspace()

    # ── 创建 DeepSeek 模型（按角色设定推理深度） ──────────────
    model = make_chat_model("supervisor")

    # ── 设置文件系统后端 ────────────────────────────────────
    backend = _create_backend()

    # ── 加载技能 ──────────────────────────────────────────
    skills = _load_skills()

    # ── 创建 3 个独立命名的研究员子智能体 ──────────────────
    researchers = create_researcher_subagents()

    # ── 组装 deep agent ────────────────────────────────────
    # deepagents 框架会自动添加 write_todos, read_file, write_file,
    # task 等内置工具——我们不需要手动传入。
    agent = _build_agent(
        model=model,
        system_prompt=SUPERVISOR_PROMPT,
        subagents=researchers,
        backend=backend,
        skills=skills,
    )

    return agent


def _prepare_workspace():
    """准备干净的 workspace 目录，并将 skills 复制到 workspace/skills/。"""
    import time as _time
    if WORKSPACE_DIR.exists():
        for _retry in range(3):
            try:
                shutil.rmtree(WORKSPACE_DIR)
                break
            except PermissionError:
                if _retry < 2:
                    _time.sleep(0.5)
                else:
                    # 最后一次尝试：只清理子文件，保留根目录
                    for _child in WORKSPACE_DIR.iterdir():
                        try:
                            if _child.is_dir():
                                shutil.rmtree(_child, ignore_errors=True)
                            else:
                                _child.unlink(missing_ok=True)
                        except Exception:
                            pass
                    break
    WORKSPACE_DIR.mkdir(parents=True, exist_ok=True)
    (WORKSPACE_DIR / "notes").mkdir(exist_ok=True)

    # 将 skills 目录复制到 workspace 内，使 FilesystemBackend 可以访问
    workspace_skills = WORKSPACE_DIR / "skills"
    if SKILLS_DIR.exists():
        shutil.copytree(SKILLS_DIR, workspace_skills, dirs_exist_ok=True)


def _load_skills():
    """加载 skills，返回虚拟路径列表。

    Skills 已被复制到 workspace/skills/，这里返回虚拟路径
    （相对于 workspace root），FilesystemBackend 可以正确解析。
    """
    skills = []
    workspace_skills = WORKSPACE_DIR / "skills"
    if workspace_skills.exists():
        for skill_dir in workspace_skills.iterdir():
            if skill_dir.is_dir():
                skill_md = skill_dir / "SKILL.md"
                if skill_md.exists():
                    # 返回虚拟路径：/skills/<skill-name>
                    skills.append(f"/skills/{skill_dir.name}")
    return skills


def _create_backend():
    """创建本地文件系统后端。

    使用本地磁盘后端，文件映射到 ./workspace 目录。
    好处：你可以在 agent 运行时打开 workspace/notes/ 目录，
    观察笔记文件一个一个出现——这是理解上下文卸载的最佳方式。
    """
    from deepagents.backends import FilesystemBackend

    return FilesystemBackend(root_dir=str(WORKSPACE_DIR), virtual_mode=True)


def _build_agent(*, model, system_prompt, subagents, backend, skills):
    """调用 create_deep_agent 组装 supervisor agent。

    deepagents 框架会自动注入 write_todos、read_file、write_file、
    task 等内置工具——我们只提供业务层的东西。
    """
    from deepagents import create_deep_agent

    return create_deep_agent(
        model=model,
        system_prompt=system_prompt,
        subagents=subagents,
        backend=backend,
        skills=skills,
    )
