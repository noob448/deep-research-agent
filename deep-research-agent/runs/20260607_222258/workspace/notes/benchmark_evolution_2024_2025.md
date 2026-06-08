# LLM推理基准测试体系演进 (2024-2025)

## 1. 传统基准饱和情况

### MMLU
- GPT-4 (2023): 86.4%
- Claude 3 Opus (2024): 88.7%
- Human expert average: ~89.8%
- Gemini Ultra (2024): 90.0%
- 到2024年中，前沿模型在MMLU上集中超过88%，几乎没有统计区分空间
- Stanford 2025 AI Index 确认MMLU、GSM8K等传统基准已饱和
- MMLU 现仅作为"sanity check"，不再是前沿模型主要区分指标
- source: src_9e9557, src_c7e33b, src_c98673, src_fab11d

### GSM8K
- 小学水平数学文字题，已基本被解决
- 作为快速验证仍有用，但已无法区分前沿模型
- source: src_9e9557, src_5ce53e

### MATH
- 被纳入MATH-500子集用于更高效评测
- DeepSeek-R1 在 MATH-500 上 pass@1 表现优异
- source: src_210e17

## 2. 2024-2025新基准

### MMLU-Pro
- MMLU的升级版，更难的题目设计
- 用于在MMLU饱和后继续区分模型能力
- source: src_9bbab8, src_c98673

### GPQA Diamond
- 研究生级别推理挑战（PhD-level science questions）
- 最难子集，对所有前沿模型仍具挑战性
- DeepSeek-R1和OpenAI o1/o3在此基准上有详细对比
- source: src_210e17, src_c98673, src_9bbab8

### AIME 2024
- 美国数学邀请赛题目，高难度数学推理
- DeepSeek-R1: pass@1从15.6%提升到71.0%（通过RL训练）
- 多数投票后达86.7%，匹配OpenAI-o1-0912
- source: src_210e17, src_23edc9

### Humanity's Last Exam (HLE)
- 2025年由CAIS和Scale AI合作发布，发表在Nature (2026年1月)
- 2,500道专家审核题目，来自近1,000位专家，覆盖500+机构，50个国家
- 领域分布：数学(41%)、物理(9%)、生物/医学(11%)等
- 已推出动态版本 HLE-Rolling
- source: src_1a0744, src_105251

### FrontierMath
- Epoch AI 创建，数百道未发表的专家级数学题
- 题目由数学家（含IMO金牌得主和Fields奖得主）贡献
- OpenAI o3 得分仅 25.2%，显示极高难度
- source: src_8f01be, src_8095c9, src_248573

### ARC-AGI
- ARC-AGI-1: 约5年未被突破，直到2024年12月OpenAI o3超越所有模型并匹配人类水平
- ARC-AGI-2 (2025): 更难的新版本，包含需要探索、规划和记忆管理的新题型
- GPT-5 Pro 在 ARC-AGI-1 Semi-Private 达70.2%
- source: src_c77d20, src_27fb33, src_228e88

### SWE-bench Verified
- SWE-bench的人类筛选500题子集，评估真实世界软件工程能力
- 每道题经人类工程师验证为可解
- 最广泛引用的编程基准之一
- source: src_3aa1e8, src_484388, src_ed7ffa

### LiveCodeBench
- 2024年推出，无污染编程评估
- 从LeetCode、AtCoder等平台收集新题目（2023年5月-2024年3月发布）
- 400+高质量编程题，持续更新
- source: src_c2a87e, src_cea1b0, src_74a5c2

## 3. 方法论变化

### 静态→动态评测
- 数据污染是核心驱动力：训练数据中包含基准题目导致分数虚高
- 论文 "Recent Advances in LLM Benchmarks against Data Contamination: From Static to Dynamic Evaluation" 系统分析了这一转变
- 动态基准如 LiveCodeBench、HLE-Rolling 通过持续引入新题目避免污染
- source: src_91222c, src_c02ad3, src_6c63ee

### 污染问题
- 当基准数据出现在模型训练数据中时产生数据污染
- 动态基准是最稳健的污染预防方法
- 2024-2025年是方法论转变的关键时期
- source: src_cd6fa2

## 4. 关键分数对比（待补全）
- DeepSeek-R1: AIME 2024 pass@1: 71.0%, MATH-500, GPQA Diamond
- OpenAI o3: FrontierMath 25.2%
- 需要更多具体分数数据
