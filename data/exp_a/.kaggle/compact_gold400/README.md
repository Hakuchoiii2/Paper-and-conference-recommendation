# Compact extraction and targeted patch — gold400

User approved private Kaggle execution on 2026-10-27 after the completed V-recall investigation. Separate kernel `htnkhi/exp-a-compact-patch-human-gold400` reuses existing private inputs `htnkhi/exp-a-v-recall-human-gold400-inputs`. Only new code, prompt and aggregate baseline metadata are uploaded. The generated local input bundle is offline-preflight-only and must not be uploaded.

Same frozen 400 accepted human gold papers, Qwen3-8B exact revision, NF4, greedy generation, original embedding matcher at .85. New compact source prompt separates independent task/method names. A fresh draft receives up to two indexed repairs of flagged items; unflagged items are protected. No broad coverage additions. Malformed/truncated full annotations receive source-only schema recovery. Invalid/truncated patches preserve the previous annotation. Actual call count is1–3 per paper, each capped at2048 output tokens.

Every completed draft/repair has a signed checkpoint keyed to source, prompt, config, messages and seed. Same-run checkpoint costs count once; resuming does not regenerate those calls. All400 final signed predictions must exist and be hashed before evaluation gold is parsed. All400, including fallback cases, remain in scoring. Draft/final scores and frozen observed prior stages appear in experiment_table.md; cost differences are explicit.

This is exploratory development on inspected AI-assisted human gold, not a new independent holdout. No training or adapters. New quality improvement remains unmeasured until cloud scoring completes.

Build: `python -B data/exp_a/.kaggle/compact_gold400/build.py`

Tests: `python -B scripts/exp_a/pilot/test_compact_gold400.py -q`

Review: two blockers fixed with regression tests (truncated patch routing; checkpointed repair resume). Independent recheck found no remaining launch blockers.

Uploaded releases are immutable. Original V-recall releases and unrelated working files remain untouched.
