# Deep Research Agent

基于 LangChain `deepagents` 框架的多智能体深度研究系统。输入一个课题，自动制定计划、并行搜索、交叉验证、撰写报告、浓缩归档。

## 工作原理

```
用户课题 → Supervisor 规划 → 3 个 Researcher 并行搜索
          ├── DuckDuckGo (通用网络)
          ├── OpenAlex (学术论文, 2.4亿篇)
          ├── Crossref (学术元数据/DOI)
          └── 本地向量知识库 (BGE-M3 + Chroma)

         → 重排精排 → 交叉验证 → 分节撰写报告
         → Summarizer 分类浓缩 → 自动增量索引归档
```

- **Supervisor**：编排规划、分配任务、质量把关，**不直接搜索**
- **Researcher × 3**：各自拥有独立上下文，8-15 次搜索预算，OODA 循环
- **Critic**（可选）：独立审查报告质量，输出结构化缺陷清单
- **RAG 知识库**：每次研究的浓缩摘要自动向量化入库，后续研究可检索历史积累

## 快速开始

### 1. 安装依赖

```bash
git clone git@github.com:noob448/deep-research-agent.git
cd deep-research-agent
pip install -r requirements.txt
```

### 2. 配置 API Key

在项目根目录创建 `deepseek.txt` 写入你的 API Key：

```
sk-your-deepseek-api-key
```

或者设置环境变量 `DEEPSEEK_API_KEY`。

> 使用 DeepSeek V4 Pro（OpenAI 兼容接口），也可在 `deep_research/config.py` 中切换其他兼容模型。

### 3. 运行测试

```bash
python run_test.py "什么是AI Agent?"
```

首次运行会自动下载 BGE-M3 嵌入模型（~1.2GB）和 BGE reranker（~300MB），之后缓存。预计 5-10 分钟完成，产出 `workspace/report.md` 和 `workspace/report.docx`。

### 4. CLI 选项

```bash
# 基础用法
python run_test.py "课题"

# 全速推理（Supervisor/Researcher/Critic 全部 max）
python run_test.py "课题" --long-thinking

# 省 token 模式
python run_test.py "课题" --short-thinking

# 深度模式：推理拉满 + 反思回路 + 人工审批
python run_test.py "课题" --long-thinking --enable-critic --interactive-plan

# 调宽搜索预算 + 并发数
python run_test.py "复杂课题" --max-searches 20 --max-researchers 5

# 调试 RAG
python run_test.py "课题" --no-hybrid-kb --debug
python run_test.py "课题" --no-rerank-kb
python run_test.py "课题" --no-contextual-rag

# 重建向量库（老 schema → 新 schema 迁移）
python build_index.py --rebuild

# 查看所有选项
python run_test.py --help
```

## 项目结构

```
deep-research-agent/
├── run_test.py              # 主入口（流式输出 + 归档 + 增量索引）
├── build_index.py           # 一次性建库脚本（--rebuild 重建）
├── deep_research/           # 核心包（~1800 行）
│   ├── config.py            # 集中配置
│   ├── tools.py             # 5 个搜索工具
│   ├── prompts.py           # Supervisor + Researcher 提示词
│   ├── agent.py             # Agent 组装工厂
│   ├── subagents.py         # Researcher + Critic 子智能体
│   ├── rerank.py            # 检索重排 (Cross-Encoder)
│   ├── knowledge_base.py    # 向量知识库 (BGE-M3 + Chroma)
│   ├── summarizer.py        # 分类决策 + 内容浓缩
│   ├── report.py            # Markdown → .docx
│   └── skills/              # 渐进式披露 Skills
└── workspace/               # 运行时产出（自动清空）
```

## 许可证

MIT
