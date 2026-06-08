# 推理模型蒸馏（2025年补充研究）

## 关键发现

### DeepSeek-R1-Distill系列
- 1.5B模型: AIME 28.9%, MATH 83.9%，超过GPT-4o和Claude-3.5-Sonnet
  source_ids: src_8b1a9b (DeepSeek-R1 arxiv论文)
- 系列包含7B/8B/14B/32B/70B
- MIT许可证，蒸馏版可在单张消费级GPU运行
  source_ids: src_46145b, src_e00d0e

### Qwen3系列
- 2025年4月29日发布，8种尺寸（600M到32B dense + MoE 235B）
- Qwen3-4B: 被distil labs独立评测为最佳微调基座模型
  source_ids: src_31548c, src_e3adfb, src_81b3a9
- 技术报告: arXiv 2505.09388

### GAPS
- 7B/8B/14B/32B/70B蒸馏版完整benchmark表未获取
- Qwen3各尺寸推理benchmark具体数值缺失
- 蒸馏推理保留率定量数据缺失
