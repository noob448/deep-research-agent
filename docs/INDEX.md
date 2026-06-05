# 项目文档索引

## 核心参考

| 文档 | 用途 | 何时读 |
|------|------|--------|
| [../README.md](../README.md) | 项目简介、快速开始、CLI 速查 | 首次接触 |
| [../CLAUDE.md](../CLAUDE.md) | Claude Code 操作指引 | 用 Claude Code 开发时 |
| [../deep-research-agent/PROJECT_OVERVIEW.md](../deep-research-agent/PROJECT_OVERVIEW.md) | 全流程技术文档 | 需要了解完整架构时 |

## 规划与设计文档

| 文档 | 说明 | 状态 |
|------|------|------|
| [BUILD_GUIDE.md](BUILD_GUIDE.md) | 从零构建 deep research agent 的教学指南 | ✅ 已完成 |
| [SEARCH_QUALITY_PLAN.md](SEARCH_QUALITY_PLAN.md) | 搜索质量优化方案（重排、域名过滤、学术搜索） | ✅ 任务 2-4 已完成，任务 1/5 不适用 |
| [CN_ACADEMIC_SOURCES.md](CN_ACADEMIC_SOURCES.md) | 国内可用学术来源接入方案（OpenAlex/Crossref/秘塔） | ✅ OpenAlex + Crossref 已接入 |
| [RAG_KNOWLEDGE_BASE_PLAN.md](RAG_KNOWLEDGE_BASE_PLAN.md) | 本地向量化知识库实施方案 | ✅ 混合检索 + 上下文检索 + KB 重排已完成 |
| [IMPLEMENTATION_PLAN.md](IMPLEMENTATION_PLAN.md) | v1.0 全面改进方案（6 模块） | ✅ 全部 6 模块已实现 |

## 文件结构（整理后）

```
self-project-agent/
├── README.md              # 项目展示页
├── CLAUDE.md              # Claude Code 指引
├── .gitignore
├── deepseek.txt            # API Key (gitignored)
├── docs/                   # 规划文档
│   ├── INDEX.md            # 本文档
│   ├── BUILD_GUIDE.md
│   ├── SEARCH_QUALITY_PLAN.md
│   ├── CN_ACADEMIC_SOURCES.md
│   ├── RAG_KNOWLEDGE_BASE_PLAN.md
│   └── IMPLEMENTATION_PLAN.md
└── deep-research-agent/    # 主项目
    ├── PROJECT_OVERVIEW.md
    └── ...
```
