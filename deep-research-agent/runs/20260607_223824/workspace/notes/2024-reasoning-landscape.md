# 2024年大语言模型推理能力全景

## 主要模型及推理Benchmark成绩

### OpenAI o1-preview / o1-mini（2024年9月）
- AIME 2024: 74%（单次），64样本投票 83.3%
- GPQA Diamond: ~78%（超越人类PhD水平）
- Codeforces: 第89百分位
- MATH: ~94.8%
- 范式意义: 首个production级test-time compute scaling模型
  source_ids: src_5fb3ed, src_e6a1df

### GPT-4o（2024年5月）
- MMLU: 88.7
- GPQA Diamond: 53.6
- MATH: 76.6
- HumanEval: ~92
- MGSM: >85
  source_ids: src_059da0, src_accff4

### Claude 3.5 Sonnet（2024年6月）
- MMLU: 90.4%（当时最高）
- GPQA Diamond: 59.4%
- MATH: 71.1%
- HumanEval: 92.0%
- GSM8K: 96.4%
- BIG-Bench Hard: 93.1%
  source_ids: src_76adfd, src_4521ff, src_dc31b6, src_bb75ca

### Gemini 1.5 Pro（2024年2月）/ Flash（2024年5月）
- 具体benchmark分数未充分获取，100万token上下文窗口为独有优势
  source_ids: src_d1edd8

### DeepSeek-V3（2024年12月）
- MoE: 671B/37B激活，训练成本$5.576M
- AIME/MATH-500超越Qwen2.5 72B约10pp
- 技术报告: arXiv:2412.19437
  source_ids: src_6fe002, src_9ba5fa

### Llama 3（2024年4月）/ Llama 3.1 405B（2024年7月）
- Llama 3.1 405B: MMLU 88.6%, HumanEval 89.0%
- 首次开源达到闭源前沿竞争水平
  source_ids: src_fab11d, src_54444d, src_1c5961

### Qwen2（2024年6月）/ Qwen2.5（2024年9月）
- Qwen2.5-72B: MMLU 85.3%, MATH 83.1%, GSM8K 95.9%
- 1/5 Llama-3-405B参数实现可比性能
- 技术报告: arXiv:2412.15115
  source_ids: src_ebeac5, src_17ae96, src_e62b28

### Mistral Large 2（2024年7月）
- MMLU: 84.0%, HumanEval: 92%
- 123B参数，原生Tool Use
  source_ids: src_9bbe5e, src_0da89d

### Phi-4（2024年12月）
- 14B参数: MMLU 84.80，数学推理超越GPT-4o
  source_ids: src_10d6f9, src_547f46

## 2024年推理技术突破
- Test-Time Compute Scaling (o1, 2024/09)
- CoT演进: Coconut, Self-Reasoning RAG, CoT-RAG, AUTO-CEI
- Tool Use/Function Calling成为标准
- RAG与推理融合
- 开源模型推理能力追赶

## 推理能力短板
- 数学推理脆弱性（GSM-Symbolic发现）
- 知识基准饱和（MMLU/GSM8K）
- 幻觉与推理懒惰
- 模式匹配 vs 真正逻辑推理
- 推理成本高
- 多步推理错误传播
