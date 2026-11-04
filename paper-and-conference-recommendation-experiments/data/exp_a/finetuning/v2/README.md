# Exp A v2 — training complete

Verified 2026-10-19: Kaggle `htnkhi/exp-a-qwen-qlora-v2` is COMPLETE. Output settings/signature match the original version 1 release. Training completed 3 epochs / 177 steps on 467 train + 100 dev papers.

| Epoch | Dev loss |
|---:|---:|
| 1 | 0.09211858 |
| 2 | **0.08514727** |
| 3 | 0.08884508 |

The final adapter matches `checkpoint-118` (epoch 2), selected by lowest dev loss. All 10 adapter files pass SHA-256 checks; all 504 LoRA tensors are finite. Adapter and evidence: `downloads/training_v1_20261019/`. Result summary and checks: `build/training_result_summary_2026-10-19.json`, `build/training_result_checks_2026-10-19.json`. Full report: `scripts/exp_a/docs/QLORA_V2_TRAINING_RESULT_2026-10-19.md` from the project root.

This was training only: dev loss was evaluated, but no generation/F1 evaluation was run. AI references / human review pending: 98 independently reviewed, 469 source-authored unreviewed. Low loss alone does not establish generation quality.

38 protected v1 artifacts remain unchanged. Test source/reference content was not opened for this collection. Automation remains PAUSED; no further GPU run or publication was started. Original launch history remains in `build/training_launch_report.json`; `build/push_report.json` is the earlier diagnostic launch.

## Paired test complete — verified 2026-10-20

Kaggle `htnkhi/exp-a-qwen-qlora-v2-test`: COMPLETE. 100 frozen test papers, same v2.2 instruction and greedy decoder with mandatory source-only review. Micro F1: base 26.52 → v2 47.02; macro F1: 29.71 → 49.54; fallback papers: 96 → 15. Problem F1 decreases 31.76 → 28.57; other four facets improve. Selected validator-valid papers: base 4/100, v2 85/100. Failed papers remain in the denominator and grounded fallback concepts are scored.

Output settings match the sealed release and launch signature. 222 local checks PASS: complete record sets, record hashes/pairing, counts and recalculated Micro F1. Existing pre-v2 AI references are unchanged; human review remains pending, so these are agreement scores rather than human-gold validation.

Evidence: `downloads/test_v1_20261020/`, `build/test_result_checks_2026-10-20.json`. Report: `scripts/exp_a/docs/QLORA_V2_TEST_RESULT_2026-10-20.md` from project root. No additional GPU run, publication or automation change.

## Base v1/v2 replay comparison — 2026-10-20

Same 100 sources, reference hash and Qwen3-8B revision. Historical base Micro F1: v1 47.44, v2 26.52. Replaying both selected raw outputs through the same v2 grounding: 44.98 versus 26.52. Raw unvalidated agreement: 47.07 versus 32.19 (diagnostic only). All four historical TP/FP/FN totals reproduced; 400 input record hashes unchanged. No new generation. See `scripts/exp_a/docs/BASE_V1_V2_COMPARISON_2026-10-20.md` from project root, and `build/base_comparison_common_gate_20261020/`.
