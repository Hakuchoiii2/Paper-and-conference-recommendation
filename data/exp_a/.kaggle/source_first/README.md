# V vs Source-first pilot50 — 25/10/2026

Private inference-only experiment authorized by the user: `htnkhi/exp-a-v-vs-source-first-pilot50`.

| Arm | Pipeline | Max new calls | Inherited calls/paper |
|---|---|---:|---:|
| R2a-V | Exact pinned V: cached raw draft, scoped validator and original full review | 2 | 1 |
| Source-first | Verbatim source inventory with roles/origin/context, final annotation, optional validator repair | 3 | 0 |

Both have at most 3 logical calls x2048 generated tokens per paper. Same model Qwen3-8B revision `b968826d9c46dd6066d109eabc6255188de91218`, NF4 double, greedy, pilot50 cohort, final schema, scoped validator, common named-dataset filter and frozen scorer/reference. No fine-tuning, adapter or semantic reviewer. Equal caps do not imply equal actual compute: inherited cost and new input/output tokens/seconds are reported separately.

The source inventory is structurally checked, not semantically certified. Final generation always receives all original sentences and may override planning roles or recover omitted ideas. An invalid inventory uses the second call for inventory retry and the third for extraction; it cannot then use an extra repair. Valid inventory permits extraction plus one validator repair. All raw attempts, source spans, origin/role/context suggestions, usage and errors are retained. A plan is not restricted to a single role; negative/null findings and prior-work limitations are permitted.

Pipeline fallback = unrecovered inventory errors OR annotation fallback. Annotation fallback and inventory-invalid count are reported separately. No claim that less fallback means better semantics. Empty inventories/outputs are observable but not automatically semantic errors. Final evidence still uses one sentence: cross-sentence caveat relations exist in the planning audit, but the old annotation schema cannot completely encode them.

This reuses the development cohort and imperfect AI reference; human review remains pending. No held-out semantic-accuracy or statistical-significance claim.

Design/ledger: [data/exp_a/docs plan](../../docs/2026-10-25-v-source-first-kaggle.md).

Build: `.venv-qwen/Scripts/python.exe -X utf8 -B data/exp_a/.kaggle/source_first/build.py`.
Tests: `.venv-qwen/Scripts/python.exe -X utf8 -B -m unittest discover -s scripts/exp_a/pilot -t . -q`.

Release `release_20261025_v1/` freezes source settings, original source/raw-draft hashes and five code assets. Build refuses to alter a release once `launch_report.json` exists. Code-only private kernel reuses the existing private frozen-input dataset; no source/reference re-upload. Kaggle outputs will be under `/kaggle/working/exp_a_v_source_first/results/`, including per-arm signed records, evaluations, `experiment_summary.json` and `experiment_table.md`. Reference content is opened only after both complete predictions are sealed.

## Launch verified

Version 1 is RUNNING on Kaggle. Cloud code bytes, private/GPU metadata and frozen release code hashes verified. [Launch report](release_20261025_v1/launch_report.json). Status does not yet confirm model worker startup or scores. Kaggle derived the final slug from the title; see requested/actual identities in launch report.
