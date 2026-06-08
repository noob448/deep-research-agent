# Initial Search Results

## Models & Benchmarks
- o3/o4-mini System Card: April 16, 2025; advanced reasoning + tool integration
- o3-mini-high AIME: 87.3% vs DeepSeek R1: 79.8%
- Claude Sonnet 4.5: Sep 29, 2025; SWE-bench Verified 77.2%; 30-hour autonomous runs
- Claude Opus 4.5: Nov 24, 2025; outperforms Sonnet 4.5 on all benchmarks
- Gemini 2.5 Pro: Mar 25, 2025; AIME 2024/2025: 92.0%; GPQA leader; 18.8% HLE without tools
- Grok 3: Feb 17, 2025; claims to surpass o3-mini-high on AIME 2025 (controversy over @1 scores)
- Kimi K1.5: Jan 2025; matches/exceeds o1 and DeepSeek-R1; SOTA short-CoT; up to +550% on AIME etc.

## Paradigms
- Test-Time Compute (TTC) Scaling emerged as complementary paradigm in 2025
- DeepSeek-R1 (Jan 2025): pure RL → reasoning matching o1
- s1: Simple test-time scaling (arxiv 2501.19393)
- GRPO: Group Relative Policy Optimization - no explicit value network
