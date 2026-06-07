"""
组装 supervisor 智能体。

使用 deepagents 框架的 create_deep_agent 将模型、提示词、
子智能体、文件系统后端和技能组合为一个可运行的 agent。
"""

import shutil

from . import config as cfg
from .model_factory import make_chat_model
from .prompts import (
    SUPERVISOR_PROMPT,
    HITL_INSTRUCTIONS,
    CRITIC_INSTRUCTIONS,
)
from .subagents import create_researcher_subagents, create_critic_subagent, create_verifier_subagent
from .tools import request_plan_approval
from .runtime_state import get_run, record_event


def create_supervisor_agent(resume: bool = False):
    """创建 supervisor 深度研究智能体。

    Args:
        resume: True 时保留已有 workspace 文件（断点恢复模式）。

    返回配置好的 agent 实例，可以直接调用 agent.invoke() 或 agent.stream()。
    """
    # ── 确保工作区目录存在 ──────────────────────────────────
    _prepare_workspace(resume=resume)

    # ── 创建 DeepSeek 模型（按角色设定推理深度） ──────────────
    model = make_chat_model("supervisor")

    # ── 设置文件系统后端 ────────────────────────────────────
    backend = _create_backend()

    # ── 加载技能 ──────────────────────────────────────────
    skills = _load_skills()

    # ── 创建子智能体 ──────────────────────────────────────
    subagents = create_researcher_subagents()
    critic = create_critic_subagent()
    if critic:
        subagents.append(critic)
    verifier = create_verifier_subagent()
    if verifier:
        subagents.append(verifier)

    # ── 组装 Supervisor prompt（条件注入 HITL / Critic 块）──
    hitl_block_text = HITL_INSTRUCTIONS.format(
        plan_revisions=cfg.PLAN_APPROVAL_MAX_REVISIONS
    ) if cfg.INTERACTIVE_PLAN_APPROVAL else ""

    critic_block_text = CRITIC_INSTRUCTIONS.format(
        critic_max_rounds=cfg.CRITIC_MAX_ROUNDS,
        search_limit=cfg.RESEARCHER_SEARCH_LIMIT,
    ) if cfg.CRITIC_ENABLED else ""

    time_constraint_text = ""
    if cfg.RESEARCH_TIMEOUT_MINUTES > 0:
        time_constraint_text = (
            f"\n## ⏱️ 时间限制\n\n"
            f"整个研究阶段（阶段1-4）必须在 **{cfg.RESEARCH_TIMEOUT_MINUTES} 分钟**内完成。"
            f"达到时限后，即使信息不完美也必须立即进入阶段5撰写报告。"
            f"不要在单个 researcher 上等太久——若某个 researcher 在2分钟内无响应，直接基于已有信息写报告。\n"
        )

    supervisor_prompt = SUPERVISOR_PROMPT.format(
        max_researchers=cfg.SUBAGENT_MAX_CONCURRENCY,
        search_limit=cfg.RESEARCHER_SEARCH_LIMIT,
        hitl_stage_marker="计划审批 (HITL)" if cfg.INTERACTIVE_PLAN_APPROVAL else "(未启用)",
        critic_stage_marker="Critic 反思" if cfg.CRITIC_ENABLED else "(未启用)",
        hitl_block=hitl_block_text,
        critic_block=critic_block_text,
        time_constraint=time_constraint_text,
        critic_enabled="✅ 已启用" if cfg.CRITIC_ENABLED else "❌ 未启用",
        hitl_enabled="✅ 已启用" if cfg.INTERACTIVE_PLAN_APPROVAL else "❌ 未启用",
    )

    # ── 组装 deep agent ────────────────────────────────────
    agent = _build_agent(
        model=model,
        system_prompt=supervisor_prompt,
        subagents=subagents,
        backend=backend,
        skills=skills,
    )

    return agent


def _prepare_workspace(resume: bool = False):
    """准备 workspace 目录，并将 skills 复制到 workspace/skills/。

    - 新 run (resume=False): 清空该 run 下的 workspace。
    - resume (resume=True): 确保目录存在，不删除已有文件。
    - 同时维护旧 workspace/ 兼容路径（LEGACY_WORKSPACE_COMPAT）。
    """
    import time as _time

    run = get_run()
    workspace = run.workspace_dir

    if not resume:
        # 新 run：清空该 run 的 workspace
        if workspace.exists():
            for _retry in range(3):
                try:
                    shutil.rmtree(workspace)
                    break
                except PermissionError:
                    if _retry < 2:
                        _time.sleep(0.5)
                    else:
                        for _child in workspace.iterdir():
                            try:
                                if _child.is_dir():
                                    shutil.rmtree(_child, ignore_errors=True)
                                else:
                                    _child.unlink(missing_ok=True)
                            except Exception:
                                pass
                        break
    # resume 或新 run 都需要确保目录存在
    workspace.mkdir(parents=True, exist_ok=True)
    (workspace / "notes").mkdir(exist_ok=True)

    # 将 skills 复制到 workspace 内，使 FilesystemBackend 可以访问
    workspace_skills = workspace / "skills"
    if cfg.SKILLS_DIR.exists():
        shutil.copytree(cfg.SKILLS_DIR, workspace_skills, dirs_exist_ok=True)

    # 旧 workspace/ 兼容：如果 LEGACY_WORKSPACE_COMPAT，同步 skills
    if cfg.LEGACY_WORKSPACE_COMPAT:
        cfg.WORKSPACE_DIR.mkdir(parents=True, exist_ok=True)
        (cfg.WORKSPACE_DIR / "notes").mkdir(exist_ok=True)
        legacy_skills = cfg.WORKSPACE_DIR / "skills"
        if cfg.SKILLS_DIR.exists():
            shutil.copytree(cfg.SKILLS_DIR, legacy_skills, dirs_exist_ok=True)

    record_event("workspace_prepared", {
        "workspace": str(workspace),
        "resume": resume,
    })


def _load_skills():
    """加载 skills，返回虚拟路径列表。

    Skills 已被复制到 run workspace/skills/，这里返回虚拟路径
    （相对于 workspace root），FilesystemBackend 可以正确解析。
    """
    skills = []
    workspace_skills = get_run().workspace_dir / "skills"
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

    使用本地磁盘后端，文件映射到当前 run 的 workspace 目录。
    好处：你可以在 agent 运行时打开 workspace/notes/ 目录，
    观察笔记文件一个一个出现——这是理解上下文卸载的最佳方式。
    """
    from deepagents.backends import FilesystemBackend

    return FilesystemBackend(root_dir=str(get_run().workspace_dir), virtual_mode=True)


def _build_agent(*, model, system_prompt, subagents, backend, skills):
    """调用 create_deep_agent 组装 supervisor agent。"""
    from deepagents import create_deep_agent

    # HITL 工具只给 Supervisor（不给 researcher）
    extra_tools = [request_plan_approval] if cfg.INTERACTIVE_PLAN_APPROVAL else None

    kwargs = dict(
        model=model,
        system_prompt=system_prompt,
        subagents=subagents,
        backend=backend,
        skills=skills,
    )
    if extra_tools:
        kwargs["tools"] = extra_tools

    return create_deep_agent(**kwargs)
