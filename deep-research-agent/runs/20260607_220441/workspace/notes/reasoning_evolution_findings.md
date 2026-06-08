# LLM Reasoning Evolution 2024-2025: Key Findings

## 1. Technology Evolution Timeline

### Phase 1: CoT Prompting (2022-baseline)
- Chain-of-Thought prompting established as standard approach
- Single-pass reasoning with explicit intermediate steps

### Phase 2: Long CoT & Structured Reasoning (2024 H1)
- Tree-of-Thought (ToT), Graph-of-Thought extend reasoning structure
- Forest-of-Thought: scaling test-time compute via tree search

### Phase 3: Test-Time Compute Scaling (2024 Q3-Q4)
- Key paper: "Scaling LLM Test-Time Compute Optimally can be More Effective than Scaling Model Parameters" (Snell et al., arxiv 2408.03314, Aug 2024)
- Two mechanisms: (1) search against PRM verifier, (2) adaptive distribution update
- "Compute-optimal" strategy: 4x efficiency gain over best-of-N
- Tradeoff: sequential (revisions) vs parallel (best-of-N) depends on difficulty & budget
- "Inference Scaling Laws" paper (Oct 2024): empirical analysis of compute-optimal inference

### Phase 4: RL for Reasoning (2024 Q4 - 2025)
- OpenAI o1 (Sept 2024): first "reasoning model" with test-time scaling laws
- OpenAI o3 (Dec 2024): major jump - AIME 2024: 96.7% (vs o1 83.3%)
- DeepSeek R1 (Jan 2025, arXiv:2501.12948): GRPO (Group Relative Policy Optimization)
  - Pure RL incentivizing reasoning without human-annotated demonstrations
  - Multi-stage training: RL + SFT + distillation
  - AIME 2024: 79.8%, slightly ahead of o1-1217 (79.2%)
- RL for LRMs as new paradigm shift from prompt engineering

### Phase 5: Search/Agentic Reasoning (2025+)
- MCTS, beam search integrated into reasoning
- Agentic workflows with tool use during reasoning

## 2. Test-Time Compute Methods

- **Best-of-N**: Generate N samples, pick best via verifier (parallel)
- **Beam Search**: Maintain top-k candidates across reasoning steps
- **Self-Consistency**: Majority voting across multiple reasoning paths
- **PRM (Process Reward Model)**: Step-level reward scoring
- **ORM (Outcome Reward Model)**: Final answer quality scoring
- **MCTS (Monte Carlo Tree Search)**: Tree exploration with value function guidance
- **Sequential Refinement**: Model revises own outputs iteratively

## 3. Source IDs Collected

- src_5c672e: Raschka "State of LLM Reasoning Model Inference" - comprehensive overview
- src_a32b6f: "Towards Large Reasoning Models: A Survey" (arxiv 2501.09686)
- src_dd44e7: "Scaling LLM Test-Time Compute Optimally" (arxiv 2408.03314)
- src_c2eb78: DeepSeek-R1 Nature paper (GRPO approach)
- src_4e9ee4: DeepSeek R1 GRPO multi-stage training explanation
- src_abb4f0: Test-time compute scaling overview with ORM/PRM comparison
- src_f271f1: OpenAI competitive programming with o1/o3 (arxiv 2502.06807)
- src_b38a71: Survey of Frontiers in LLM Reasoning (OpenReview)
- src_563277: o1 Technical Primer (Alignment Forum)

## 4. Benchmark Data Points

### AIME 2024:
- o1-preview (Sept 2024): 83.3%
- o1-1217 (Dec 2024): 79.2%
- o3 (Dec 2024): 96.7%
- DeepSeek R1 (Jan 2025): 79.8%

### GPQA Diamond:
- o3: 83.0%
- Need more data points

### MATH-500:
- DeepSeek R1 strong performance (need exact score)
