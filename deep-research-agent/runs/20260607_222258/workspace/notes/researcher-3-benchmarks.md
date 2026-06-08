# 推理基准测试体系演进（2024-2025）

## 一、传统基准饱和

- MMLU 2024年实质饱和，前沿模型88-90%，超过人类专家~89.8% [src_c7e33b, src_9e9557]
- GPT-4(2023) 86.4% → Claude 3 Opus(2024) 88.7% → Gemini Ultra(2024) 90.0% [src_fab11d]
- GSM8K被基本"解决" [src_5ce53e]
- MMLU现仅作"sanity check" [src_9e9557]

## 二、新基准推出

### MMLU-Pro
- MMLU升级版，更难题目区分前沿模型 [src_9bbab8]
- DeepSeek-R1 84.0%（原MMLU 90.8%）[src_457855]

### GPQA Diamond
- 博士级科学推理，前沿模型仍有挑战 [src_210e17]
- DeepSeek-R1 71.5% [src_457855]

### AIME 2024
- 美国数学邀请赛题，DeepSeek-R1 pass@1从15.6%→71.0%（RL训练后）[src_23edc9]

### Humanity's Last Exam (HLE)
- 2025年CAIS/Scale AI发布，发表于Nature [src_1a0744]
- 2500题，近1000位专家贡献 [src_105251]
- HLE-Rolling动态版本防污染 [src_1a0744]

### FrontierMath
- Epoch AI，350道研究级数学题，IMO金牌/Fields奖得主贡献 [src_8f01be]
- o3仅25.2%，极高难度 [src_8095c9]

### ARC-AGI
- ARC-AGI-1约5年未被突破，o3匹配人类水平 [src_c77d20]
- ARC-AGI-2（2025年发布），GPT-5 Pro 70.2%, Gemini 3 Deep Think 84.6% [src_27fb33, src_ef400f]

### SWE-bench Verified
- 500题真实软件工程任务，从~30%快速提升至80%+ [src_484388, src_3aa1e8]

### LiveCodeBench
- 2024年推出，动态爬取新题防污染 [src_c2a87e, src_cea1b0]

## 三、关键模型分数对比

| 模型 | MMLU | MMLU-Pro | GPQA Diamond | AIME 2024 | FrontierMath |
|------|------|----------|-------------|-----------|-------------|
| GPT-4 (2023) | 86.4% | - | - | - | - |
| Claude 3 Opus (2024) | 88.7% | - | - | - | - |
| Gemini Ultra (2024) | 90.0% | - | - | - | - |
| DeepSeek-R1 (2025) | 90.8% | 84.0% | 71.5% | 71.0% | - |
| OpenAI o3 (2024.12) | - | - | - | - | 25.2% |

## 四、方法论变化
- 静态→动态评测转变（防数据污染）[src_91222c, src_6c63ee]
- 三大趋势：难度提升、能力维度细分、防污染设计 [src_9bbab8, src_8f01be, src_1a0744]
