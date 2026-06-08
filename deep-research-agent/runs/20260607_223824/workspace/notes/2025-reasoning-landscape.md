# 2025年大语言模型推理能力全景

## 关键模型

### OpenAI o3/o4-mini（2025年4月）
- o3: AIME 2025 ~99.5%, HLE 20.32%
- o3-mini-high: AIME 87.3%, 超越DeepSeek-R1的79.8%
- 首次将SOTA推理与完整工具使用整合
- System Card: openai.com/index/o3-o4-mini-system-card/
  source_ids: src_6ed0de, src_15528f, src_4c2c92, src_91ed92, src_cb8dc7

### DeepSeek-R1（2025年1月）
- 纯RL激发推理能力（无人类CoT示例）
- GRPO算法，Nature论文 (DOI: 10.1038/s41586-025-09422-z)
- 成本约o1的1/10-1/20，MIT协议开源
- MATH-500: 97.3%, AIME 2024: 79.8%
  source_ids: src_c2eb78, src_b5749f, src_2e2748, src_f77736

### Anthropic Claude系列（2025年）
- Claude Sonnet 4.5: SWE-bench 77.2%, extended thinking 64K tokens
- Claude Opus 4.5: SWE-bench 80%+
- Claude 3.7 Sonnet: GPQA/SWE-bench超越o3-mini
  source_ids: src_0569b8, src_f479bb, src_364224, src_a73548

### Gemini 2.5系列（2025年3月）
- Gemini 2.5 Pro: AIME 92.0%, HLE 18.8%
- "thinking model"，2M上下文
  source_ids: src_32ccb4, src_41c6c9, src_a1d763

### xAI Grok 3（2025年2月）
- 声称AIME 2025超越o3-mini-high（@1分数有争议）
  source_ids: src_40de16, src_382d4a

### Kimi K1.5（2025年1月）
- 中国首个o1级别开源推理模型
- AIME/MATH-500/LiveCodeBench超越GPT-4o和Claude 3.5 Sonnet
  source_ids: src_a3cd48, src_36be79

### Qwen3（2025年5月）
- reasoning/non-reasoning双模式
- Apache 2.0开源
  source_ids: src_d46d96, src_505f31

### Llama 4（2025年4月）
- Scout/Maverick发布，无技术论文
- 专用推理模型开发中
  source_ids: src_184ff4, src_1fd8ac

### MiniMax-01（2025年1月）
- Lightning Attention，4M上下文
- 开源
  source_ids: src_cf8225, src_78c497, src_3b506b

## 2025年新推理范式
1. Test-Time Compute Scaling
2. RLVR/GRPO成为推理训练核心
3. Thinking模型与推理时思考
4. 思维链从外部prompt内化为RL训练产物

## 代表性论文
1. DeepSeek-R1 (Nature, 2025)
2. o3/o4-mini System Card (OpenAI, 2025)
3. s1: Simple test-time scaling (arxiv 2501.19393)
4. The Art of Scaling Test-Time Compute (arxiv 2512.02008)
5. HLE (arxiv 2501.14249)
6. Toward Large Reasoning Models (Cell Patterns, 2025)
