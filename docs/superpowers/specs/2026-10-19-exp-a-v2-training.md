# Exp A v2 training and workspace cleanup

Approved direction: the user accepted the three-step in-chat design and said to try it, then asked for workspace cleanup. Proceed in the named Windows project. The old adapter failing a changed prompt is diagnostic evidence, not a requirement that v1 must pass v2 before training. Data quality and preflight still gate upload/training.

## Outcome

Produce 567 independently source-reviewed AI reference records under policy v2.2/schema evidence_ids, preserving original 467 train / 100 dev and the sealed 100 test. Train a separate adapter from Qwen/Qwen3-8B revision b968826d9c46dd6066d109eabc6255188de91218, with identical train/inference prompt rendering, and package a private htnkhi v2-only dataset/kernel. Do not overwrite v1. No F1 or trained-v2 claim before a qualified run.

## Data and review

- Confirm policy clarifications on 12 fresh purposively selected source-only train/dev papers (6/6); two independent authors seal drafts before comparison. Resolve semantic differences from sources; this is AI review, human review pending, not generalization evidence.
- Then read/review all 567 sources in checkpointed batches. Independent reviewer identity must differ from draft author. Store labels, per-facet role/evidence/conditions/coverage decisions, source/policy/prompt/schema/label hashes and batch seals. Do not use student predictions or merely rename fields. Do not open test source/targets for tuning.
- Source text stays frozen. Missing input cannot be completed from full text. Preserve upstream spelling; omit underdetermined findings, retain the exact gap in audit. Keep all split IDs; classify source/scope uncertainty explicitly instead of silently replacing or reassigning records. Labels remain ai_reference / human_review_status=pending.

## Training boundary

Reuse the unchanged schema-agnostic v1 trainer for assistant-JSON-and-EOS-only loss, lowest-dev-loss checkpoint selection and existing QLoRA settings. Add one v2 boundary module for validated data preparation, deterministic private packaging and pre-training contract verification, plus a training-only kernel template. The existing v2 probe modules/build/raw logs remain untouched.

- Require complete independently reviewed 567 labels, fresh policy confirmation, exact original split and hashes, source grounding, five per-facet review decisions and honest provenance before preparing a release.
- Real pinned tokenizer: max sequence 4096, assistant completion <=2048, exact inference prefix/EOS, no truncation. Runtime independently repeats v2 data/contract checks before invoking trainer.
- Model/revision pinned as above; LoRA r16/alpha32/dropout0.05/all-linear, NF4 double FP16, epochs3, LR2e-4, accumulation8, seed42; output/checkpoint paths explicitly v2-only.
- Package only train/dev inputs and required code/policy/schema/manifests. No test papers/references or v1 weights. New private dataset htnkhi/exp-a-qwen-qlora-v2-inputs and kernel htnkhi/exp-a-qwen-qlora-v2. Local preflight and tests must pass; data are private and AI references.
- Send final v1-to-v2 comparison with actual counts/config/tests/hashes immediately before any train push; notification, not another approval. Check kernel/version/signature and QUEUED/RUNNING once after push, write launch report, leave automation PAUSED; no recurring training monitor, no archive.

## Cleanup

Remove only verified disposable project Python/tool caches and empty/clearly temporary test fixtures. Keep venvs, model/checkpoint weights, research raw outputs, source/labels, manifests/log evidence, user Git changes and coursework untouched. Native PowerShell deletion must validate each absolute resolved target under the exact project root, reject reparse points and verify protected hashes before/after. Record manifest counts/bytes. No broad git clean/reset.

## Execution constraints

The project is a dirty subtree of a parent main checkout with essential untracked research data. Use new v2 paths in place; no bulk staging/commits or worktree copying. Writes outside writable roots require explicit tool escalation. If automatic approval rejects a mutation, do not bypass it: finish unaffected work and report the precise rejection.
