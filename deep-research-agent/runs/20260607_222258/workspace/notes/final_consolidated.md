# Final Consolidated Research Notes

## 1. Test-Time Compute Scaling (o1 → o3)

### Core Insight
The AI scaling paradigm shifted in 2024-2025 from "train bigger models" to "spend more compute at inference time." Models think longer through extended CoT, producing reasoning capabilities training alone cannot achieve.

### Key Evidence
- OpenAI's o1 (2024) demonstrated test-time compute scaling: more inference compute → better reasoning
- o3 cost ~$1000/task vs o1-preview $5/task — 200x cost for state-of-the-art reasoning
- DeepSeek-R1 matched o1 by generating 10-100x more tokens per query, at 70% lower cost (src_e4c51a)
- OpenAI's 2024 inference spend: $2.3B, 15x GPT-4.5 training cost (src_e4c51a)
- Inference projected to exceed training demand by 118x by 2026; 75% of total AI compute by 2030 (src_e4c51a)
- Open question: smaller distilled models plateau in thinking length; larger models keep improving (src_e4c51a)

### Technical Papers
- "Test-time Computing: from System-1 Thinking to System-2 Thinking" — arXiv 2501.02497 (src_7b99c8)
- ThreadWeaver: 1.5x latency reduction via parallelized reasoning (src_e4c51a)
- P1: first open-source model to win physics olympiad gold through RL + test-time agents (src_e4c51a)

## 2. RL for Reasoning Training

### OpenAI's Approach (Proprietary)
- RLVR (Reinforcement Learning with Verifiable Rewards) — core training method (src_8ccc94, src_0c4bd4)
- Uses objective, verifiable rewards (math answers, code execution) rather than human preference labels
- Exact o1 training methodology remains proprietary
- RLVR enables models to develop reasoning strategies through optimization on objective tasks

### DeepSeek-R1: GRPO (Group Relative Policy Optimization)
- Published in Nature (src_b5749f, DOI: 10.1038/s41586-025-09422-z)
- GRPO first introduced in DeepSeekMath paper; core to R1 post-training
- Four-stage pipeline (src_909527):
  1. Cold-start SFT: few thousand high-quality long CoT examples
  2. GRPO training: reasoning-focused RL
  3. Rejection sampling + SFT
  4. Final GRPO across all domains
- GRPO eliminates need for separate critic/value model (unlike PPO)
- Group-based relative advantages: compare outputs within group for same prompt
- Reward = relative comparison → much lower computational cost

### R1-Zero: Pure RL without SFT
- DeepSeek-R1-Zero showed RL at scale can directly enhance reasoning WITHOUT supervised fine-tuning (src_18d56e)
- Critical finding: DeepSeek-V3-Base already exhibited "Aha moment" (self-correction during reasoning), while Qwen base models did not
- This suggests pretraining quality matters enormously for RL reasoning emergence (src_18d56e)
- Paper: "Understanding R1-Zero-Like Training: A Critical Perspective" (arXiv 2503.20783)

### Kimi k1.5
- Moonshot AI, arXiv:2501.12599 (Jan 22, 2025)
- "Scaling Reinforcement Learning with LLMs"
- Described as one of "China's Reasoning Model Twin Stars" alongside DeepSeek-R1 (src_0feaa8)
- Free web version at Kimi.ai (Jan 2025) (src_a3cd48)

### JustTinker
- Demonstrated RLVR can build reasoning models for under $150 (src_6a1ce2)

## 3. Chain-of-Thought Evolution

### Explicit CoT → Long CoT
- Standard CoT: models generate intermediate reasoning steps in natural language
- Long CoT (o1/R1 style): models generate 10-100x more tokens of reasoning
- Core trade-off: more tokens → better reasoning but higher latency and cost

### Latent/Implicit CoT — Coconut
- "Chain of Continuous Thought": reasoning in continuous latent space rather than discrete tokens (src_7deaa7, src_0e52ec)
- Uses model's last embedding layer latent representations
- Advantages: more efficient, no need to verbalize intermediate steps
- Trade-off: less interpretable but potentially faster
- Building on earlier work like "Training Large Language Models to Reason in a Continuous Latent Space" (src_157097, arXiv 2412.06769)

### Structured Reasoning Variants
- Tree-of-Thought (ToT): explicit branching of reasoning paths
- Graph-of-Thought: more complex dependency structures
- The field is moving from linear CoT → branching/search-based CoT → latent CoT

## 4. Inference-Time Search Techniques

### Tree Search Methods Applied to LLM Reasoning
- Beam Search (Yao et al., 2024; Zhu et al., 2024; Yu et al., 2024)
- MCTS — Monte Carlo Tree Search (Tian et al., 2024; Zhang et al., 2024)
- A* search (Wang et al., 2024b) (src_942cfe)

### Key Survey
- TMLR 2025 survey: comprehensive framework of LLM inference via search (src_78ad4f)
- GitHub: xinzhel/LLM-Search

### Critical Limitation
- LLMs struggle to replicate AlphaGo's tree search success (src_67c9dc)
- Reasons: different reward structure, open-ended state space (vs. finite Go board), verification difficulty
- MCTS four-phase loop (selection, expansion, simulation, backpropagation) doesn't map cleanly to text generation

### Key Paper
- "Don't Get Lost in the Trees: Streamlining LLM Reasoning by..." (arXiv 2502.11183) — argues for pruning search trees strategically (src_942cfe)

## 5. Open-Source vs Closed-Source Gap

### DeepSeek-R1 as Watershed Moment
- R1 open-sourced at 671B parameters with performance "comparable to OpenAI o1 across math, code, and reasoning tasks" (src_f48967)
- Achieved this at fraction of the cost — 70% lower operational cost than o1 (src_e4c51a)
- "Profound effect on AI ecosystem" — developers building on R1 within days of release (src_67f445)
- DeepSeek R2 announced: 92.7% AIME, 32B open-weight, using R1 as teacher model (src_b7c43d)

### Gap Dynamics
- Gap narrowed significantly in early 2025 with DeepSeek-R1 release
- But o3 still holds frontier on hardest reasoning benchmarks (AIME 2024: o3 scored significantly higher)
- o3 cost ($1000/task) creates practical gap — open-source more cost-effective for most use cases
- Distillation matters: DeepSeek-R1-Distill models bring reasoning to smaller, more deployable sizes
- R1-Zero finding: pretraining quality is the bottleneck for RL reasoning — not just RL technique

## 6. Reasoning Scaling Laws

### Key Debate: Training vs Inference
- Epoch AI analysis: "Optimally allocating compute between inference and training" (src_6eb7b8)
- Compute-optimal scaling laws now include inference tokens as a component (src_133db2)
- Key finding: allocate compute toward generating solutions ~1.5-2x faster than verifications (src_fa9ba2)
- Inference scaling laws for GenRM (Generative Reward Models): formal blueprint for compute-optimal problem solving

### The "Both Are Needed" Consensus
- Smaller distilled models plateau → larger base models + RL needed for continued improvement
- DeepSeek-V3-Base already had "Aha moment" before RL → pretraining matters
- But RL is what unlocks and amplifies latent reasoning ability
- Emerging view: pretraining scale provides latent reasoning capability; RL + test-time compute activate and extend it

## 7. System 1 → System 2 Paradigm Shift

### Framework
- System 1: fast, instinctive, pattern-based (standard LLM autoregressive generation)
- System 2: slow, analytical, deliberate (o1/R1-type reasoning with extended CoT)
- Kahneman's dual-process theory from cognitive psychology provides the metaphor

### The Shift
- Pre-2024: LLMs operated primarily as System 1 — generate next token based on learned patterns
- 2024-2025: o1, R1, k1.5 demonstrate System 2 — deliberate multi-step reasoning with self-verification
- Test-time compute is the mechanism that enables System 2 behavior
- "Aha moment" observed in R1-Zero: models spontaneously learn to self-correct and re-evaluate during RL training

### Key Reference
- "Test-time Computing: from System-1 Thinking to System-2 Thinking" (arXiv 2501.02497) (src_7b99c8)
