# Initial Findings - Open Source LLM Reasoning 2024-2025

## DeepSeek-R1
- 671B MoE parameters, released Jan 20, 2025, MIT license
- AIME 79.8% pass@1, MATH-500 97.3% — matches/exceeds OpenAI o1
- 130 days after o1-preview (Sept 12, 2024) → open-source parity gap compressing
- Technical innovation: RL training (GRPO), chain-of-thought reasoning visible to users
- Source: src_81f1c1, src_5c00a8, src_b69e1a

## Qwen3/QwQ-32B
- QwQ-32B: 32B parameters, released March 2025, performance matches DeepSeek-R1 (671B)
- Qwen3: dense (0.6B-32B) + MoE (30B, 235B) models, hybrid reasoning (thinking/non-thinking modes)
- Source: src_52c326, src_626b4f

## General Gap
- 2024-2025: open-source significantly narrowed performance gap with closed-source
- Claude 3.5 Sonnet and DeepSeek-V3 mentioned as parity examples
- Source: src_0ac7f2
