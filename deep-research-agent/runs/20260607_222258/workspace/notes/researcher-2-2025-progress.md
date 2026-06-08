# 2025年LLM推理能力关键进展

## 一、重要模型发布

### OpenAI o3 / o4-mini（2025年4月）
- o4-mini AIME 2025: 无工具92.7%, 带Python 99.5% [src_bbbd47, src_b45bcd]
- o3 AIME 2025: 带Python 98.4% [src_749908]
- GPQA Diamond: o3 83.3%, o4-mini 81.4% [src_b45bcd]
- o3 SWE-bench Verified 69.1%, HLE无工具20.32%/带工具24.9% [src_749908]
- o3比o1减少约20%重大错误 [src_1cce41]

### DeepSeek-R1（2025年1月）
- 核心创新: GRPO（Group Relative Policy Optimization），无需critic模型 [src_909527, src_c2eb78]
- 训练流程: SFT冷启动 → GRPO RL → 推理数据生成 → 蒸馏至小模型(1.5B-70B) [src_64e64e]
- R1-Zero: 纯RL训练，自然涌现"aha moment"自我修正 [src_18d56e]
- 发表于Nature (2025) [src_b5749f]
- API: $0.70/M输入, $2.50/M输出（o1的1/10-1/20）[src_970d8b]

### Claude 4 / Opus 4.5（2025年5月/11月）
- Claude Opus 4.5: SWE-bench Verified 80.9%，首个突破80% [src_a631ac]
- "可能是现存最好的编程模型" [src_6b43bd]

### Gemini 2.5 Pro（2025年）
- GPQA Diamond 84%（科学推理领先）[src_e50d5d]
- AIME 2025首次尝试86.7% [src_0eeebb]
- HLE无工具最高18.8% [src_4e6bd6]
- LMArena领先约40分 [src_e50d5d]

### Grok-3（2025年2月）
- "Think mode"（6秒-6分钟深度推理）[src_51439d]
- AIME 2025 93.3%, GPQA Diamond 84.6% [src_1217a8]
- Grok 4于2025年7月跟进 [src_40de16]

### Qwen3（2025年4月）
- 32B参数，Apache 2.0许可，同级别效率领先 [src_df3041]
- Qwen3.6 Plus GPQA Diamond 90.4% [src_30e751]

### Llama 4（2025年4月）
- Maverick 17B-128E, 402B MoE [src_01f89b]
- 基准被操纵争议：LeCun离职后承认结果被操纵 [src_e97cea]

## 二、推理技术创新

- Test-time compute scaling成熟：sequential/parallel/hybrid三维分配 [src_77dd7f, src_232227]
- ATLAS: Agentic Test-time Learning-to-Allocate Scaling [src_21d505]
- GRPO/RLVR成为RL推理训练核心方法论 [src_842722]
- CoT演化为训练内生能力，不再依赖外部提示 [src_c2eb78, src_3c5700]
- 推理时搜索与蒸馏互补 [src_64e64e]

## 三、生产化转变
- API成本大幅下降（DeepSeek-R1为o1的1/10-1/20）[src_970d8b]
- Gemini 2.5 Flash低至$0.30/M输入 [src_29bb6a]
- 蒸馏模型使推理能力部署到小规模环境 [src_64e64e]
