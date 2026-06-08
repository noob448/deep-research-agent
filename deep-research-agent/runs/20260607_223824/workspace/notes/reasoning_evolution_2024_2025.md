# LLM推理技术路线演进 2024→2025 - 研究笔记

## 来自知识库 (KB, 0.731相关度)
- 核心转变：从"训练时扩展"→"推理时扩展"（test-time compute scaling）
- OpenAI o1 (2024/09): 首个production级test-time compute scaling，内部思维链深度思考
- DeepSeek-R1 (2025): GRPO算法，开源实现，成本仅o1的1/10-1/20
- OpenAI o3/o4-mini: AIME 2025近乎满分(99.5%)
- Claude Opus 4.5: SWE-bench Verified突破80%
- RLVR (可验证奖励的强化学习)成为推理训练核心方法论
- 思维链从外部prompt工程内化为RL训练自然产物
- 基准换代: MMLU/GSM8K饱和 → FrontierMath, Humanity's Last Exam, ARC-AGI-2
- 动态评测方法论兴起应对数据污染

## 来自web_search初步
- EngineersOfAI: "biggest shift in LLM capability 2024-2025 was not bigger training run" - paradigm shift from training-time to inference-time scaling
- kiankyars: pre-training scaling laws diminishing returns, test-time computation emerging as driver
- OpenReview survey: "Frontiers in LLM Reasoning: Inference Scaling"
- Medium: "Test-Time Compute breakthrough" of 2025
