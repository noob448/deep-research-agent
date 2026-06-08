# Phi-4 & LLaMA 4 Findings

## Phi-4 Reasoning
- 14B parameter reasoning model, Microsoft, released April 30, 2025
- Trained via SFT on Phi-4 with reasoning demonstrations from o3-mini
- Variants: Phi-4-reasoning, Phi-4-reasoning-plus, Phi-4-mini-reasoning
- Designed to compete with o3-mini and DeepSeek in small model category
- Source: src_db4d5f, src_a5f99d, src_af3e5a, src_dd7ee1

## LLaMA 4
- Scout (17B active MoE) and Maverick (17B active, 128 experts MoE), released April 2025
- Behemoth announced as upcoming "highest performing base model"
- Maverick sits ahead of Claude 3.7 Sonnet on benchmarks
- 10M context window (Scout), runs on single H100
- Source: src_01f89b, src_64bc0a, src_da34fb, src_a1d13d
