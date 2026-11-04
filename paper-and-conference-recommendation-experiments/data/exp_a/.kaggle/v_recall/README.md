# V recall-first pilot50 — 26/10/2026

Approved experiment: prioritize recall, with the existing ceiling of 3 logical calls x2048 output tokens. New private Kaggle kernel: `htnkhi/exp-a-v-recall-pilot50`.

| Arm | Calls |
|---|---|
| R2a-V control | Exact cached draft + up to two original V reviews |
| V-recall | Exact cached draft + first original V review + task/method additions only |

Both use the frozen Qwen3-8B revision, NF4, greedy decoding, identical pilot50 sources/drafts, scoped V validator, named-dataset filter and scorer/AI reference. No training or adapter. Old kernels and releases are unchanged.

The bounded original review uses its exact original seed and messages, verified by test. The coverage call inspects ALL source sentences, even those already cited; code permits only additions to task/method. Exact canonical duplicates are ignored; each addition passes the same source/validator checks independently. Invalid items are rejected without losing valid additions. Malformed/truncated coverage leaves the base intact. This validates source/form, not semantic role, novelty or exhaustive coverage. Semantic duplicates beyond canonical forms can remain.

`coverage_fallback` counts coverage parse/rejection failures; `annotation_fallback` counts final annotation validation failures. Pipeline fallback is their union. All raw attempts, accepted/rejected items, call seeds, prompt hashes and usage remain in signed records. Coverage does not repair remaining first-review errors and can therefore increase fallback compared with using both calls for repair.

Evaluation reports precision, recall, F1 and F2 (5TP/(5TP+4FN+FP)), overall and per facet. `V-review1` is the exact intermediate output before additions, not an extra model arm. Per-paper `coverage_addition_audit.json` reports TP/FP/FN deltas plus accepted labels matched/unmatched to the AI reference; these are not human judgments of truth. References are opened only after both complete prediction sets are loaded.

Build: `.venv-qwen/Scripts/python.exe -X utf8 -B data/exp_a/.kaggle/v_recall/build.py`.
Tests: `.venv-qwen/Scripts/python.exe -X utf8 -B -m unittest discover -s scripts/exp_a -t . -q`.

Release settings/code and input hashes are verified before workers run. Launch makes that release immutable. Private code-only kernel reuses `htnkhi/exp-a-base-v1-r1-r2-frozen-inputs`; no reupload of reference/source. GPU0 control; GPU1 recall. Actual calls/input/output tokens/time are reported separately; equal caps do not equal actual compute. Reused development cohort and imperfect AI reference; human review pending.

## Launch verified

Version 1 submitted, Kaggle RUNNING. Pulled cloud source is byte-identical to the release; private/GPU/frozen-dataset metadata verified. 252 A regression tests passed after allowing tokenizer metadata network access, 10 packaged behavior tests passed, reporting smoke passed, independent review found no blockers. No results or worker-start log confirmation yet. See release_20261026_v1/launch_report.json.

## Results checked 26/10/2026

Kaggle COMPLETE; 50 records/arm downloaded and 50 full pipeline replays passed (2,312 checks). Recall 53.73 -> 56.22%, F2 54.88 -> 56.61%, precision 60.00 -> 58.25%. Coverage alone adds 7 TP and 20 FP under the AI reference. See [review](completed_20261026/review_vi.md). No new run submitted.
