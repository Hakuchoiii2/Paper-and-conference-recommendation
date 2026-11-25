# V-recall on accepted human gold400 — 26/10/2026

User requested private Kaggle execution and scoring of the current V-recall on all400 human_gold papers. Kernel: htnkhi/exp-a-v-recall-human-gold400. Input dataset: htnkhi/exp-a-v-recall-human-gold400-inputs (private).

Same frozen Qwen3-8B/NF4/greedy, original draft prompt, scoped V review, add-only task/method coverage and .85 embedding scorer as the current pilot V-recall. No adapter/training. The400 IDs do not overlap the cached pilot50, so every paper gets a fresh draft and both follow-up calls:3x2048 output-token ceiling. All3 logical calls are reported as fresh cost even when resuming a previously generated draft checkpoint from this same run.

Two T4 workers each take200 alternating IDs. Generation input contains only paper_id, title/abstract evidence options and model-produced annotation. Gold files remain evaluation-only, parsed only after all400 signed predictions have been loaded and hashed. All400 included, no removal of fallback or audit-noted cases.

Frozen code, source, accepted gold and model metadata are packaged in gold400_bundle.zip.bin. File allowlist/checksums and safe paths validated at unpack. Source/config identity is checked on draft resume. Final records check settings signature, source identity and three-call budget. Runtime/scorer/recall bytes copied from the immutable prior release; shared source files are unchanged.

Outputs: signed results/V-recall/records, raw drafts/attempt audits, prediction manifest, per-stage evaluation.json for Draft/V-review1/V-recall, coverage_addition_audit.json, experiment_summary.json, experiment_table.md. Intermediate stages reuse the same three calls. Main score reports human_gold hash, precision, recall, micro/macroF1, F2 and by-facet counts/metrics; scorer is approximate matching, not a new manual semantic-equivalence evaluation. Existing selection/development history remains in result limitations.

Build: .venv-qwen/Scripts/python.exe -X utf8 -B data/exp_a/.kaggle/v_recall_gold400/build.py
Test: .venv-qwen/Scripts/python.exe -X utf8 -B scripts/exp_a/pilot/test_v_recall_gold400.py -q

No historical split, label file, pilot release or kernel is overwritten. Uploaded releases are immutable.
