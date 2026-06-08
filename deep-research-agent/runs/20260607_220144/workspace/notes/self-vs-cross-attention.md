# Self-Attention vs Cross-Attention

## Self-Attention（自注意力）
- Q、K、V 来自**同一序列**
- 让序列内部相互关注，捕获序列内 token 之间的关系
- 用途：Encoder 的每一层 + Decoder 的 masked self-attention 层
- 公式：Q=K=V 来自同一输入 X，经不同投影矩阵 (W_Q, W_K, W_V)

## Cross-Attention（交叉注意力）
- Q 来自一个序列（解码器），K 和 V 来自**另一个序列**（编码器）
- 让一个序列"关注"另一个序列中的相关信息
- 用途：Transformer Decoder 中连接 encoder 输出的层
- 公式：Q = Decoder输出 @ W_Q, K = Encoder输出 @ W_K, V = Encoder输出 @ W_V

## 核心区别
| 维度 | Self-Attention | Cross-Attention |
|------|---------------|-----------------|
| Q来源 | 当前序列 | 当前序列（Decoder） |
| K来源 | 同一序列 | 另一序列（Encoder） |
| V来源 | 同一序列 | 另一序列（Encoder） |
| 目的 | 序列内关系 | 序列间对齐 |

## 来源
- src_bf537c: AI Adda visual guide
- src_0332d5: AIML.com
- src_8a2d5c: GeeksforGeeks
- src_61879c: Aryan Upadhyay
