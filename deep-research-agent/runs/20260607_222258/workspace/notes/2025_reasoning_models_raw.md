# 2025 推理模型研究笔记 - 原始数据

## OpenAI o3 / o4-mini (2025年4月发布)
- o3: AIME 2025 得分 98.4%（带Python工具）, GPQA Diamond 83.3, HLE 20.32（无工具）/ 24.9（带工具）, SWE-Bench Verified 69.1%, MMMU 82.9%
- o4-mini: AIME 2025 得分 92.7%（不带工具）/ 99.5%（带Python）, GPQA Diamond 81.4
- o3 比 o1 在困难任务上少 20% 重大错误
- Source: OpenAI官方博客 (src_1cce41), AnalyticsVidhya (src_bbbd47), Beebom (src_b45bcd)

## DeepSeek-R1 (2025年1月发布)
- 使用 GRPO (Group Relative Policy Optimization) 强化学习训练
- 纯RL无需人类标注即可激励推理能力
- 发表在 Nature (src_c2eb78)
- Source: ghost.oxen.ai (src_909527), Nature (src_c2eb78)

## Claude 4 (2025年5月发布)
- Anthropic 在2025年5月发布 Claude 4，包含 Claude Opus 4 和 Sonnet 4
- Claude Opus 4.5 (2025年11月): 可能是最好的编程模型
- Sonnet 4.5 提供 extended thinking toggle
- Source: thepromptbuddy (src_6b43bd), varunsharma (src_fc89c4)

## 学术综述 (src_dbc21d)
- ICT Express 2025 综述: test-time compute scaling, RL, SFT, distillation 等技术应用于 DeepSeek-R1, o1, o3, GPT-4o, Qwen-32B, Llama variants
