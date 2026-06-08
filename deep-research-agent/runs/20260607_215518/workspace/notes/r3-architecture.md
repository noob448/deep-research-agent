# R3: Transformer架构中注意力的整合

## 核心发现

### 1. Self-Attention vs Cross-Attention
**Self-Attention**: Q、K、V 全部来自同一序列
- Encoder: 无掩码，每个位置可见所有位置（双向）
- Decoder: 带因果掩码，每个位置只能看到自身及之前位置（单向自回归）

**Cross-Attention**: Q来自Decoder，K和V来自Encoder输出
- Encoder-Decoder之间的桥梁
- Decoder生成时查询源序列编码信息，实现跨序列信息融合

### 2. Sinusoidal Positional Encoding
- Self-Attention本身置换不变，需要位置编码注入顺序信息
- 公式: PE(pos,2i)=sin(pos/10000^(2i/d_model)); PE(pos,2i+1)=cos(pos/10000^(2i/d_model))
- 偶数维度用sin，奇数维度用cos
- 低频维度捕捉全局结构，高频维度捕捉局部差异
- 相对位置可线性表达：PE(pos+k) = PE(pos) 的线性变换
- 可外推到训练时未见过的更长序列

### 3. Pre-LN vs Post-LN
**Post-LN（原始方案）**: x → Sublayer(x) → x + Sublayer(x) → LayerNorm(·)
- 原论文6层可用，深层训练不稳定，需学习率预热

**Pre-LN（现代主流）**: x → LayerNorm(x) → Sublayer(LayerNorm(x)) → x + Sublayer(LayerNorm(x))
- 梯度稳定，无需预热，可训练数百层
- GPT/LLaMA等现代架构的事实标准

### 4. Encoder结构
- N层堆叠，每层: Self-Attention + FFN（各包裹残差+LN）
- Self-Attention无掩码，完全上下文感知
- 输出为等长上下文表示序列，作为Decoder Cross-Attention的K/V

### 5. Decoder结构
- N层堆叠，每层3个子层：
  (1) Masked Self-Attention → (2) Cross-Attention → (3) FFN
- Masked实现：上三角置-∞（softmax前），防止看到未来
- Cross-Attention以当前位置表示为Q，Encoder全部输出为K/V

### 6. 残差连接的三重作用
(1) 梯度高速公路——缓解梯度消失
(2) 恒等映射能力——即使子层无效，信息无损传播
(3) 使深层堆叠可行——无残差连接6层几乎无法训练

## 来源
- src_4ac98f: Self vs Cross Attention — teachme.sh
- src_61879c: Cross Attention Explained — aryanupadhyay.com
- src_e51952: Sinusoidal Position Encoding — mbrenndoerfer.com
- src_060f19: Pre-Norm vs Post-Norm — mbrenndoerfer.com
- src_3ab778: Encoder-Decoder Architecture — emergentmind.com
