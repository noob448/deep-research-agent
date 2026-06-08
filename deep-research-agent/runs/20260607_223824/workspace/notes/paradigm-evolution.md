# 2024→2025推理技术路线演进

## 范式转变（质变）

### 1. 推理时扩展取代训练时扩展
- 2024年9月o1开创，2025年全面爆发
- 从"更大的模型"到"让模型更会思考"
- 来源: EngineersOfAI, KB

### 2. RL取代SFT成为推理训练核心
- DeepSeek-R1-Zero: 纯RL可涌现推理行为
- RLVR/GRPO: 可验证奖励替代人工标注
- 来源: Nature (DeepSeek-R1), 知乎技术分析

### 3. 思维链从外部注入到内部涌现
- 2024: CoT prompting是用户技巧
- 2025: thinking tokens是RL训练的自然产物
- 来源: OpenReview (thinking tokens MI分析), KB

### 4. 开源追赶闭源
- 2024: o1系列闭源垄断
- 2025: DeepSeek-R1 MIT开源，性能可比o1
- Open-R1项目推动推理民主化

## 量变（同一范式内的加速）
- 推理成本骤降: o1 $60/1M → DeepSeek-R1 $2.50/1M → o3-mini $4.40/1M
- 蒸馏技术成熟
- 多领域泛化: GURU项目覆盖Math/Code/Science/Logic/Simulation/Tabular

## 争议与讨论
1. 推理能力的真实泛化 vs Benchmark过拟合
   - o3 AIME 99.5% 但 FrontierMath 25.2%、HLE 20.32%
2. Benchmark饱和与评测危机
   - MMLU/GSM8K退居二线，新一代基准快速迭代
3. RL真的在激励推理吗？
   - 当前RLVR限于单轮响应，迭代式反思仍是瓶颈
   - 论文: "Does Reinforcement Learning Really Incentivize Reasoning" (arxiv 2504.13837)
4. Thinking Tokens的不可解释性
   - "Hmm", "Wait"代表什么认知过程？
   - 互信息分析提供信息论洞察但语义解释不足

## 未来趋势
1. Latent Reasoning（隐式推理）: ICLR 2026论文，在潜在空间推理
2. Thinking Environment重设计: 结构化迭代改进
3. 多领域统一推理: GURU等项目
4. DRTO框架: 增强推理鲁棒性
5. 推理成本持续快速下降
6. 通用推理仍有漫长道路: HLE 20.32%

## 关键来源
- src_83b9c8: EngineersOfAI reasoning models overview
- src_021593: Survey of Slow Thinking-based Reasoning LLMs (arxiv 2505.02665)
- src_41a085: DeepSeek R1 analysis (UNU)
- src_60a67e: Does RL Really Incentivize Reasoning (arxiv 2504.13837)
- src_e947e8: Thinking Tokens are Information Peaks (OpenReview)
- src_29c0a8: Reinforced Latent Reasoning (ICLR 2026)
- src_dc7cef: DeepSeek-R1 GRPO解读 (知乎)
- src_927516: DeepSeek-R1-Zero技术详解 (知乎)
- src_b5749f: DeepSeek-R1 Nature论文 (DOI: 10.1038/s41586-025-09422-z)
