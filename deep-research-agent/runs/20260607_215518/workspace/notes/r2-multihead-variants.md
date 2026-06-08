# R2: 多头注意力与变体

## 核心发现

### 1. Multi-Head Attention (MHA) 设计原理
**h 个并行注意力头 + 独立投影矩阵**
- 每个头拥有独立学习的投影矩阵 W^Q_i、W^K_i、W^V_i
- 各头在维度 d_k = d_model / h 的子空间中操作
- 拼接所有头输出: Concat(head_1, ..., head_h)
- 通过 W^O ∈ R^(hd_v × d_model) 融合信息

**不同头捕捉不同关系的直觉**
- 语言中存在多种同时发生的关系（句法、语义、指代）
- 不同头自然专业化：有的侧重句法依赖，有的关注共指消解，有的捕捉长距离语义关联
- 这是MHA"联合关注不同位置不同表示子空间"的核心优势

### 2. Multi-Query Attention (MQA)
- Shazeer, 2019 提出
- 所有头共享同一组 K 和 V，Q 仍各自独立
- KV Cache 缩减 h 倍（如h=8→缩减8倍）
- 动机：缓解LLM推理阶段KV Cache的显存/带宽瓶颈
- Google PaLM 采用
- 代价：表达能力下降，可能训练不稳定

### 3. Grouped-Query Attention (GQA)
- Ainslie et al., 2023 (EMNLP)
- h 个查询头分成 G 个组（1 < G < h），组内共享K/V
- G=1 → MQA；G=h → MHA；中间值可控权衡
- 质量接近MHA，推理速度接近MQA
- 可从MHA checkpoint通过mean pooling初始化（uptraining）
- Llama 2 (70B)、Llama 3、Mistral 均采用GQA

### 4. Flash Attention
- Dao et al., 2022 (NeurIPS)，精确注意力（非近似）
- 核心：IO-Aware——减少HBM与SRAM之间的数据搬运
- Tiling（分块）：SRAM中逐块计算softmax累积，避免完整N×N中间矩阵写入HBM
- Kernel Fusion：融合多个CUDA kernel为单个，减少launch开销
- HBM读写从O(N²)降至O(N)，2-4倍加速
- FlashAttention-2 (2023)、FlashAttention-3 (2024，Hopper优化)

## 来源
- src_cba76c: Multi-Head Attention blog — mbrenndoerfer.com
- src_2fdb2e: GQA — IBM Think
- src_d066b4: MQA & GQA — Tinkerd
- src_c68df5: FlashAttention — DigitalOcean tutorial
- src_686fad: FlashAttention paper — arXiv:2205.14135
- src_9ef7fd: MHA/MQA/GQA对比 — 知乎
- 原始论文: Vaswani et al. 2017; Shazeer 2019; Ainslie et al. 2023; Dao et al. 2022
