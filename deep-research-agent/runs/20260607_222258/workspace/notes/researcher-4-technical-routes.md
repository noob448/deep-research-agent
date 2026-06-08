# 推理技术路线深度对比（2024-2025）

## 一、推理时计算扩展（Test-Time Compute Scaling）

- 范式从"训练更大模型"转向"推理时投入更多计算" [src_e4c51a, src_7b99c8]
- o1率先展示，o3推理成本约$1000/任务（vs o1 $5/任务）[src_e4c51a]
- DeepSeek-R1生成10-100倍token，以低70%成本匹配o1 [src_f48967]
- OpenAI 2024年推理支出$23亿，是GPT-4.5训练成本15倍 [src_e4c51a]
- 关键限制：小蒸馏模型超过一定"思考长度"后性能停止提升 [src_b7c43d]

## 二、强化学习用于推理训练

- RLVR成为核心范式：使用可验证奖励（数学正确性、代码执行结果）替代人类偏好 [src_8ccc94, src_0c4bd4]
- GRPO（DeepSeek）：消除critic模型，组内相对比较降本 [src_909527, src_b5749f]
- 四阶段流水线：Cold-start SFT → GRPO推理 → 拒绝采样+SFT → 全领域GRPO [src_909527]
- R1-Zero实验：纯RL可增强推理，但基座质量决定上限 [src_18d56e]
- Kimi k1.5（arXiv:2501.12599）是另一条重要路线 [src_a3cd48]

## 三、Chain-of-Thought演变

- 三阶段：标准CoT → 长CoT（o1/R1, 10-100倍token）→ 隐式CoT（Coconut）[src_7deaa7, src_0e52ec]
- Coconut：在连续潜在空间推理，无需显式语言token [src_7deaa7, src_157097]
- 趋势：从显式结构化搜索→RL训练自主决定推理结构 [src_942cfe]

## 四、推理时搜索

- Beam Search, MCTS, A*搜索均被尝试 [src_78ad4f, src_942cfe]
- 核心挑战：LLM推理状态空间开放式，奖励结构不明确 [src_67c9dc]
- "Don't Get Lost in the Trees"(arXiv 2502.11183)提出战略性剪枝 [src_942cfe]

## 五、开源 vs 闭源

- DeepSeek-R1开源是分水岭事件 [src_f48967]
- 差距缩小但未消失，o3在最难基准上仍领先 [src_553e3b]
- 开源优势：社区快速迭代、成本效益 [src_f48967]

## 六、Scaling Law

- 训练时与推理时计算需最优分配 [src_6eb7b8]
- 新共识：预训练提供潜在能力 → RL训练激活引导 → 推理时计算扩展 [src_18d56e]
- "A Theory of Inference Compute Scaling"提供形式化框架 [src_133db2]

## 七、System 1 → System 2

- 从快速模式匹配（System 1）到深度分析推理（System 2）[src_7b99c8, src_7200c3]
- R1-Zero的"aha moment"是System 2涌现的关键证据 [src_18d56e]
