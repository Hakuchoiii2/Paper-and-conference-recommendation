# Exp A v2 Training Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans for inline pipeline implementation; independent source annotation/review and cleanup use superpowers:dispatching-parallel-agents.

**Goal:** Prepare independently source-reviewed v2 train/dev labels and launch one separate private QLoRA v2 run after preflight, while safely cleaning disposable workspace files.

**Architecture:** Reuse unchanged v1 training internals. A v2 boundary validates review provenance/source/split/token contracts, writes v2-only data and deterministic packaging, and verifies the package before a training-only kernel delegates to v1 train. Source reviews and cleanup are separately checkpointed.

**Tech Stack:** Python .venv-qwen, stdlib, existing Transformers4.57.6/PEFT0.18.1/tokenizer, Kaggle CLI Python314.

**Spec:** docs/superpowers/specs/2026-10-19-exp-a-v2-training.md (approved in-chat direction).

## Global Constraints

- Preserve 38 protected v1 hashes; split467/100/100; never tune on test or use student outputs as labels.
- evidence_ids, policy2.2, source-first AI references, human review pending; independent author/reviewer IDs and sealed hashes.
- Base Qwen/Qwen3-8B revision b968826d9c46dd6066d109eabc6255188de91218; no continuation of adapter v1.
- Sequence4096/assistant2048, exact prefix/EOS, no truncation; v1 QLoRA hyperparameters unchanged.
- New private htnkhi v2-only paths; send comparison before push; confirm launch once; no scheduled v2 training checks.
- No writes outside allowed roots without escalation; never bypass automatic-review rejection.

## Review Focus

1. A source/label changes after acceptance: hashes must reject release/runtime.
2. Self-review, missing facet decisions or unresolved semantic issues must not become training-ready.
3. A missing/reassigned/duplicated paper or test ID must fail before writing a release.
4. Multi-evidence targets must retain same inference prefix and EOS; overlength must fail, never truncate.
5. A tampered/private-metadata mismatch, escaping zip member or v1 output path must fail before upload/train.

### Task 1: Source confirmation and safe cleanup

**Files:** v2/review/confirmation12/*; data/exp_a/cleanup_manifest_2026-10-19.json.
**Interfaces:** Source-only review queue -> independent sealed annotations/audits -> source-adjudicated policy confirmation; cleanup -> counts/bytes and protected-hash evidence.
- [ ] Two authors independently annotate/ground/cover all12 and seal before cross-review.
- [ ] Resolve differences from source; write per-facet decisions and independent acceptance.
- [ ] Remove only validated disposable caches/test fixtures; verify hashes and record manifest.

### Task 2: Checkpointed full train/dev review

**Files:** v2/review/batches/*; v2/review/source_papers.jsonl; annotations.jsonl; decisions.jsonl; review_manifest.json; progress.json.
**Interfaces:** Frozen567 queue + accepted policy -> batches with source/author/reviewer/label hashes -> complete accepted records.
- [ ] Assign source-only batches; each first draft precedes independent review.
- [ ] Verify all source words/evidence IDs/roles/conditions/negation/coverage; resolve source-limited cases in audit without changing source/split.
- [ ] Aggregate only accepted records and retain batch provenance; 567/567 required.

### Task 3: V2 training boundary and packaging (TDD)

**Files:** create data/exp_a/finetuning/v2/training.py, training_kernel.template.py; scripts/exp_a/finetuning/test_v2_training.py.
**Interfaces:** prepare(review_dir,destination,tokenizer=None) -> training data manifest; messages(paper,instruction) -> exact two-turn inference prefix; build(data,destination) -> private deterministic package; run_training(root,settings) -> unchanged-trainer result with v2 provenance.
- [ ] Write failing integration tests for complete accepted multi-evidence data, self-review/missing-review/tampered-source rejection and original split preservation.
- [ ] Write failing real-tokenizer prefix/EOS/no-truncation and packaging-no-test/v1-output protection tests.
- [ ] Implement the smallest v2 boundary; delegate existing trainer unchanged and repeat contract validation at runtime.
- [ ] Run targeted tests RED -> GREEN, then relevant full suites; fresh independent code review; fix meaningful findings with regression tests.

### Task 4: Preflight and authorized launch

**Files:** v2/training_data/*; v2/training_build/*; updated README/readiness/comparison; launch_report.json.
- [ ] Build only after Task2 acceptance; real-tokenizer full567 preflight and hash/provenance verification.
- [ ] Stage deterministic private payload; inspect files/metadata, compile/import runtime without GPU, verify no test/source leakage and v1 hashes.
- [ ] Update/send concrete v1-to-v2 comparison including actual hashes/config/counts/tests.
- [ ] Create/update private v2 dataset and push distinct training kernel; if automatic review blocks, stop that action and report exact reason.
- [ ] Immediately verify launched kernel/version/signature and QUEUED/RUNNING; write report, keep automation PAUSED, no future training monitor.

## Execution ledger

- User accepted the in-chat three-step design and instructed implementation; cleanup is additional steering, not cancellation.
- Ruling: work in new v2 paths in place because the dirty parent-main subtree contains essential untracked experiment data; do not reset/stage/commit unrelated work.
- Ruling: old adapter-v1/new-prompt failure remains a diagnostic risk, superseded as a mandatory pre-train gate by the newly accepted direction. Data review and preflight gates remain.
- Task1 in progress: confirmation12 source selection sealed, two independent authors active; cleanup separately audited.
- Tasks2–4 pending. Pipeline implementation may proceed independently of label content, but release/upload cannot.

- Checkpoint 2026-10-19T01:51:16.878484+00:00: cleanup verified complete; source confirmation both drafts sealed and cross-review active. Task3 controlled-fixture TDD in progress; no real567 release.

- Ruling: model instruction is prompt_v2_2.md only; policy_v2_2.md is versioned reviewer policy/provenance and contains pilot/history instructions that must not enter the model prompt. Shared messages() renders identical train/inference system content.
- Ruling: batch source records use exact paper_id/title/abstract/split; staged evidence_options metadata removed before any full-batch draft, with all source hashes refreshed. Text/IDs/splits unchanged.

- Task1 complete: cleanup55 files/856944 bytes/13dirs verified; source confirmation12/95labels accepted after two source-first drafts, cross-review, adjudication and both final semantic rechecks. Human review pending, policy2.2 unchanged.
- Task2 active: source authors A/B processing lane0/lane1; lane2 assigned to pipeline implementer after Task3. No full release exists.


### Checkpoint 2026-10-19T06:47:45.662707+00:00

Task3 pipeline implementation complete and independently inspected by root:211 Exp A tests +38 project tests PASS. Earlier discovery/import harness mistakes resolved with qualified Exp A and flat project commands. Fresh offline tokenizer test catches/fixes Transformers model_info lookup by resolving exact cached snapshot; root real48 accepted-source token preflight max2576 sequence/579 assistant, exact prefix/EOS, no truncation (sample only). Full567 review still active. Root independently reviewed lane0 batches00–04; no own draft acceptance. Work balanced: cleanup_workspace authors lane2 00–07 (96), root authors lane2 08–15 (93); source_confirmation_a reviews lane2. Source_confirmation_b reviews remaining unsealed lane0; cleanup_workspace reviews lane1. Stable actual actor IDs preserved. Policy remains reviewer/provenance-only; prompt_v2_2.md alone is the actual model instruction, identically rendered for train/inference. No real release, dataset upload or train launch yet.


### User-approved lean scope 2026-10-19T07:19:33.103612+00:00

User explicitly replaced exhaustive per-paper independent review with source-first all567, automated all567 and selective independent sample/difficult cases. Preserve completed work; no additional v1 probes/policy samples or repeated unchanged full suites. Final source release now567 (467train/100dev),98 independently source-reviewed (60existing+38selected),469 explicitly source_authored_unreviewed, all AI/humanreviewpending. Source/hash/split/grounding gates pass,18 boolean-flagged cases independently resolved; old uncertainty notes remain historical author audit. Manifest 998d18de3a40f9cfc18e858a3ca2f333698e5be7f43a61f409a323e66774814d. All567 draft token preflight max2899sequence/731assistant passed, final overlay preflight running. Lean10tests:9pass,1Windows childstderr Unicode decoding harness error; fixed explicit child-Xutf8 and isolated packaging recheck passed. Existing211+38 passed before lean change and are not repeated. Independent static gate review by source_confirmation_a found no blocker;2targetedtests passed. No upload/train yet.


### Launch complete 2026-10-19T07:24:20.378088+00:00

User received actual final comparison before upload/push. New private datasetID12699834 ready; one new private kernelversion1 successfully pushed. Immediate statusQUEUED, remote bootstrap SHA equals local 55ac8a667bd829e23806ccbbec302ac7627c01c8382c696f3881b4de09782016, bundle pin3a4093e7113bfa9bf69bbd5b1a9f58418f7409ec7482653eb9d393da45138860, local settingssignature3875d3d25d83d48170e26a97b07fb2338388b7ba3b557ff261396578f5207550. Final567 source references98reviewed/469unreviewed, tokenizer maxsequence3007/maxassistant968, no truncation. All38v1protectedhashes verified after launch. Launchreport build/training_launch_report.json. Automation alreadyPAUSED verified, no newmonitor, no traincompletion/F1 claim.
