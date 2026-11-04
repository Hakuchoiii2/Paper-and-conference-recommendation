# Pilot50 V versus V-recall

Development cohort; AI reference; unchanged imperfect scorer. Matched/unmatched additions are not human semantic judgments. V-review1 is the intermediate output before coverage. Equal call caps, unequal actual costs.

| Arm | Precision | Recall | F2 | F1 | Pipeline fallback | New calls |
|---|---:|---:|---:|---:|---:|---:|
| R0 | 58.9674 | 53.9801 | 54.9089 | 56.3636 | 33 | None |
| R2a-V | 60.0000 | 53.7313 | 54.8780 | 56.6929 | 18 | 74 |
| V-review1 | 60.6648 | 54.4776 | 55.6120 | 57.4050 | 24 | None |
| V-recall | 58.2474 | 56.2189 | 56.6132 | 57.2152 | 34 | 100 |
