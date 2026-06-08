# 2025 推理模型研究笔记 - 最终整理

## 一、2025年重要推理模型发布

### OpenAI o3 / o4-mini（2025年4月）
- o3: AIME 2025 98.4%（带Python）, GPQA Diamond 83.3%, HLE 20.32%（无工具）/24.9%（带工具）, SWE-bench 69.1%, MMMU 82.9%
- o4-mini: AIME 2025 92.7%（不带工具）/ 99.5%（带Python）, GPQA Diamond 81.4, 小型高效推理模型
- 比 o1 在困难任务上减少 20% 重大错误
- 来源: src_1cce41, src_bbbd47, src_b45bcd, src_749908

### DeepSeek-R1（2025年1月）
- 使用 GRPO (Group Relative Policy Optimization) 强化学习训练
- 核心发现：纯 RL 无需人类标注即可激励 Chain-of-Thought 推理能力
- 训练流程：SFT冷启动 → GRPO RL → 推理数据生成 → 蒸馏到小模型
- 开源 + 低成本 API ($0.70/M input, $2.50/M output)
- 发表在 Nature (2025)
- R1-Zero: 跳过冷启动SFT，纯RL训练，展现"aha moment"涌现
- 来源: src_c2eb78 (Nature), src_909527 (GRPO详解), src_b5749f (OpenAlex), src_64e64e (GitHub), src_970d8b (OpenRouter)

### Claude 4（2025年5月，Anthropic）
- Claude Opus 4 + Sonnet 4，2025年5月发布
- Opus 4.5 (2025年11月): SWE-bench Verified 80.9%（首个突破80%），"可能是最好的编程模型"
- Sonnet 4.5: extended thinking toggle，部分编程基准超越Opus
- 来源: src_6b43bd, src_fc89c4, src_a631ac

### Gemini 2.5 Pro / Flash（2025年，Google）
- Gemini 2.5 Pro: GPQA Diamond 84%, AIME 2025 86.7%, HLE 18.8%（无工具模型第一）
- LMArena 领先约40分
- Gemini 2.5 Flash: $0.30/M input, $2.50/M output, 1M context window
- 来源: src_4e6bd6, src_e50d5d, src_0eeebb, src_29bb6a

### Qwen3（2025年4月，阿里云）
- Qwen3 32B: 2025年4月28日发布，Apache 2.0 开源
- 30B级别效率领先，重新定义该参数级别的性价比
- 来源: src_df3041, src_fa3013

### Llama 4（2025年4月，Meta）
- Llama-4-Maverick-17B-128E（402B MoE），2025年4月发布
- 争议：Yann LeCun 离职后承认基准测试结果被操纵（被调优以提升基准分数）
- 在长上下文任务上表现不佳
- 来源: src_e97cea, src_a7a516, src_01f89b

### Grok-3（2025年2月，xAI）
- AIME 2025: 93.3%, GPQA Diamond: 84.6%
- "Think mode" 深度推理，6秒到6分钟
- Grok 4 (2025年7月): GPQA Diamond 领先
- 来源: src_51439d, src_1217a8, src_40de16

## 二、2025年推理技术创新

### Test-Time Compute Scaling 成熟化
- 核心理念：将推理时的计算预算分配到 sequential/parallel/hybrid 维度
- 包括 self-correction, budget-controlled decoding, self-consistency aggregation, tree search
- OpenAI o1/o3 系列的核心技术基础
- ATLAS (Agentic Test-time Learning-to-Allocate Scaling): 2025年代理式测试时计算分配
- 来源: src_77dd7f, src_232227, src_21d505, src_3c5700

### GRPO / RLVR (强化学习用于推理训练)
- GRPO (Group Relative Policy Optimization): DeepSeek 提出，替代传统 critic 模型
- 使用组内相对归一化计算策略优势
- SFT + GRPO 交替训练流水线
- R1-Zero 证明：纯 RL 无需 SFT 冷启动也能激励推理
- RLVR: 使用可验证奖励（数学答案正确/错误）进行 RL
- 来源: src_909527, src_c2eb78, src_18d56e, src_842722

### Chain-of-Thought 优化
- 长链推理（数千 token）成为标准
- "Aha moment" 在 RL 训练中自然涌现
- 推理token 透明度提升（DeepSeek-R1 完全开放推理token）
- 来源: src_3c5700, src_c2eb78

### 推理时搜索
- 与 test-time compute scaling 结合
- O3 使用创新的 test-time search 实现高性能推理
- Tree search / beam search 在推理阶段的部署
- 来源: src_3c5700, src_21d505

## 三、2025年关键推理基准分数

### AIME 2025 (数学竞赛)
- o4-mini: 99.5% (带Python) / 92.7% (不带工具)
- o3: 98.4% (带Python)
- Grok-3: 93.3%
- Gemini 2.5 Pro: 86.7%

### GPQA Diamond (研究生级科学推理)
- Grok-3: 84.6%
- Gemini 2.5 Pro: 84%
- o3: 83.3%
- o4-mini: 81.4%

### HLE (Humanity's Last Exam)
- o3: 20.32% (无工具) / 24.9% (带工具)
- Gemini 2.5 Pro: 18.8% (无工具模型最高)

### SWE-bench Verified (软件工程)
- Claude Opus 4.5: 80.9% (首个突破80%)
- o3: 69.1%

### MMLU-Pro / MMMU
- o3 MMMU: 82.9%

### ARC-AGI
- ARC-AGI-2 于2025年发布，挑战 test-time reasoning
- o3-preview 在 ARC-AGI-1 上展示了突破
- 来源: src_c4c6fb

### LiveCodeBench
- 覆盖代码生成的动态基准（持续更新至2025年）
- 来源: src_eb8534

## 四、从演示到生产的转变

### 成本降低
- DeepSeek-R1: $0.70/M input, $2.50/M output（显著低于o1）
- Gemini 2.5 Flash: $0.30/M input, $2.50/M output
- 开源模型（DeepSeek-R1, Qwen3）允许本地部署，零API成本

### 速度提升
- o4-mini 针对速度和成本优化
- Gemini 2.5 Flash 作为"工作马"模型
- 小模型蒸馏（DeepSeek-R1 蒸馏到 1.5B-70B 密集模型）

### API化
- 所有主要推理模型均已API化
- OpenRouter 等聚合平台提供统一接口
- 开源推理模型的权重和推理token完全开放
- 来源: src_970d8b, src_29bb6a, src_64e64e
