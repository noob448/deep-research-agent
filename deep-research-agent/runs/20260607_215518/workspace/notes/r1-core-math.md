# R1: Transformer注意力机制核心数学原理

## 核心发现

### 1. Scaled Dot-Product Attention 完整公式
Attention(Q, K, V) = softmax(QK^T / √d_k) V

计算流程：
- 步骤1: 计算 QK^T → 得到 n×m 的注意力分数矩阵（query数量×key数量）
- 步骤2: 除以 √d_k → 缩放（防止softmax饱和）
- 步骤3: softmax 按行归一化 → 得到注意力权重矩阵（每行和为1）
- 步骤4: 乘以 V → 输出为V的加权和

### 2. Q/K/V 定义与来源
- Q = XW_Q, K = XW_K, V = XW_V
- X 为输入嵌入矩阵
- W_Q, W_K, W_V 为可学习的权重矩阵
- Q/K/V 直觉：(1) "软字典查找"——Q发起查询，K提供索引，V存储值；(2) "可学习最近邻搜索"——通过相似度加权聚合

### 3. Softmax归一化
- softmax(z_i) = exp(z_i) / Σexp(z_j)
- 输出为概率分布（非负，和为1），语义上表示注意力权重
- 指数函数放大差异——大值主导输出

### 4. √d_k 缩放因子（关键洞察）
- 点积分量的分量方差≈1（假设q,k独立同分布，零均值单位方差）
- 点积方差=d_k（d_k个独立分量求和）
- 大d_k → 点积值大 → softmax输出趋近one-hot → 梯度趋零
- 除以√d_k → 点积方差归一化回1 → 梯度健康

### 5. 梯度稳定性
Softmax雅可比在饱和区（极端值）趋零，缩放因子确保输入落在softmax敏感区域。

### 6. 注意力权重矩阵
n×m矩阵，每个元素a_ij表示query_i对key_j的注意力程度，提供可解释性窗口。

## 来源
- src_mbrenn_mha: https://mbrenndoerfer.com/writing/multi-head-attention-transformers
- src_lilian_weng: https://lilianweng.github.io/posts/2018-06-24-attention/
- src_distill: https://distill.pub/2016/augmented-rnns/
- 原始论文: Vaswani et al., "Attention Is All You Need", NeurIPS 2017
