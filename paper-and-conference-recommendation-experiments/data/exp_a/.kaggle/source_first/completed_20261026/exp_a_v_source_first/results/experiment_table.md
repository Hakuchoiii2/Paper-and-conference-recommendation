# Pilot50: V versus Source-first

Development cohort; unchanged imperfect scorer; equal logical call/token caps, unequal actual costs. Pipeline fallback for Source-first includes invalid inventory; annotation fallback is reported separately.

| Arm | Micro F1 | Macro F1 | Pipeline fallback | Annotation fallback | Inventory invalid | New calls | Inherited calls |
|---|---:|---:|---:|---:|---:|---:|---:|
| R0 | 56.3636 | 56.8943 | 33 | 33 | None | 0 | 0 |
| R2a-V | 56.6929 | 56.5333 | 18 | 18 | None | 74 | 50 |
| Source-first | 50.0669 | 51.4551 | 43 | 22 | 41 | 146 | 0 |
