# Verification — experiment folder layout, 2026-10-05

Latest timing probe: see [GENERATOR_TIMING.md](GENERATOR_TIMING.md). Three real
Qwen papers took 204.2 seconds including model loading; output passed partial
validation, with two audited quality fallbacks. B–E each generated full target
counts three times on 4,210-paper test-only fixtures and passed validators.
The current part_1 snapshot has 192 flagged annotations and 650 clean papers;
direct B/C sampling diagnostics produce only 52 queries / 16 cases. These are
newer measurements than the earlier one-fallback snapshot recorded below.

- Experiment generators now live under `data/exp_*`; A merge/review selection
  are in `data/exp_a`, and Qwen evaluation is in `scripts/exp_a`.
  B–E generation rules belong to their individual builders, with shared rules
  and dispatch under `data/`. Shared I/O and validators remain in `scripts/`.
- Fresh full suite after relocation: **77 tests passed**. All nine relocated
  or affected CLIs passed `--help` from outside the project directory.
- Compared generator functions before/after splitting: their ASTs match.
  Qwen A generator bytes are unchanged (SHA256
  `48ff88ceca3c0e259675a34e684a6ad871bfe0f3e24afc599f7d1fff81d48d72`).
- Fresh real corpus and partial A validation passed. The read-only 400-paper
  preview still has 59 five-facet, 281 four-facet and 60 three-facet papers.
  Merge stops at missing part_2; B–E stop at the missing complete A manifest.
- Read-only GitHub branch check confirms `Prepare-Dataset` points to
  `160d76444d79e022ebba241fbe396523bf5e1a2a`, which contains retry scoring and
  best-attempt selection. Folder changes in this session remain uncommitted.

## Earlier Qwen gold evaluation verification — 2026-10-05

- Fresh full suite: **77 tests passed**. Eight new evaluator checks cover literal
  TP/FP/FN and asymmetric metrics, pending/unattributed gold, count/IDs/cohort,
  normalized labels with meaningful punctuation preserved, N/A empty metrics,
  cross-facet diagnostics, corrupted silver, deterministic report rebuilds and
  source/output safety.
- One focused independent review reproduced source-manifest overwrite when a
  custom A source shared the evaluation destination. Fixed by rejecting source
  directory overlap before writes; regression verifies source and human gold
  bytes remain unchanged and a separate destination still works.
- Evaluator compares independently completed reviewed forms with verified A
  silver. Reports explicitly measure lexical agreement, disclose selection
  bias, and retain paper text/evidence for human semantic error analysis.
- Actual part_1 evaluation stopped because no completed human gold file exists;
  no real metrics report was fabricated. Evaluation outputs are Git-ignored.
  Local documentation links and tracked whitespace checks passed.
- Commands/protocol: docs/EVALUATE_QWEN.md and scripts/exp_a/evaluate_exp_a.py.

## Earlier dataset implementation verification — 2026-10-05

- Fresh full suite: **69 tests passed** using Python 3.11.16.
  Target-sized, explicitly test-only temporary fixtures produced B 300 queries /
  30,000 pairs; C 1,500 cases / 30,000 pairs; D 300 users / 15,000 events;
  E the same 300 users / 1,200 profiles / 18,000 events.
- Rebuilds matched byte-for-byte, including D/E in fresh processes with a
  different PYTHONHASHSEED. Corruption checks cover labels, observable truth,
  references, input/output hashes, temporal ordering and partial A rejection.
- Fresh real corpus gate passed: 4,210 papers, 4,235 active source references,
  9,390 scope audit records. A part_1 validator passed as explicitly partial:
  842/4,210 records, one audited fallback. Missing parts 2–5 block full handoff.
- A merge dry-run correctly stopped at missing part_2/manifest.json without
  writing merged output. Read-only 400-paper selection preview on part_1 had
  59 papers with five nonempty facets, 281 with four and 60 with three. This
  preview is not the final cohort and creates no human gold or review queue.
- B/C/D/E real-corpus dry runs all stopped at the missing full A manifest;
  none created an experiment manifest. Documentation local links and tracked
  diff whitespace checks passed.
- One fresh independent code review found two important issues, now fixed:
  D/E observable behavior counts included holdout outcomes; A merge accepted
  different resolved checkpoints. Added regression tests for both, including
  rejecting forged combined behavior reports and permitting fallback metadata
  without runtime model fields. Also restrict merged output to experiment A.
- Source, configs, wrappers and validators are implemented. B–E datasets on
  the real corpus, the final 400-paper review queue and scientific/model results
  remain pending complete real A coverage and independent human review.
- Existing local A generator/resume changes are preserved. No GPU annotation
  batch, Git commit, push or fabricated real annotations were performed here.

## Earlier local Qwen snapshot — 2026-10-03

- Local runtime: Python 3.11.16; PyTorch 2.6.0+cu124; Transformers 4.57.6;
  accelerate 1.15.0; bitsandbytes 0.50.2. CUDA is available on RTX 4060 Laptop 8 GB.
- Qwen/Qwen3-4B-Instruct-2507 revision cdbee75f17c01a7cc42f958dc650907174af0554
  loaded and inferred successfully using NF4 double 4-bit, float16 compute.
  Observed VRAM during the smoke run: approximately 3.8 GB.
- 14 unit checks passed; main corpus gate passed: 4,210 papers, 4,235 active
  source references, 9,390 audit records. Corpus text and IDs remain unchanged.
- Prompt 1.5, guideline 1.0: five real papers accepted in the pilot and the
  partial-output validator passed. P000001 is a prompt-development example;
  exclude it from held-out human gold.
- Structural/source checks cover exact evidence, source phrases, IDs, schema,
  resume, provenance, duplicate-run lock, partial export and Windows launcher.
  They do not measure semantic accuracy or extraction completeness. One of the
  first five papers received five empty lists; this is a model output that needs
  semantic review, not a missing paper filled by the code.
- The full run was started at 2026-10-03 12:00 Asia/Bangkok, resuming after the
  five pilot records. That run stopped after six accepted papers on a validation error in P000007. The batch runner now records per-paper validation rejections and continues with later papers; runtime/GPU failures still stop. Six previously accepted records are preserved in generated/pre_batch_snapshot and are reprocessed under the new generator hash. The batch flow passed a real rejection at P000007 and continued to later papers. Before the final zero-annotation reset fix, seven accepted records and logs were preserved in generated/pre_reset_fix_snapshot; SQLite integrity_check passed. The final full run was launched after the fix; generator, prompt and config remain frozen for this run. This is a launch snapshot, not a completion claim. Read the
  checkpoint for live counts; manifest/JSONL export on completion or handled stop.
  B–E may consume the full corpus only after complete A validation succeeds.
- No API key is used for inference; no human gold is generated. Failed API
  outputs and rejected local pilots remain in generated audit subdirectories.
  Annotator is qwen_local, tier silver, review_status unreviewed.
