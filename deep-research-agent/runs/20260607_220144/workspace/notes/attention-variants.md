# 注意力机制关键变体

## 1. Sparse Attention（稀疏注意力）
- 核心思路：限制每个 query 只关注 key 的一个子集，而非全部
- 将 O(n²) 复杂度降低到 O(n·k)，k 为稀疏窗口大小
- 变体：滑动窗口（Sliding Window）、扩张窗口（Dilated）、全局+局部混合
- 代表：Longformer（滑动窗口+全局注意力）、BigBird（随机+窗口+全局）
- 新发现（2025）：高稀疏度的大模型在固定 FLOPs 下可超越稠密小模型
- 压缩比（逆稀疏度）在解码阶段可高于预填充阶段

## 2. Flash Attention
- 核心思路：IO-aware，通过 tiling 和 recomputation 减少 HBM 读写
- 不改变注意力计算的数学结果，纯粹是工程优化
- FlashAttention-1 (2022)：分块计算 + online softmax
- FlashAttention-2 (2023)：优化并行策略和工作分区
- FlashAttention-3 (2024)：针对 H100 GPU 进一步优化
- FlashInfer：扩展 FlashAttention 模板以支持稀疏注意力内核

## 3. Linear Attention（线性注意力）
- 将 softmax(QK^T) 替换为线性核函数 φ(Q)·φ(K)^T
- 利用矩阵乘法结合律将复杂度从 O(n²) 降至 O(n)
- 代表：Performer、Linear Transformer

## 4. Multi-Query Attention (MQA) / Grouped-Query Attention (GQA)
- MQA：所有 head 共享 K 和 V，仅 Q 保留多头（大幅减少 KV cache）
- GQA：将 head 分组，组内共享 K 和 V（在 MHA 和 MQA 之间折中）
- GQA 被 LLaMA 2、Gemini 等采用

## 关键趋势
- 从"计算全部注意力"→"选择性计算重要token的注意力"（稀疏化）
- 从"算法级优化"→"硬件感知优化"（Flash Attention 系列）
- 从"每个 head 独立 KV"→"共享 KV"（MQA/GQA，优化推理）

## 来源
- src_5c93ba: EmergentMind — Sparse Attention Variants Overview (2025)
- src_5f1e07: arXiv 2507.19595 — Efficient Attention Mechanisms Survey (2026)
- src_5acc79: arXiv 2512.07011 — Block Sparse Flash Attention
- src_ddd679: FlashInfer — MLSys 2025
