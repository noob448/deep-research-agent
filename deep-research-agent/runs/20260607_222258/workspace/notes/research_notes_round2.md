# Round 2 Research Notes

## System 1 → System 2 Thinking (from src_7200c3, src_20a599, src_7b99c8)
- System 1 = fast, instinctive, pattern-based (standard LLM autoregressive generation)
- System 2 = slow, analytical, deliberate (o1-type reasoning with extended CoT)
- o1 model (OpenAI 2024) incorporates System-2 thinking via test-time computing scaling
- The arxiv paper "Test-time Computing: from System-1 Thinking to System-2 Thinking" (2501.02497) provides theoretical framework
- Key insight: test-time compute scaling is the mechanism that enables System 2 behavior in LLMs
- Reasoning models are explicitly "System 2" — slow, analytical, meticulous

## Reasoning Scaling Laws (from src_6eb7b8, src_133db2, src_fa9ba2)
- Epoch AI blog: "Optimally allocating compute between inference and training"
- Compute-optimal scaling laws now include inference tokens as a component
- Key finding: allocate compute towards generating solutions faster than verifications (~1.5-2x faster)
- "A Theory of Inference Compute Scaling: Reasoning through Directed Stochastic Skill Search" — formal theory paper
- Crossover point between one-time training cost and linear inference growth determines optimal strategy
- Smaller distilled models plateau in thinking length; larger models continue improving

## Latent/Implicit CoT — Coconut (from src_157097, src_7deaa7, src_0e52ec)
- Coconut = "Chain of Continuous Thought" — reasoning in latent space rather than explicit language tokens
- Uses model's last embedding layer latent representations instead of discrete token output
- Key advantage: more efficient, no need to verbalize intermediate steps in natural language
- Trade-off: less interpretable but potentially faster and more compute-efficient
- Represents evolution beyond explicit CoT toward more efficient reasoning paradigms

## MCTS / Search for LLM Reasoning (from src_942cfe, src_78ad4f, src_67c9dc)
- Advanced tree search algorithms applied to LLM reasoning:
  - Beam Search (Yao et al., 2024; Zhu et al., 2024)
  - MCTS (Tian et al., 2024; Zhang et al., 2024)
  - A* search (Wang et al., 2024b)
- TMLR 2025 survey: comprehensive framework of LLM inference via search
- Key limitation: LLMs struggle with tree search unlike AlphaGo — due to different reward structures and state space nature
- Tree-of-Thought (ToT) was an early influential framework, but search-based methods have evolved significantly

## Kimi k1.5 (from src_4f182f, src_a3cd48, src_0feaa8)
- Moonshot AI's reasoning model, arXiv:2501.12599 (Jan 22, 2025)
- "Kimi K1.5: Scaling Reinforcement Learning with LLMs"
- Described alongside DeepSeek-R1 as "China's Reasoning Model Twin Stars"
- Available as free web version at Kimi.ai (Jan 2025)
