# 国内可用学术来源接入方案 · China-Accessible Academic Sources

> 本文件用于替换/扩展深度研究 agent 的学术搜索来源，使其在**中国大陆网络环境**下稳定可用。
> 它是一份可执行的接入方案，供编码助手（Claude Code，驱动 DeepSeek）按任务实现。
> 配套文件：`SEARCH_QUALITY_PLAN.md`（任务 5 原本用的 arXiv 工具，本方案将其替换为大陆可达的来源）。

---

## 0. 给编码助手的执行规则

1. 一次只接入一个来源，做完跑「验证」、确认可返回真实论文后，再接下一个。
2. 只新增/修改本方案指出的文件（主要是 `deep_research/tools.py`、`agent.py`、`config.py`）。
3. 新建 `.py` 文件第一行写 `# -*- coding: utf-8 -*-`。
4. 所有外部请求**必须设置超时 + 异常捕获**（网络环境不稳定，不能让单个请求卡死整个 agent）。
5. 网络可达性因用户网络而异，**不要假设某个源一定通**；以「验证」命令的实际结果为准，通不过就换备选源。

---

## 1. 背景与核心结论

**问题**：之前推荐的 arXiv / Semantic Scholar 等国际学术站点在大陆访问不稳定。

**关键现实（决定接入策略）**：
- 国内**最权威、最前沿**的平台（PubScholar、ChinaXiv、AMiner）是面向人使用的网站，**没有开放给第三方的免费开发者 API**，难以直接给 agent 程序化调用。
- 真正**有干净免费 API、且大陆通常可达**的，是 OpenAlex、Crossref 这类"开放科学"基础设施——它们不在防火墙封锁之列，且覆盖中外文献。

**因此本方案的策略**：

| 角色 | 选用来源 | 理由 |
|---|---|---|
| **程序化主干（agent 直接调用）** | **OpenAlex**（首选）+ Crossref（补充） | 免费、无需 key、有真 REST API、大陆通常可达、覆盖 2.4 亿+ 论文 |
| **国产 AI 搜索（可选增强）** | **秘塔 Metaso API / MCP** | 国产、有学术模式与研究模式、自带引用、有 API/MCP；偏商业化 |
| **人工/网页参考（agent 用 web_fetch 或你手动用）** | PubScholar、ChinaXiv、AMiner | 权威、前沿、带 AI 综述，但无免费开发 API |
| **arXiv 加速（按需取全文）** | 镜像 `xxx.itp.ac.cn` | 加速网页/PDF，非 API |

---

## 2. 全景对比表（选型参考）

| 平台 | 归属 | 免费 | 公开免费 API | 大陆可达 | 覆盖 | 前沿/AI 能力 | 给 agent 用的方式 |
|---|---|---|---|---|---|---|---|
| **OpenAlex** | 开放科学(非营利) | ✅ | ✅ 无需 key | ✅ 通常可达 | 2.4 亿+ 中外论文 | 语义搜索 | **REST API 直接调用（首选）** |
| **Crossref** | 开放科学(非营利) | ✅ | ✅ 无需 key | ✅ 通常可达 | 全球 DOI 元数据 | — | REST API（补充 DOI/元数据） |
| **arXiv API** | 康奈尔大学 | ✅ | ✅ | ⚠️ 时通时不通 | 理工预印本 | — | API（不稳，OpenAlex 已含 arXiv） |
| **arXiv 镜像** | 中科院理论物理所 | ✅ | ❌(网页) | ✅ 快 | 同 arXiv | — | web_fetch 取网页/PDF |
| **秘塔 Metaso** | 上海秘塔科技 | 部分免费 | ✅ 有 API/MCP(偏商业) | ✅ | 数千万 OA 论文 | ✅ 研究模式自动生成综述+引用 | API / MCP 接入 |
| **PubScholar** | 中科院文献情报中心 | ✅ | ❌ 无开放开发 API | ✅ | 1.7 亿元数据/8000 万全文 | ✅ 智能综述/AI 对话/文献精读 | web_fetch 或手动 |
| **ChinaXiv** | 中科院文献情报中心 | ✅ | ❌ 无开放开发 API | ✅ | 中英文预印本 | 开放评阅 | web_fetch 或手动 |
| **AMiner** | 清华唐杰团队 | 部分免费 | ⚠️ API 面向机构 | ✅ | 2.3 亿+ 论文/学者图谱 | ✅ "沉思"GLM 深度思考助手 | 机构 API / 手动 |
| **CSTCloud 云评** | 中科院网络信息中心 | ✅ | ⚠️ 面向院内单位 | ✅ | arXiv+ChinaXiv+bioRxiv+medRxiv 300 万+ | 论文检索 API | 仅院内可申请 |
| **CNKI/万方/维普** | 商业 | ❌ 付费 | ⚠️ 订阅用户 | ✅ | 中文期刊/学位论文最全 | — | 需机构订阅 |

> 说明：「大陆可达」一栏为一般情况，实际以你的网络 + 本文「验证」命令结果为准。

---

## 3. 落地代码

### 任务 1 · 接入 OpenAlex（首选，免费无 key）

**目标**：用 OpenAlex 替换原 `SEARCH_QUALITY_PLAN.md` 任务 5 中的 arXiv 工具，作为 agent 的主学术检索源。

**涉及文件**：`deep_research/tools.py`（新增工具）、`deep_research/agent.py`（注册）

**依赖**：无（标准库即可）

**实现** — 在 `tools.py` 新增：

```python
# -*- coding: utf-8 -*-
import json
import urllib.parse
import urllib.request
from langchain_core.tools import tool

# 建议填入你的邮箱，进入 OpenAlex "礼貌池"，响应更快更稳定（非必填）
_OPENALEX_MAILTO = "your_email@example.com"


def _reconstruct_abstract(inverted_index) -> str:
    """OpenAlex 的摘要以倒排索引(inverted index)存储，需还原为正常文本。"""
    if not inverted_index:
        return "（无摘要）"
    positions = {}
    for word, idx_list in inverted_index.items():
        for i in idx_list:
            positions[i] = word
    return " ".join(positions[i] for i in sorted(positions))


@tool
def search_openalex(query: str, max_results: int = 5) -> str:
    """检索 OpenAlex 学术文献库（免费，覆盖 2.4 亿+ 中外论文）。
    当课题偏学术、需要同行评审文献时优先使用。返回标题、年份、作者、摘要和链接。"""
    base = "https://api.openalex.org/works?"
    params = urllib.parse.urlencode({
        "search": query,
        "per-page": max_results,
        "mailto": _OPENALEX_MAILTO,
    })
    req = urllib.request.Request(
        base + params,
        headers={"User-Agent": "deep-research-agent"},
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            data = json.loads(resp.read().decode("utf-8"))
    except Exception as e:
        return f"OpenAlex 检索失败（网络或服务问题）：{e}"

    works = data.get("results", [])
    if not works:
        return "OpenAlex 未找到相关论文。"

    out = []
    for w in works:
        title = w.get("title") or w.get("display_name") or "（无标题）"
        year = w.get("publication_year", "")
        doi = w.get("doi") or ""
        loc = w.get("primary_location") or {}
        url = loc.get("landing_page_url") or doi or ""
        authors = [
            a.get("author", {}).get("display_name", "")
            for a in (w.get("authorships") or [])[:5]
        ]
        abstract = _reconstruct_abstract(w.get("abstract_inverted_index"))
        out.append(
            f"标题: {title}\n年份: {year}\n作者: {', '.join(filter(None, authors))}\n"
            f"链接: {url}\n摘要: {abstract[:500]}"
        )
    return "\n\n".join(out)
```

然后在 `agent.py` 把 `search_openalex` 加入工具列表（与 `web_search` 并列）。无需改提示词，docstring 已说明何时使用。

**验证**

```bash
python -c "from deep_research.tools import search_openalex; print(search_openalex.invoke({'query':'large language model agents','max_results':2}))"
```
预期：打印 2 条真实论文（标题/年份/作者/链接/摘要）。若返回"检索失败"，说明该网络访问 OpenAlex 受阻，转任务 3 的秘塔方案。

**完成标准**：能返回真实论文且已注册进 agent；学术课题下 agent 会调用它。

---

### 任务 2 · 接入 Crossref（补充 DOI 与元数据）

**目标**：作为 OpenAlex 的补充，按标题/关键词查 DOI 和权威元数据（引用格式更规范）。

**涉及文件**：`deep_research/tools.py`

**依赖**：无

**实现**

```python
@tool
def search_crossref(query: str, max_results: int = 5) -> str:
    """检索 Crossref 学术元数据库（免费），适合获取论文的 DOI、作者、期刊和年份。
    需要规范引用信息时使用。"""
    base = "https://api.crossref.org/works?"
    params = urllib.parse.urlencode({
        "query": query,
        "rows": max_results,
        "mailto": _OPENALEX_MAILTO,  # 复用上面的邮箱即可
    })
    req = urllib.request.Request(base + params, headers={"User-Agent": "deep-research-agent"})
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            data = json.loads(resp.read().decode("utf-8"))
    except Exception as e:
        return f"Crossref 检索失败：{e}"

    items = data.get("message", {}).get("items", [])
    if not items:
        return "Crossref 未找到相关条目。"

    out = []
    for it in items:
        title = (it.get("title") or ["（无标题）"])[0]
        doi = it.get("DOI", "")
        url = it.get("URL", "")
        year = ""
        try:
            year = it.get("published", {}).get("date-parts", [[None]])[0][0] or ""
        except Exception:
            pass
        authors = [
            f"{a.get('given','')} {a.get('family','')}".strip()
            for a in (it.get("author") or [])[:5]
        ]
        out.append(f"标题: {title}\n年份: {year}\nDOI: {doi}\n链接: {url}\n作者: {', '.join(authors)}")
    return "\n\n".join(out)
```

**验证**

```bash
python -c "from deep_research.tools import search_crossref; print(search_crossref.invoke({'query':'retrieval augmented generation','max_results':2}))"
```
预期：返回 2 条带 DOI 的条目。

**完成标准**：能返回真实 DOI/元数据并已注册。

---

### 任务 3（可选）· 接入秘塔 Metaso（国产 AI 搜索 + 研究模式）

**目标**：若你想要一个**国产、自带研究模式（生成综述+引用）**的搜索层，接入秘塔 API 或其 MCP。秘塔有"学术模式"和"研究模式"，本身就接近一个轻量 deep research。

**前置**：需在秘塔开放平台申请 API Key（偏商业化，按量计费）。MCP 方式则配置其 MCP server。

**实现（HTTP API 思路，具体端点以秘塔官方文档为准）**

```python
import os

@tool
def search_metaso(query: str) -> str:
    """使用秘塔 AI 搜索（学术模式）检索中外 Open Access 论文，返回带来源引用的结果。
    适合需要中文语境、或希望搜索引擎侧已做初步综合时使用。"""
    api_key = os.environ.get("METASO_API_KEY", "")
    if not api_key:
        return "未配置 METASO_API_KEY，无法使用秘塔搜索。"
    # 注意：以下端点/字段为示意，请对照秘塔开放平台最新文档填写
    import urllib.request, json
    url = "https://metaso.cn/api/v1/search"   # 占位，以官方文档为准
    body = json.dumps({"q": query, "mode": "academic"}).encode("utf-8")
    req = urllib.request.Request(
        url, data=body,
        headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        return json.dumps(data, ensure_ascii=False)[:2000]
    except Exception as e:
        return f"秘塔检索失败：{e}"
```

> **重要**：秘塔的具体 API 端点、请求体、鉴权方式请以其开放平台**官方文档**为准，上面仅为接入骨架。也可改用其 **MCP server**，按 `mcp_app` 方式配置后由 agent 调用。

**完成标准**：配置 key 后能返回带来源的搜索结果。

---

### 任务 4 · 在 config 中集中管理来源开关

**涉及文件**：`deep_research/config.py`

```python
# ===== 学术来源开关 =====
use_openalex: bool = True       # 首选，免费
use_crossref: bool = True       # 补充元数据
use_metaso: bool = False        # 国产 AI 搜索（需 API key，默认关）
academic_mailto: str = "your_email@example.com"   # OpenAlex/Crossref 礼貌池邮箱
```

在 `agent.py` 注册工具时按开关决定加入哪些，便于按网络情况灵活切换。

---

## 4. 人工/网页类平台怎么用（PubScholar / ChinaXiv / AMiner）

这三个平台**权威且前沿**（PubScholar 有智能综述、AMiner 有 GLM"沉思"助手），但没有免费开发 API，给 agent 用有两条路：

1. **agent 用 web_fetch 抓搜索结果页**：让 agent 访问它们的搜索 URL（如 `https://pubscholar.cn` 的检索结果页），再解析返回的 HTML。缺点：页面结构可能变、解析脆弱；适合作为补充而非主力。
2. **你手动用作研究辅助**：在写报告的关键节点，自己上这些平台用其 AI 综述/精读功能交叉验证，再把要点喂给 agent。对学习和质量把控反而更有效。

> 经验建议：**自动化主干仍用 OpenAlex/Crossref；PubScholar/AMiner 作为你手动深挖和交叉验证的工具。** 不要为了"全自动"去硬爬这些站点，性价比低且不稳定。

**各平台入口**：
- PubScholar：`https://pubscholar.cn`（中科院公益平台，免费，带 AI 检索/智能综述）
- ChinaXiv：`https://chinaxiv.org`（中科院预印本，免费）
- AMiner：`https://www.aminer.cn`（清华，"沉思"AI 助手）

**arXiv 取全文加速**：把 `arxiv.org` 换成 `xxx.itp.ac.cn`（中科院理论物理所镜像）即可，例如 `http://xxx.itp.ac.cn/abs/2401.00001`。可在 agent 需要下载 arXiv PDF/网页时用 web_fetch 走镜像。

---

## 5. 推荐实施顺序

1. **先做任务 1（OpenAlex）**：免费、无 key、覆盖中外，跑通它你的学术检索就基本可用了。
2. **再做任务 2（Crossref）**：补充规范的 DOI 与引用元数据。
3. **任务 4（config 开关）**：把来源做成可切换。
4. **按需做任务 3（秘塔）**：想要国产 AI 搜索 + 研究模式、且愿意用付费 API/MCP 时再加。
5. **PubScholar/AMiner**：作为你手动交叉验证的工具，必要时让 agent 用 web_fetch 补充。

---

## 6. 取舍建议（一句话）

> **能稳定给 agent 自动调用的免费学术 API，现实里是 OpenAlex（首选）+ Crossref——它们开放、免费、覆盖中外、大陆通常可达；国内最前沿的 PubScholar / AMiner 更适合你手动深挖。** 先把 OpenAlex 接通，你的"访问难"问题就解决了大半；其余按需叠加。

---

## 7. 注意事项

- 所有外部 API 调用务必保留 `try/except` + `timeout`，单源失败要能优雅降级，不拖垮整个研究流程。
- OpenAlex / Crossref 建议填 `mailto`（你的邮箱），进入礼貌池后更稳定。
- 若某天 OpenAlex 在你网络下变慢，可加重试，或临时切到秘塔/镜像。
- 各来源的实际字段以其**官方文档/接口返回**为准；本文件给的是接入骨架与正确用法，DeepSeek 实现时若遇字段不符，按实际返回调整并提示你。
