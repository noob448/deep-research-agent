# 注意力机制与位置编码的协同

## 为什么需要位置编码
- 注意力机制本身是**置换不变的**（permutation-invariant）——对序列顺序不敏感
- 没有位置编码时，"A 爱 B"和"B 爱 A"在注意力计算中完全相同
- 位置编码注入序列中的 token 位置信息

## 主要方案

### 1. 正弦位置编码（Sinusoidal PE）— 原始 Transformer
- 使用 sin/cos 函数生成固定编码，无需学习
- PE(pos, 2i) = sin(pos / 10000^(2i/d_model))
- PE(pos, 2i+1) = cos(pos / 10000^(2i/d_model))
- 优点：可外推到训练时未见过的序列长度（有理论支持）
- 缺点：外推能力有限，长序列上困惑度（perplexity）会退化

### 2. 可学习位置编码（Learned PE）
- 将位置编码作为可训练参数
- 优点：灵活性高，可适应特定任务
- 缺点：无法外推到超过训练时的序列长度

### 3. 相对位置编码（Relative PE / RoPE / ALiBi）
- 不编码绝对位置，而是编码 token 之间的相对距离
- ALiBi：在注意力分数上加一个线性偏置（不随序列长度退化）
- RoPE：通过旋转矩阵将相对位置注入 QK 内积

## 与注意力的配合方式
- **加法式**（Additive）：位置编码直接加到 token embedding 上，然后输入注意力层
- **偏置式**（Bias）：在注意力分数矩阵上添加位置偏置（如 ALiBi）
- **旋转式**（Rotary）：修改 QK 内积计算以注入相对位置（如 RoPE）

## 关键发现
- ALiBi 证明：位置编码是限制 Transformer 外推能力的主要瓶颈
- 可学习 PE 无外推能力；正弦 PE 和 RoPE 外推能力有限；ALiBi 外推能力最强
- 现代架构（如 LLaMA、GPT）普遍使用 RoPE

## 来源
- src_d5df20: arXiv 2406.08272 — 可学习 PE 依赖初始化
- src_1b700e: Medium/TDS — PE 方法进展综述（含 ALiBi/RoPE 对比）
- src_0a4b89: arXiv 2502.12370 — PE 在时间序列中的综述
