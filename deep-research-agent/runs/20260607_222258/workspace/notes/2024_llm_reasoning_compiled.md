# 2024 LLM Reasoning - Compiled Research Notes

## OpenAI o1 Series (September 12, 2024)

### o1-preview
- Released: September 12, 2024
- Context window: 128K input tokens, 32.8K max output
- Pricing: $15/M input, $60/M output tokens
- MMLU: 90.8% (pass@1)
- MATH (0-shot CoT): 85.5% — source: src_fb689f, src_c08868
- HumanEval: 92.4% — source: src_fb689f
- MGSM: 90.8%
- IMO qualifying exam: 83% — source: src_c08868
- Competitive programming: 89th percentile — source: src_c08868
- GPT-4o was at ~13% on AIME 2024; o1 averaged ~74% (from other known benchmarks)

### o1-mini
- Released: September 12, 2024
- Context window: 128K input, 65.5K max output
- MMLU: 85.2% (zero-shot CoT) — source: src_fb689f
- HumanEval: 92.4% — source: src_fb689f

## Claude 3.5 Sonnet (June 21, 2024)
- Sets new industry benchmarks for GPQA (graduate-level reasoning), MMLU, HumanEval — source: src_76adfd
- 200K token context window
- Pricing: $3/M input, $15/M output
- 2x speed of Claude 3 Opus
- MATH (0-shot CoT): 71.1 (second-best after o1-preview among non-reasoning models) — source: src_c08868

## Test-Time Compute Scaling (o1 paradigm shift)
- OpenAI's o1 (September 2024) was the first publicly available model demonstrating test-time compute scaling at production quality — source: src_a087be
- Key concept: spend more computation at inference time to improve answer quality, rather than just scaling model parameters
- "Scaling LLM Test-Time Compute Optimally can be More Effective than Scaling Model Parameters" (2024 paper) — source: src_0fd40d
- Paradigm shift from "training-time scaling" to "inference-time scaling" — source: src_a087be, src_9c7d88

## Reasoning Techniques (2024)
- Chain-of-Thought (CoT): foundation technique, observable reasoning traces
- Self-Consistency: improved accuracy by 10-15 percentage points over single-sample CoT
- Tree-of-Thoughts (ToT): branching reasoning paths
- Graph-of-Thoughts (GoT): models reasoning as graph of thought nodes with dependencies
- Search-Based CoT Optimization: systematically explores multiple reasoning trajectories
- Process Reward Models (PRMs): used in o1-style reasoning
- Comprehensive survey: "A Survey of Frontiers in LLM Reasoning" — source: src_5aa3b1

## Still Missing / Need to Fill
- DeepSeek-V2/V3 specific benchmark scores
- Qwen2.5 specific benchmark scores
- Llama 3.1 405B specific benchmark scores
- Mistral Large 2 specific benchmark scores
- Gemini 1.5 Pro/Flash specific benchmark scores
- BBH, ARC-Challenge specific scores
- Specific 2024 reasoning technique papers with concrete results
