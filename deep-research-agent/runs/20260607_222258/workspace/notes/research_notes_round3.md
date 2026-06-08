# Round 3 Research Notes

## RLVR (Reinforcement Learning with Verifiable Rewards) — from src_8ccc94, src_0c4bd4
- RLVR has become a core training method for reasoning models in 2025
- Uses objective, verifiable rewards (math answers, code execution results) rather than human preference labels
- Enables models to develop reasoning-like strategies through optimization on objective tasks
- Core to both DeepSeek-R1 and OpenAI o-series training
- Key difference from RLHF: rewards are automatically verifiable, not human-judged
- JustTinker: demonstrated RLVR can build reasoning models for under $150

## DeepSeek-R1 Training Pipeline (from earlier source src_909527)
Stage 1: Cold-start SFT — few thousand high-quality long CoT examples
Stage 2: GRPO training — reasoning-focused RL with group-based relative rewards
Stage 3: Rejection sampling + SFT — collect high-quality outputs, fine-tune
Stage 4: GRPO across all domains — final RL phase for general capability

GRPO innovation: eliminates need for separate critic/value model (unlike PPO)
- Compares outputs within a group for same prompt
- Reward = relative advantage within the group
- Much lower computational cost than PPO-style RL

## Key Unresolved:
- Exact details of OpenAI's o1 training methodology remain proprietary
- The arxiv paper 2501.02497 (System-1 to System-2) needs fetching
- DeepSeek-R1 paper details on exact GRPO reward formulation
- Kimi k1.5 paper (2501.12599) technical specifics
