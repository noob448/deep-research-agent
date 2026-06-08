# Multi-Head Attention 结构

## 核心流程
1. Q = X @ W_Q, K = X @ W_K, V = X @ W_V  — 线性投影
2. split_into_heads(Q, K, V, num_heads) — 按维度均分拆分为多个 head
3. 每个 head 独立执行 Scaled Dot-Product Attention
4. concat_heads(Z_i) — 拼接所有 head 的输出
5. output = Z @ W_O — 最终线性投影

## 关键要点
- 拆分时按 embedding 维度均分（如 d_model=512, h=8 → head_dim=64）
- 每个 head 在低维子空间中独立计算注意力
- 拼接后通过 W_O 投影回原始维度
- Masking 在 softmax 之前、在每个 head 内独立执行

## 来源
- src_1f28b8: DataCamp tutorial
- src_508d3a: DigitalOcean tutorial  
- src_7d43de: GeeksforGeeks
