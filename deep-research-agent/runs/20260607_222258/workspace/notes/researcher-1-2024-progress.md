# 2024年LLM推理能力关键进展

## 一、重要模型发布

### OpenAI o1-preview / o1-mini（2024年9月12日）
- 首次展示 test-time compute scaling 范式——推理时"花更多时间思考" [src_a087be, src_9c7d88]
- o1-preview AIME 2024 约74%（GPT-4o仅13%），IMO资格赛83%，编程竞赛89th百分位 [src_c08868, src_a087be]
- o1-preview 基准: MMLU 90.8%, MATH 85.5%, HumanEval 92.4%, MGSM 90.8% [src_fb689f, src_c08868]
- o1-mini: MMLU 85.2%, HumanEval 92.4% [src_fb689f]
- 非多模态纯文本，128K上下文，知识截止2023年10月 [src_fb689f, src_979a30]

### Claude 3.5 Sonnet（2024年6月21日）
- GPQA/MMLU/HumanEval上树立新行业基准，超越Claude 3 Opus [src_76adfd]
- MATH 0-shot CoT 71.1 [src_c08868]
- 200K上下文，$3/M输入 + $15/M输出 [src_76adfd]

### DeepSeek-V3（2024年12月）
- 671B MoE架构，2.788M H800 GPU小时预训练 [src_9f4b57, src_5df717]
- 开源模型SOTA，数学和代码任务领先 [src_51be60]

### Gemini 1.5 Pro / Flash（2024年）
- 1M token上下文窗口 [src_ed7c3f]
- Flash在多个推理基准上表现优异 [src_88d09e]

### Llama 3.1 / Qwen2.5 / Mistral Large 2
- Llama 3.1 405B与GPT-4o、Claude 3.5竞争 [src_f303db]
- Qwen2.5-Coder HumanEval 92.7% [src_3f08d8]

## 二、推理技术创新

- CoT变体: Self-Consistency（提升10-15个百分点）、Tree-of-Thoughts、Graph-of-Thoughts [src_074bbc, src_49ef34]
- Search-Based CoT Optimization + Process Reward Models [src_b0c129]
- Scratchpad技术（o1核心组件）[src_a087be]
- 综述论文 "A Survey of Frontiers in LLM Reasoning" [src_5aa3b1]

## 三、范式转变
- 从 training-time scaling 到 inference-time/test-time compute scaling [src_0fd40d, src_a087be]
- 关键论文 "Scaling LLM Test-Time Compute Optimally can be More Effective than Scaling Model Parameters" [src_0fd40d]
