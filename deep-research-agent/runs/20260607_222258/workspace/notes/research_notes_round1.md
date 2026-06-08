# Round 1 Research Notes

## Test-Time Compute Scaling (from src_e4c51a - Introl Blog)
- AI scaling paradigm shifted: now spending more compute at inference time rather than training larger models
- Core insight: letting models "think longer" through extended chain-of-thought produces reasoning capabilities training alone cannot achieve
- DeepSeek-R1 matched o1 by generating 10-100x more tokens per query
- ThreadWeaver: 1.5x latency reduction while matching accuracy (parallelizes reasoning)
- P1: first open-source model to win physics olympiad gold through RL + test-time agents
- Inference demand projected to exceed training demand by 118x by 2026
- Analysts project inference = 75% of total AI compute by 2030
- OpenAI's 2024 inference spend reached $2.3B — 15x the training cost for GPT-4.5
- Key open question: smaller distilled models stop improving past a certain thinking length; larger ones keep going

## DeepSeek-R1 GRPO (from src_909527 - Oxen AI)
- GRPO = Group Relative Policy Optimization, introduced in DeepSeekMath paper
- Full pipeline alternates between SFT and GRPO:
  1. Cold start SFT (few thousand high-quality CoT examples)
  2. GRPO training for reasoning
  3. Rejection sampling + SFT
  4. More GRPO across all domains
- GRPO eliminates the need for a separate value/critic model (unlike PPO)
- Uses group-based relative advantages: compares outputs within a group for the same prompt
- Key innovation: reward is based on relative comparison within group, reducing computational cost

## Key Connections
- DeepSeek-R1 matched o1 at 70% lower cost
- Both o1 and R1 leverage test-time compute (long CoT at inference)
- GRPO is the open-source counterpart to OpenAI's (proprietary) RL approach
