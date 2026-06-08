# 2024 vs 2025 Benchmark对比

## Benchmark说明
| Benchmark | 考什么 | 指标 |
|---|---|---|
| MMLU | 57学科多选 | accuracy |
| MMLU-Pro | MMLU升级版 | accuracy |
| MATH | 竞赛数学 | accuracy |
| MATH-500 | MATH精选500题 | pass@1 |
| GSM8K | 小学数学应用题 | accuracy |
| GPQA Diamond | 研究生级科学推理 | accuracy |
| HumanEval | Python编程 | pass@1 |
| ARC-Challenge | 小学科学多选 | accuracy |
| ARC-AGI | 抽象视觉推理 | accuracy |
| BBH | 23个高难度BIG-Bench子任务 | accuracy |
| AIME 2024/2025 | 美国数学邀请赛 | pass@1 |
| SWE-bench Verified | GitHub软件工程issue | % resolved |
| LiveCodeBench | 实时编程题 | pass@1 |
| HLE | 跨学科极难题 | accuracy |

## 跨年对比表
| Benchmark | 2024最佳 | 2025最佳 | 提升 |
|---|---|---|---|
| MMLU | GPT-4o/Claude 3.5 Sonnet ~88.7% | GPT-5.2 ~91-92%; DeepSeek-R1 90.8% | +2-3pp |
| MMLU-Pro | GPT-4o ~72.6% | Claude Opus 4.6 ~82% | +6-11pp |
| MATH | GPT-4o ~76.6% | Claude Opus 4.5 ~99.2% | +22pp |
| MATH-500 | GPT-4o ~74.6% | DeepSeek-R1 97.3% | +23-24pp |
| GSM8K | GPT-4o ~96% | GPT-5.x ~99-100% (饱和) | +3-4pp |
| GPQA Diamond | GPT-4o ~49.9% | Claude Mythos 94.6% | **+40-45pp** |
| HumanEval | Claude 3.5 Sonnet 92% | GPT-5.3 Codex ~99-100% (饱和) | +8-10pp |
| ARC-Challenge | GPT-4o ~96% (饱和) | GPT-5 ~96.3% | +0-1pp |
| ARC-AGI | ~30-35% | GPT-5.2 54% (ARC-AGI-2) | +19-24pp |
| BBH | GPT-4o ~86-88% | GPT-5.x ~95%+ | +7-9pp |
| AIME 2024 | o1-preview ~56% | o3 83.3%; DeepSeek-R1 79.8% | **+31-75pp** |
| SWE-bench | GPT-4o ~33% | Claude Opus 4.5 80%+ | **+31-47pp** |
| LiveCodeBench | GPT-4o ~35-40% | Claude Sonnet 4.5 ~61 | +20-25pp |
| HLE | N/A (2024年无) | o3 20.32% | 新基准 |

## 关键洞察
- 提升最大 (>30pp): GPQA Diamond, AIME, SWE-bench
- 提升显著 (10-30pp): MATH/MATH-500, LiveCodeBench, MMLU-Pro, ARC-AGI
- 趋于饱和 (<10pp): MMLU, GSM8K, HumanEval, ARC-Challenge, BBH
- 2025新挑战: HLE (o3仅20.32%)

来源: llm-stats.com, RankSaga, Stanford HAI 2025 AI Index, DataCamp, Nature (DeepSeek-R1)
