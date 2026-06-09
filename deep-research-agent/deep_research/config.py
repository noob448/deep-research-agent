"""
集中配置：模型、搜索深度、递归限制、工作区路径、技能路径。

所有可调参数集中在这里，修改一行即可影响整个系统。
"""

import os
from pathlib import Path

# ─── 项目路径 ───────────────────────────────────────────
PROJECT_ROOT = Path(__file__).resolve().parent.parent  # deep-research-agent/
WORKSPACE_DIR = PROJECT_ROOT / "workspace"
SKILLS_DIR = Path(__file__).resolve().parent / "skills"  # deep_research/skills/

# ── Run / State 配置 ───────────────────────────────────
RUNS_DIR = PROJECT_ROOT / "runs"
DEFAULT_RUN_ID_FORMAT = "%Y%m%d_%H%M%S"
STATE_SCHEMA_VERSION = 1
ENABLE_RUN_STATE = True
COPY_LATEST_TO_WORKSPACE = True
LEGACY_WORKSPACE_COMPAT = True

# 事件日志与账本文件名
EVENT_LOG_FILENAME = "events.jsonl"
PROGRESS_FILENAME = "research_progress.json"
SOURCES_LEDGER_FILENAME = "sources.jsonl"
CLAIMS_LEDGER_FILENAME = "claims.jsonl"
VERIFICATION_LEDGER_FILENAME = "verification.jsonl"

# ── Source / Claim Ledger ───────────────────────────────
ENABLE_SOURCE_REGISTRY = True
SOURCE_ID_PREFIX = "src"
SOURCE_SNIPPET_CHAR_LIMIT = 800
WEB_FETCH_INLINE_CHAR_LIMIT = 1200
WEB_FETCH_FULLTEXT_SAVE = True
SOURCE_LEDGER_ENABLED = True
CLAIM_LEDGER_ENABLED = True
VERIFIER_ENABLED = True
VERIFIER_AS_SUBAGENT = False  # V3.0: 用 Python orchestration 层调用

# ─── DeepSeek API 配置 ───────────────────────────────────
# DeepSeek 使用 OpenAI 兼容格式
# 优先级: 环境变量 > 项目根目录的 deepseek.txt

def _load_api_key() -> str:
    """加载 DeepSeek API key（优先环境变量，其次从文件读取）。"""
    key = os.getenv("DEEPSEEK_API_KEY", "")
    if key:
        return key
    # 尝试从项目根目录的 deepseek.txt 读取
    key_file = PROJECT_ROOT.parent / "deepseek.txt"
    if key_file.exists():
        return key_file.read_text(encoding="utf-8").strip()
    return ""

DEEPSEEK_API_KEY = _load_api_key()
DEEPSEEK_BASE_URL = "https://api.deepseek.com"

# 模型选择 —— 所有 agent 使用统一模型
# deepseek-v4-pro   → DeepSeek-V4 Pro，最新旗舰
# deepseek-v4-flash → DeepSeek-V4 Flash，轻量快速
AGENT_MODEL = "deepseek-v4-pro"

# API 调用参数
REQUEST_TIMEOUT = 300  # max 档单次调用可能更长
MAX_RETRIES = 5        # thinking 模式下偶发断连需更多重试

# ─── 搜索配置 ───────────────────────────────────────────
SEARCH_MAX_RESULTS = 10      # web_search 原始结果数（重排前多搜回）
FETCH_CHAR_LIMIT = 4000      # web_fetch 单页截断字符数
FETCH_TIMEOUT = 15           # web_fetch 请求超时（秒）

# ─── HuggingFace 镜像（国内加速）──────────────────
import os as _os
_os.environ.setdefault("HF_ENDPOINT", "https://hf-mirror.com")

# ─── 重排配置（检索质量提升最大的单点优化）──────────
RERANK_ENABLED = True
RERANK_MODEL = "BAAI/bge-reranker-v2-m3"  # 本地开源 cross-encoder
RERANK_TOP_K = 4                          # 重排后保留的最相关结果数

# ─── Agent 运行时配置 ────────────────────────────────────
RECURSION_LIMIT = 250        # LangGraph 循环步数上限（安全阀）
SUBAGENT_MAX_CONCURRENCY = 3 # 并行 researcher 最大数量

# ─── 报告配置 ───────────────────────────────────────────
REPORT_FILENAME = "report.md"
OUTPUT_DOCX_FILENAME = "report.docx"

# ─── 归档配置 ───────────────────────────────────────────
SUMMARIZE_MODEL = "deepseek-v4-pro"  # 分类+浓缩用的模型，可独立切换为更廉价的模型
VERIFIER_MODEL = "deepseek-v4-pro"   # 事实验证模型

# ─── 向量库 / RAG 配置 ───────────────────────────────────
# 将历史研究摘要向量化，存入本地 Chroma，供研究员检索历史积累
RAG_ENABLED = True
EMBEDDING_MODEL = "BAAI/bge-m3"                     # 本地嵌入模型（~1.2GB，与 reranker 同家族）
VECTOR_STORE_DIR = PROJECT_ROOT / "vector-store"      # 本地持久化目录（不随 workspace 清空）
VECTOR_COLLECTION = "research_history"
RAG_TOP_K = 3                                         # 每次检索返回的历史研究条数
# 注：BGE-M3(~1.2GB) + bge-reranker(~300MB) 同时加载约 1.5-2GB 内存

# ─── 推理深度控制 ───────────────────────────────────────
# DeepSeek V4 Pro 支持 reasoning_effort: "high" 或 "max"
# max 档: 思维链更长、agentic 任务更深; thinking 模式下 temperature 静默忽略
# 注意: Researcher 永远不要设 max——5 路并行 max reasoning 会触发限流/超时
REASONING_EFFORT_SUPERVISOR = "max"
REASONING_EFFORT_RESEARCHER = "high"
REASONING_EFFORT_CRITIC = "max"
THINKING_ENABLED = True
THINKING_MAX_OUTPUT_TOKENS = 16000

# ─── 研究员深度 ─────────────────────────────────────────
RESEARCHER_SEARCH_LIMIT = 20            # 代码层硬拦截，超过直接返回"预算用尽"
RESEARCHER_SUFFICIENCY_REQUIRED = True  # 必须自评充分性才能停
RESEARCH_TIMEOUT_MINUTES = 0            # 研究阶段时限（分钟），0=不限。fast模式设为5
COUNT_FAILED_SEARCHES = False           # 失败/空结果是否计入搜索预算。fast=True, deep/max=False

# ─── Critic 反思回路 ────────────────────────────────────
CRITIC_ENABLED = False                  # --enable-critic 开启
CRITIC_MAX_ROUNDS = 3  # 最多 3 轮反思→补研究→修订循环

# ─── HITL 计划审批 ──────────────────────────────────────
INTERACTIVE_PLAN_APPROVAL = False       # --interactive-plan 开启
PLAN_APPROVAL_MAX_REVISIONS = 3

# ─── RAG 混合检索 ───────────────────────────────────────
HYBRID_RETRIEVAL_ENABLED = True
HYBRID_RRF_K = 60
KB_CANDIDATE_K = 20                     # dense 召回候选数
KB_RERANK_ENABLED = True                # KB 路径加 cross-encoder 重排
KB_FINAL_TOP_K = 3

# ─── 上下文检索 ─────────────────────────────────────────
CONTEXTUAL_RETRIEVAL_ENABLED = True
CHUNK_MAX_CHARS = 1200                  # 单文档超此长度才切块，否则整篇当 chunk

# ─── 任务分配 ───────────────────────────────────────────
SUBAGENT_MAX_CONCURRENCY = 5            # 原 3，支持动态 1-5 个 researcher

# ─── 调试 ───────────────────────────────────────────────
DEBUG = False

# ─── 学术来源配置 ────────────────────────────────────────
# 免费、无需 API key 的开放学术 API，国内通常可达
ACADEMIC_MAILTO = ""            # 你的邮箱，填入后 OpenAlex/Crossref 响应更快更稳定
USE_OPENALEX = True             # 首选学术搜索（覆盖 2.4 亿+ 中外论文）
USE_CROSSREF = True             # DOI/期刊/作者等规范元数据
ARXIV_MIRROR = "xxx.itp.ac.cn"  # 中科院 arXiv 镜像，加速论文下载（空字符串则用原站）

# ── 国内来源 (DDGS site: 过滤器) ─────────────────────────
USE_CN_SEARCH = True            # 中文来源搜索工具
CN_SEARCH_MAX_RESULTS = 10      # 每次返回条数（重排前）
CN_SOURCES = {                  # 支持的中文站点
    "zhihu": "site:zhihu.com",          # 知乎: 技术讨论
    "baike": "site:baike.baidu.com",    # 百度百科: 事实定义
    "xueshu": "site:xueshu.baidu.com",  # 百度学术: 中文论文
}
