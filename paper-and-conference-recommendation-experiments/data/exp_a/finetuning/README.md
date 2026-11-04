# Exp A QLoRA

Qwen3-8B adapter training on private Kaggle, followed by fresh base/adapter
predictions on the same100 held-out papers. Target split467/100/100, pilot50
excluded; GPT/Codex AI references with human review pending.

- `teacher/`: frozen corpus candidates, separate GPT drafts and independent
  source reviews, source-quality audit, then frozen additional references.
- `review.py`: validate review coverage/provenance, aggregate exact evidence,
  freeze whole reviewed papers after token/source checks.
- `prepare.py`: exact evidence-ID remapping, whole-paper validation, stratified
  70/15/15 split, tokenizer limits, leakage checks and frozen file hashes.
- `train.py`: NF4/FP16 QLoRA, assistant-only loss, best adapter by dev loss.
- `experiment.py`: train once, fresh base and adapter prediction workers, paired
  semantic evaluation with the unchanged threshold0.85.
- `bundle.py` and `kernel.template.py`: deterministic private Kaggle input bundle
  and bootstrap; `build/` stores the exact launched signature and settings.
- `collect.py`: verify downloaded outputs, recompute scores locally, stage only
  adapter/tokenizer/metadata for the reusable private adapter dataset.

Use `.venv-qwen/Scripts/python.exe -X utf8 -B`; pinned Transformers4.57.6 and
PEFT0.18.1. The corpus source papers and labels never come from student
predictions. Test references are separate from generator inputs.

Run status and design:
`scripts/exp_a/docs/QLORA_V1_PROGRESS_2026-10-16.md` and
`scripts/exp_a/docs/QLORA_V1_DESIGN_2026-10-16.md`.

Annotation-quality follow-up (2026-10-18):
[label_revision_v2/README.md](label_revision_v2/README.md) records the source-first
40-paper train/dev pilot and versioned multi-sentence evidence schema. These are
provisional AI references, separate from the frozen v1 split, adapter and scores.
