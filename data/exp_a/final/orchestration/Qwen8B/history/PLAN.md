# Gold400 V-recall fine-tuning pilot — 2026-10-28

User authorized a fine-tuning trial on the accepted gold400, with paper-level train/valid/test and Precision, Recall, F1; no F2. This is an experimental release, not replacement of existing adapters.

Use 280/60/60 papers, seed 42, reject duplicate normalized titles/abstracts across splits. Bind gold concepts to their existing reviewed sentence evidence without rewriting labels. Freeze the original Qwen3-8B revision, v3.7 extraction prompt, V-recall three-call policy and embedding scorer (threshold .85). Train a fresh rank16 QLoRA adapter, 3 epochs, learning rate 1e-4, completion-only loss. Retain all epoch checkpoints; choose highest validation V-recall micro F1 (tie: Recall, then earlier epoch). Only after selection run baseline and selected adapter on test.

Gold400 was purposively selected and already inspected during pipeline development. The split prevents training leakage for this run; it is not a pristine external holdout. Record this in results. Existing V-recall gold400 used no adapter. Existing v1/v2 artifacts stay untouched.

- [x] Test deterministic splits, source/gold/evidence binding, private package integrity and test isolation.
- [x] Build isolated release using frozen runtime, existing QLoRA helpers and all three saved checkpoints.
- [x] Verify all token lengths and targets locally, compile bootstrap and run regression checks.
- [x] Upload a new private input dataset and launch a new private Kaggle kernel; verify actual cloud status.

Training reads only train/valid SFT examples; checkpoint selection uses only validation references. Test reference content is opened by scoring after prediction records are sealed. Report micro Precision/Recall/F1, macro F1, facet metrics, fallback and cost. Store hashes, split IDs, validation scores, chosen adapter and paired test output. No automated follow-up or public publication.

## Current validator update and launch boundary

Launched after explicit user approval on2026-10-28: final v5 package is uploaded to the named private dataset (ready, private verified), and private kernel version1 is RUNNING. Cloud source SHA256 and dataset binding match the local release. Latest evidence is `release_20261028_v5/launch_report.json`. Training optimizer steps are not yet confirmed. The historical upload block below is resolved by the user's explicit push instruction.

User explicitly requested adapting the validator to the accepted gold. The current release is `release_20261028_v5`, using the reference-free `source_attributed_paraphrase_v1` gate and consistent paraphrase instructions. All400 /3,346 unchanged gold labels survive the full packaged pipeline. 16 new tests and20 historical regression tests pass. See `VALIDATOR_RESULT.md` for behavior, limitations and exact hashes. No gold lookup is used in runtime validation.

After explicit upload approval, use only the final v5 input-dataset and kernel, verify dataset privacy/readiness, then verify actual cloud status. Earlier local snapshots are superseded and must not be uploaded. Upload approval remains pending; no new upload or GPU run occurred.

## Historical v2 preflight and upload block

Final unlaunched release: `release_20261028_v2`. The earlier v1 directory is a local preflight snapshot, never uploaded. Five new package/data tests and twenty existing V-recall regression tests pass. Every bundled Python source compiles. Longest full supervised sequence: train3219, valid2977 tokens; limit4096. Bundle SHA256: `94b416da285ba624199eb42030eed881f5e3726815547e6e7228df03fb6f087f`.

Gold/validator disagreement: 191 papers total (train130, valid29, test32). Accepted gold concepts and evidence remain unchanged; full original validator disagreements are recorded in `release_20261028_v2/preflight.json`. This trial intentionally measures the existing V-recall gate; potential rejection of learned paraphrases is a material limitation.

Independent code review found incorrect inherited `training_performed=False` in fine-tuned prediction records; corrected to reflect whether an adapter is enabled. Original decoder closure retained, with optional PEFT loading only. Trainer snapshot changes only attention helper location, retaining all3 epoch checkpoints and human-gold provenance. Its provisional lowest-loss adapter is superseded by validation-F1 selection before test.

Upload was blocked by automatic approval review: explicit user approval is required to transmit sources, gold400 labels and experiment artifacts to the new private Kaggle dataset `htnkhi/exp-a-v-recall-gold400-qlora-inputs`, for private kernel `htnkhi/exp-a-v-recall-gold400-qlora`. No upload or new GPU run occurred. Resume only after that approval; do not bypass the rejection. After approval upload the final v2 input-dataset, verify dataset readiness/privacy, push v2 kernel with a two-T4 accelerator and verify actual status. Record cloud identity/version/signature in a launch report.
