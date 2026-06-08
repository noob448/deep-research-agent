# 2024 LLM Reasoning Research Notes

## KB Background
- 2024 characterized by "training-time scaling" before shift to "inference-time scaling" (started with OpenAI o1, Sept 2024)
- MMLU and GSM8K became saturated, shifting to harder benchmarks
- OpenAI o1: first production-level test-time compute scaling with internal CoT

## Model Benchmark Scores (2024)

### GPT-4o (May 2024)
- MMLU: 88.7, GPQA: 53.6, MATH: 76.6, HumanEval: ~92
- source: community.openai.com, synscribe.com

### Claude 3.5 Sonnet (June 2024)
- MMLU: 90.4%, GPQA: 59.4%, MATH: 71.1%, HumanEval: 92.0%, GSM8K: 96.4%, BIG-Bench Hard: 93.1%
- source: anthropic.com/news/claude-3-5-sonnet (src_76adfd), galileo.ai, llm-stats.com

### Gemini 1.5 Pro (Feb 2024)
- Less specific data found. Need more.
- MMLU-Pro scores available on Artificial Analysis

### DeepSeek-V3 (Dec 2024)
- MMLU: ~88.5 (ties with Claude 3.5 Sonnet)
- On AIME, MATH-500, CNMO 2024: outperforms Qwen2.5 72B by ~10% absolute
- HumanEval: top-tier open-weight
- GSM8K: top-tier
- arXiv: 2412.19437 (src_6fe002)

### DeepSeek-V2 (May 2024)
- Need more data

### Llama 3.1 405B (July 2024)
- MMLU: 88.6% (Meta report), HumanEval: 89.0%
- source: huggingface, gentic.news

### Qwen2.5-72B (Sept 2024)
- MMLU: 85.3%, MATH: 83.1% (instruct) / 88.1% (math-instruct with TIR), GSM8K: 95.9% (math-instruct)
- Qwen2.5-72B base achieves comparable to Llama-3-405B with 1/5 params
- arXiv: 2412.15115 (src_ebeac5)
- Qwen2.5-7B MATH: 75.5% (instruct) vs Qwen2-7B: 52.9%

### Mistral Large 2 (July 2024)
- MMLU: 84.0% (5-shot), HumanEval: 92%
- 123B params, comparable to GPT-4o, Llama-3-405B on coding
- Supports tool use and function calling

### Phi-3 / Phi-4 (Apr/Dec 2024)
- Phi-4 (14B, Dec 2024): MMLU 84.80, beats GPT-4o on math
- Phi-3-mini: MMLU ~60% (but 10x faster than Llama 3 70B)

### OpenAI o1 (Sept 2024 - preview)
- First production-level test-time compute scaling
- Internal chain-of-thought for deep reasoning
- Started the "inference-time scaling" paradigm shift

## Benchmarks Mentioned
- MMLU, MMLU-Pro, MATH, GSM8K, HumanEval, GPQA (Diamond), ARC-Challenge, BIG-Bench Hard
- AIME, MATH-500, CNMO 2024
- MGSM, SimpleQA, DROP

## Tech Topics to Cover
- Chain-of-Thought improvements: Coconut (Continuous Thought, 2024)
- Self-Consistency: need search
- Constitutional AI: need search
- Tool Use/Function Calling: Mistral Large 2, Claude all support
- RAG + Reasoning: Self-Reasoning RAG (2024), CoT-RAG
- Prompt engineering: need search
