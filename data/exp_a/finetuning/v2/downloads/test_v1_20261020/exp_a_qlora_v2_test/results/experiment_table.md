# QLoRA v2 paired test: 100 papers

Frozen existing AI references (pre-v2 label policy); human review pending.
Same v2.2 instruction, schema, greedy decoder and mandatory source-only review for both arms.
Failed papers remain in the denominator; grounded fallback concepts are scored and flagged.

| Arm | Micro F1 | Macro F1 | Precision | Recall | Fallback papers |
|---|---:|---:|---:|---:|---:|
| base | 26.52 | 29.71 | 45.87 | 18.66 | 96 |
| qlora_v2 | 47.02 | 49.54 | 51.89 | 42.99 | 15 |
