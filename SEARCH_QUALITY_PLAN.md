# 搜索质量优化方案 · Search Quality Improvement Plan

> 本文件是一份**实施规划（spec）**，用于指导编码助手（Claude Code，驱动 DeepSeek 模型）逐步改造本项目的检索环节。
> 它不是说明文档，而是**可执行的任务清单**。请按顺序逐任务实现。

---

## 0. 给编码助手的执行规则（请先读这一节）

实现本方案时，严格遵守以下规则：

1. **一次只做一个任务。** 完成一个任务、跑通它的「验证」、确认「完成标准」后，再开始下一个。
2. **改动最小化。** 只修改任务中明确指出的文件，不要顺手重构、重命名或"优化"无关代码。
3. **沿用现有风格。** 新建的 `.py` 文件第一行必须是 `# -*- coding: utf-8 -*-`（本项目代码含中文注释）。
4. **不破坏核心编排。** 本方案只增强"检索"环节，**不得改动**主管-研究员（supervisor-researcher）的委派逻辑、子 agent 结构、文件边界机制。
5. **遇到不确定时停下来问，不要臆测**项目中不存在的函数或文件。本文件第 3 节给出了假设的项目结构，若实际不符，以实际为准并提示用户。
6. 所有新增的可调参数，统一放进 `deep_research/config.py`，不要散落在各处硬编码。

---

## 1. 背景与目标

- **项目**：基于 `deepagents`（构建在 LangGraph 之上）的深度研究 agent，采用主管-研究员架构。给定课题 → 主管规划子问题 → 研究员子 agent 并行搜索并蒸馏成笔记 → 主管综合成论文式报告。
- **模型**：DeepSeek（OpenAI 兼容接口）。主管 `openai:deepseek-reasoner`，研究员 `openai:deepseek-chat`。
- **搜索后端**：Tavily。
- **当前问题**：研究员从**通用网络**搜回的内容噪音大、质量参差，混入博客、营销软文、内容农场，导致报告质量不稳定。
- **优化目标**：在三个入口分别降噪——**搜哪里**（来源）、**怎么搜**（参数与查询）、**留什么**（重排与质量判断）——从而显著提升最终报告质量。

**核心思路一句话**：与其让 agent 在垃圾堆里挑金子，不如先别让它进垃圾堆（搜对地方）、再给它一个筛子（重排）、最后教它认金子（质量准则）。

---

## 2. 关键约束（事实，避免臆测）

> 以下是已确认的技术事实，实现时直接采用，**不要**自行假设相反的情况。

- **DeepSeek 只提供对话（chat）模型，不提供 embedding / reranker 模型。** 因此本方案中所有需要 embedding 或 reranking 的环节，**一律使用本地开源模型**（通过 `sentence-transformers` 加载，免费、不联网）。不要试图调用 DeepSeek 做 embedding 或 rerank。
- **重排（reranking）是本方案中性价比最高的单点优化**：多项研究表明，适度的重排往往比增加搜索时推理带来更大的质量收益，且成本更低。优先保证这一环节正确实现。
- 学术搜索源（arXiv / Semantic Scholar / OpenAlex）的 API **免费**，适合论文型研究，作为可选增强。
- Tavily 每条搜索结果都带 `score`（相关性分数）字段，可用于阈值过滤。

---

## 3. 假设的项目结构（用于定位文件）

```
项目根目录/
├── deep_research/
│   ├── __init__.py
│   ├── agent.py          # 组装 deep agent（create_deep_agent 调用）
│   ├── config.py         # 所有可调参数（本方案将在此新增字段）
│   ├── prompts.py        # 主管 + 研究员系统提示词（任务 2 修改）
│   ├── subagents.py      # 研究员子 agent 声明
│   ├── tools.py          # web_search / web_fetch 工具（任务 1、4、5 修改）
│   ├── report.py         # 报告 → Word
│   └── rerank.py         # 【新增】重排模块（任务 4 创建）
├── skills/
│   ├── academic-report/
│   │   └── SKILL.md
│   └── source-quality/   # 【新增】来源质量 skill（任务 3 创建）
│       └── SKILL.md
└── examples/
    └── run.py
```

> 若实际文件名或路径与上表不同，以实际项目为准，并在动手前向用户确认对应关系。

---

## 4. 实施任务

> 按编号顺序执行。每个任务都包含：**目标 / 涉及文件 / 依赖 / 实现 / 验证 / 完成标准**。

---

### 任务 1 · 搜索参数调优 + 域名过滤

**目标**：用最小改动消除一批低质量结果——提高检索精度、按相关性分数过滤、可选地限制可信域名。

**涉及文件**：`deep_research/config.py`、`deep_research/tools.py`

**依赖**：无（沿用已安装的 Tavily 客户端）

**实现**

第一步，在 `config.py` 的配置类中新增以下字段（若已有 Settings/BaseSettings 类，加进去即可）：

```python
# ===== 搜索质量相关参数 =====
search_depth: str = "advanced"        # Tavily 高级模式：提取与查询高度对齐的正文片段
max_search_results: int = 8           # 单次搜索返回的原始结果数（重排前）；不宜过大
min_relevance_score: float = 0.5      # 低于此相关性分数的结果直接丢弃
trusted_domains: list[str] = []       # 仅搜这些域名（空 = 不限制）。学术场景可填:
                                      # ["arxiv.org", "nature.com", "sciencedirect.com", ".edu", ".gov"]
blocked_domains: list[str] = []       # 排除的低质域名，如内容农场
```

第二步，改造 `tools.py` 里的 `web_search` 工具，应用上述参数并按分数过滤：

```python
# -*- coding: utf-8 -*-
from langchain_core.tools import tool
from .config import settings
# 假设已有全局 tavily_client = TavilyClient(api_key=...)

@tool
def web_search(query: str) -> str:
    """搜索可信来源的网络内容，返回与查询最相关的若干结果。
    用于研究阶段获取外部信息。查询应尽量具体、聚焦。"""
    kwargs = dict(
        query=query,
        search_depth=settings.search_depth,
        max_results=settings.max_search_results,
    )
    if settings.trusted_domains:
        kwargs["include_domains"] = settings.trusted_domains
    if settings.blocked_domains:
        kwargs["exclude_domains"] = settings.blocked_domains

    resp = tavily_client.search(**kwargs)
    results = resp.get("results", [])

    # 按相关性分数过滤掉低质结果
    results = [r for r in results if r.get("score", 0) >= settings.min_relevance_score]

    if not results:
        return "未找到达到相关性阈值的结果，请尝试更换或细化查询。"

    return _format_results(results)   # 沿用项目已有的格式化函数


def _format_results(results: list) -> str:
    lines = []
    for i, r in enumerate(results, 1):
        title = r.get("title", "")
        url = r.get("url", "")
        content = r.get("content", "")
        lines.append(f"[{i}] {title}\nURL: {url}\n{content}")
    return "\n\n".join(lines)
```

**验证**

```bash
python -c "from deep_research.config import settings; print(settings.search_depth, settings.max_search_results, settings.min_relevance_score)"
```
预期输出：`advanced 8 0.5`

**完成标准**：配置可正常读取；`web_search` 运行时不再返回低于阈值分数的结果；域名列表为空时行为与原来一致（不报错）。

---

### 任务 2 · 查询窄化（提示词改动）

**目标**：噪音常来自查询太宽。让研究员把宽问题拆成**具体、狭窄**的子查询并分别搜索，而不是用一个大而泛的查询搜一次。

**涉及文件**：`deep_research/prompts.py`（研究员 researcher 的系统提示词）

**依赖**：无

**实现**

在研究员提示词中**插入**以下指令段（不要删改已有内容，只追加这一块）：

```text
## 搜索查询规范
- 把宽泛的问题拆成具体、聚焦的子查询，逐个搜索，不要用一个笼统的查询搜一次。
  反例（太宽）："睡眠与健康"
  正例（聚焦）："REM 睡眠剥夺对成人记忆巩固的影响"
- 每个子查询只针对一个明确的子问题；需要多角度时，发起多次窄查询。
- 若一次搜索结果质量不佳，换用更具体的措辞或更换关键术语再搜，不要在同一个宽查询上重复。
```

**验证**

```bash
python -c "from deep_research.prompts import RESEARCHER_PROMPT; print('搜索查询规范' in RESEARCHER_PROMPT)"
```
（把 `RESEARCHER_PROMPT` 换成项目里研究员提示词的实际变量名）
预期输出：`True`

**完成标准**：研究员提示词包含查询窄化指令；实际运行时可观察到研究员发起的是多个具体查询而非单个宽查询。

---

### 任务 3 · 来源质量 Skill（教 agent 认金子）

**目标**：给研究员一套"来源质量判断"准则。这属于 agent 的"判断力"层，用 skill 承载（skill = 渐进式披露的提示词片段，仅在相关时加载）。

**涉及文件**：`skills/source-quality/SKILL.md`（新建）；确认 `config.py` 的 skills 目录扫描包含 `skills/`

**依赖**：无

**实现**

新建文件 `skills/source-quality/SKILL.md`，内容如下：

```markdown
---
name: source-quality
description: "Use when evaluating, filtering, or citing search results during
  research. Provides criteria for judging source credibility and handling
  conflicting or low-quality evidence."
---

# 来源质量准则

## 优先采用
- 同行评审论文、官方/政府数据、一手资料、近期权威来源

## 保持警惕（降权或舍弃）
- 无发表日期的内容、内容农场、营销软文、缺乏出处的二手转述

## 处理规则
1. 关键论断必须跨 ≥2 个独立来源交叉验证后才写入笔记。
2. 来源可信度存疑时，在笔记里显式标注「该来源可信度较低」，不要直接当作事实陈述。
3. 多个来源冲突时，记录分歧本身，并指出各自来源，不要单方面下结论。
4. 宁可少而准，不要多而杂——舍弃与子问题无关但"看起来相关"的内容。
```

**验证**

```bash
python -c "import os; print(os.path.exists('skills/source-quality/SKILL.md'))"
```
预期输出：`True`

**完成标准**：skill 文件存在且被 agent 的 skills 目录扫描到；研究员在处理搜索结果时会参考质量准则（可在 trace 中观察到它对弱来源的标注/舍弃）。

---

### 任务 4 · 检索重排（最高性价比，重点实现）

**目标**：在搜索和"写入笔记"之间插入一个**重排**环节——多搜回一些结果，用本地 reranker 按"与查询的相关性"重新打分，只保留最相关的前几条。这是本方案中质量收益最大的一步。

**涉及文件**：`deep_research/rerank.py`（新建）、`deep_research/tools.py`（接入）、`deep_research/config.py`（参数）

**依赖**

```bash
pip install sentence-transformers
```
> 首次运行会自动下载 reranker 模型（约几百 MB），需联网一次；之后本地缓存、离线可用。

**实现**

第一步，`config.py` 新增：

```python
# ===== 重排相关参数 =====
rerank_enabled: bool = True
rerank_model: str = "BAAI/bge-reranker-v2-m3"   # 本地开源 reranker，免费
rerank_top_k: int = 4                           # 重排后保留的结果数
```

> 配合任务 1：建议把 `max_search_results` 设为 8~15（多搜回），由 `rerank_top_k`=4 收敛到最相关的少数几条。"多搜 → 精排 → 少留"是标准两段式策略。

第二步，新建 `deep_research/rerank.py`：

```python
# -*- coding: utf-8 -*-
"""检索结果重排：先多搜回，再按与查询的相关性精排，只留 top_k。"""
from functools import lru_cache
from .config import settings


@lru_cache(maxsize=1)
def _get_reranker():
    # 延迟加载并缓存，避免每次调用都重新载入模型
    from sentence_transformers import CrossEncoder
    return CrossEncoder(settings.rerank_model)


def rerank_results(query: str, results: list, top_k: int | None = None) -> list:
    """对搜索结果按与 query 的相关性重排，返回最相关的 top_k 条。
    results: 形如 [{"title":..., "url":..., "content":...}, ...]
    """
    if not results:
        return results
    top_k = top_k or settings.rerank_top_k

    model = _get_reranker()
    pairs = [(query, r.get("content", "")) for r in results]
    scores = model.predict(pairs)

    ranked = sorted(
        zip(results, scores),
        key=lambda pair: float(pair[1]),
        reverse=True,
    )
    return [r for r, _ in ranked[:top_k]]
```

第三步，在 `tools.py` 的 `web_search` 中接入（在分数过滤之后、格式化之前）：

```python
from .rerank import rerank_results
from .config import settings

# ...（任务 1 中分数过滤之后）...
if settings.rerank_enabled and len(results) > settings.rerank_top_k:
    results = rerank_results(query, results)

return _format_results(results)
```

**验证**

新建临时脚本 `verify_rerank.py` 并运行：

```python
# -*- coding: utf-8 -*-
from deep_research.rerank import rerank_results

fake = [
    {"title": "无关", "url": "u1", "content": "如何烤蛋糕的家庭食谱"},
    {"title": "相关", "url": "u2", "content": "REM 睡眠剥夺会损害成人记忆巩固"},
    {"title": "弱相关", "url": "u3", "content": "睡眠是一种常见的生理现象"},
]
top = rerank_results("睡眠剥夺对记忆的影响", fake, top_k=2)
for r in top:
    print(r["title"], "-", r["url"])
```
```bash
python verify_rerank.py
```
预期：输出 2 条，且「相关」(u2) 排在最前。验证通过后可删除该临时脚本。

**完成标准**：reranker 能正确加载；`rerank_results` 按相关性排序并截断；`web_search` 接入后，返回结果数等于 `rerank_top_k` 且明显更聚焦。

---

### 任务 5（可选）· 接入学术搜索源

**目标**：对学术/论文型课题，从根上把"杂"换成"精"——增加一个**只搜论文**的工具，与通用 `web_search` 并列，由 agent 自行选择。

**涉及文件**：`deep_research/tools.py`（新增工具）、`deep_research/agent.py`（注册工具）

**依赖**：无（直接调用免费学术 API；以下示例用 arXiv）

**实现**

在 `tools.py` 新增一个 arXiv 搜索工具（最简、免费、无需 key）：

```python
# -*- coding: utf-8 -*-
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from langchain_core.tools import tool


@tool
def search_papers(query: str, max_results: int = 5) -> str:
    """检索 arXiv 上的学术论文。当课题偏学术、需要同行评审/预印本一手文献时，
    优先使用本工具而非通用网络搜索。返回论文标题、作者、摘要和链接。"""
    base = "http://export.arxiv.org/api/query?"
    params = urllib.parse.urlencode({
        "search_query": f"all:{query}",
        "start": 0,
        "max_results": max_results,
    })
    with urllib.request.urlopen(base + params, timeout=30) as resp:
        data = resp.read()

    ns = {"a": "http://www.w3.org/2005/Atom"}
    root = ET.fromstring(data)
    entries = root.findall("a:entry", ns)
    if not entries:
        return "arXiv 未找到相关论文。"

    out = []
    for e in entries:
        title = (e.find("a:title", ns).text or "").strip()
        summary = (e.find("a:summary", ns).text or "").strip()
        link = (e.find("a:id", ns).text or "").strip()
        authors = [a.find("a:name", ns).text for a in e.findall("a:author", ns)]
        out.append(
            f"标题: {title}\n作者: {', '.join(filter(None, authors))}\n"
            f"链接: {link}\n摘要: {summary}"
        )
    return "\n\n".join(out)
```

然后在 `agent.py` 里把 `search_papers` 和 `web_search` 一起注册进 agent 的工具列表。无需修改提示词——`search_papers` 的 docstring 已说明"何时优先使用"，agent 会据此自主路由。

> **延伸**：同理可再加 Semantic Scholar / OpenAlex 工具（均免费），或接入 Exa（语义/神经检索，新账号有免费额度）。当前主流做法是"多源路由"：通用问题用 web 搜，学术综述用论文源，由 agent 按查询意图选择。一次只加一个源，跑通再加下一个。

**验证**

```bash
python -c "from deep_research.tools import search_papers; print(search_papers.invoke({'query':'large language model agents','max_results':2})[:200])"
```
预期：打印出 arXiv 返回的论文标题/摘要片段（前 200 字）。

**完成标准**：`search_papers` 能返回真实论文；已注册进 agent；学术课题下 agent 会调用它。

---

## 5. 依赖安装汇总

```bash
# 任务 4 必需（本地 reranker）
pip install sentence-transformers

# 任务 1、2、3、5 无新增依赖
```

> 提醒：确认在项目对应的 Python/conda 环境中安装（先激活环境再 pip install）。

---

## 6. 配置项汇总（`config.py` 本方案新增字段一览）

```python
# 搜索质量
search_depth: str = "advanced"
max_search_results: int = 8
min_relevance_score: float = 0.5
trusted_domains: list[str] = []
blocked_domains: list[str] = []

# 重排
rerank_enabled: bool = True
rerank_model: str = "BAAI/bge-reranker-v2-m3"
rerank_top_k: int = 4
```

---

## 7. 验收清单（全部完成后逐项确认）

- [ ] 任务 1：`web_search` 应用了 advanced 深度、分数过滤、域名过滤；配置可读取
- [ ] 任务 2：研究员提示词包含「搜索查询规范」，实际发起多个窄查询
- [ ] 任务 3：`skills/source-quality/SKILL.md` 存在且被扫描到
- [ ] 任务 4：`rerank.py` 可加载模型并正确排序；已接入 `web_search`；临时验证脚本已删除
- [ ] 任务 5（可选）：`search_papers` 可返回真实论文并已注册
- [ ] 端到端：跑一次完整研究任务，对比改造前后报告质量（来源更权威、内容更聚焦、无关信息明显减少）

---

## 8. 调优与回退建议

- **想要质量更高 / 速度更慢**：调大 `max_search_results`（多搜回）+ 保持 `rerank_top_k` 较小（精排收敛）。
- **想要速度更快 / 成本更低**：`search_depth` 改回 `"basic"`，或临时 `rerank_enabled=False`。
- **结果仍偏杂**：优先用 `trusted_domains` 收紧来源，或对学术课题改用任务 5 的论文源——这比在通用网络里反复过滤更有效。
- **reranker 下载失败/环境受限**：临时设 `rerank_enabled=False` 退回到"仅分数过滤"，不影响其余环节运行。
- **每一步都应可独立开关、可回退**，不要把多个改动耦合在一起，便于定位质量变化来自哪个环节。

---

## 9. 实施顺序建议（给用户的优先级）

1. **先做任务 1 + 任务 2**：改几行/加一段提示词，当天见效。
2. **再做任务 3**：加一个 skill，让 agent 学会判断来源质量。
3. **重点做任务 4（重排）**：本方案质量收益最大的单点优化。
4. **若主要做学术研究**：做任务 5，从根上提升来源质量。

> 不要一次全上。每完成一档，跑一次真实任务感受提升，再进入下一档。
