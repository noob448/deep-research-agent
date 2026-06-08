# Self-Attention vs Cross-Attention (Search 1)

## Key Sources Found
- src_daed07: AST Consulting - Self vs Cross attention overview
- src_4ac98f: TeachMe.sh - Clear visual explanation of self vs cross attention
- src_7ed716: Wikipedia - Comprehensive Transformer architecture article (covers encoder/decoder layers, attention sublayers)
- src_61879c: Aryan Upadhyay blog - Cross attention explained (Mar 2026)

## Key Findings
- Cross-attention is the bridge between encoder and decoder; decoder queries the encoder's output (one-way flow)
- Decoder has TWO attention sublayers: (1) masked self-attention, (2) cross-attention
- Encoder has pure (unmasked) self-attention
- Cross-attention: Q from decoder, K and V from encoder output
