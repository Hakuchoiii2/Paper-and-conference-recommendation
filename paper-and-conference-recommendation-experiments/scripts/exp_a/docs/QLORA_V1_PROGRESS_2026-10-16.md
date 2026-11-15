# QLoRA v1 execution record

Design: QLORA_V1_DESIGN_2026-10-16.md. User requested execution and latest70/15/15
split plus GPT-reviewed corpus expansion to preserve100 test papers.

- Data audit complete:400 AI-reviewed,395 source-cleared,364 whole-paper current
  grounding-compatible; allsourcehashes verified, zero pilot50 overlap.
- Cleanup complete: matrix/pilot code grouped, pre3.5 experiment outputs removed
  according to cleanup_manifest_2026-10-16.json; shared live baseline retained.
- Trainer and data preparation implemented. Root orchestration, deterministic
  bundler, independent-review aggregation and output/adapter collector implemented.
- Verification:126ExpA tests and88project tests PASS, including actual tinyQwen3
  LoRA updates and adapter-only serialization. Full8B/T4 training completed on Kaggle; see the completion record below.
-330additional corpus papers GPT/Codex drafted and independently reviewed in
  three rotated batches.312 pass whole-paper grounding/source checks;18 are
  excluded with reasons. Two likely paper-version family members are excluded
  before the final selection;303 additional papers frozen with seed44.
- Final cohort:364 existing plus303 new AI references,667 total. Seed42
  iterative multilabel allocation produces467 train/100 dev/100 test. All
  pilot50 and prompt example IDs excluded. Cross-fold ID/title/source overlap0.
  Dataset-facet presence:152/467 train,33/100 dev,32/100 test. Two all-empty
  papers fall in train; too rare to represent in every fold.
- Independent code audit caught a missing evidence_id in aggregation; corrected
  and verified through actual aggregate-to-prepare integration.
- Completion-position logits avoid allocating vocabulary logits for prompt
  tokens.11trainer tests PASS, including equal full/selected CE loss and LoRA
  gradients plus actual Trainer accumulation/eval/best-adapter restoration.
- Source-family audit adds conservative pre-split exclusions for two likely
  PyMC3/biological-relation-extraction version families; audit saved with teacher.
- PEFT0.18.1 installed in project venv; pinned Qwen3-8B tokenizer downloaded.
-2026-10-17: private input dataset htnkhi/exp-a-qwen-qlora-inputs ready;
  private kernel htnkhi/exp-a-qwen-qlora version1 pushed and Kaggle status
  RUNNING verified. No trained adapter produced or published yet.
- Exact launched bundle SHA256:
  d5268b86cc01d751bf9d759e412f5a269ea651a056092b85dd8483aa978b7582.
  Experiment signature:
  462c10dd432670fbf61accd8589bc79641d3d7794830a98fb7315fab741c244b.
- Isolated extracted payload imports and file checksums verified; all567
  train/dev examples pass actual pinned Qwen3 tokenization and completion
  encoding. Maximum sequence3415, supervised completion567 tokens, no
  truncation. Build/verification.json and build/push_report.json preserve proof.
- Hourly thread heartbeat theo-d-i-qlora-exp-a will check quietly, collect and
  rescore complete outputs, then publish verified adapter-only private dataset
  htnkhi/exp-a-qwen3-8b-facets-qlora-v1. Notify on completion/failure/action only.
- Ruling: preserve live generated/ baseline because B–E and pilot build use it.
- Ruling: use existing checkout to preserve untracked work and requested cleanup.
- Ruling: expanded labels are GPT/Codex AI review, not human gold; retain clear
  provenance and independent source review, never label student outputs as gold.


## Completion: 2026-10-18

- Kernel version1 COMPLETE; training ran3epochs/177steps. Best adapter is
  checkpoint118(epoch2), development loss0.0926563814.
- Downloaded adapter, tokenizer, metadata and all200signed predictions. Exact
  split/source/trainer/prompt/schema/base-revision signatures verified.
- Fresh local semantic scoring agrees with cloud TP/FP/FN for both arms:
  original399/420/464; QLoRA500/324/363. Threshold0.85 unchanged.
- Micro F147.44→59.28; macro F146.99→61.00. Every facet improves. Validation
  fallback69→9/100. All labels remain AI references, human review pending.
- Contribution240 and method200 measured FP+FN account for64.05% of remaining
  errors. Exploratory source review finds model coverage/role errors plus
  alias/reference-granularity mismatches. Newly sourced45-paper test subgroup
  improves53.25→56.67, versus42.54→61.52 on55 existing-reference papers.
- Private reusable dataset htnkhi/exp-a-qwen3-8b-facets-qlora-v1 version2 READY.
  Downloaded that published version again and verified all13 payload files
  against the staged hashes and original sealed adapter manifest.
- Final packaging verification caught README being overwritten after sealing.
  Collector now retains the sealed PEFT card and adds USAGE.md, then verifies
  hashes after documentation. Regression first reproduced the error; all28
  QLoRA tests pass after fix. Version2 changes documentation only, not weights.
- Canonical local adapter: data/exp_a/finetuning/adapter-dataset.
  Downloaded cloud run: data/exp_a/finetuning/downloads/v1/exp_a_qlora.
  Result review, error analysis, cloud snapshot, collection/publication proof
  and full regression log are in data/exp_a/finetuning/build.
- Heartbeat theo-d-i-qlora-exp-a is confirmed PAUSED; no extra training run.
