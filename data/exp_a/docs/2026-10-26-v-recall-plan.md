# V recall-first implementation plan and ledger

User approved prioritizing recall and testing within the existing three-call ceiling. Execute inline using writing-plans, executing-plans, TDD and ponytail. The approved conversation is the short design: unchanged draft and V validator; replace one review with an all-source search for omitted task/method ideas; report recall/F2, precision, false additions and cost.

Architecture: exact frozen draft -> first original V review -> task/method additions only. The first review retains original V semantics and seed. Coverage always runs even for a validator-valid result, sees all source sentences including cited ones, and cannot remove/rewrite existing labels. Each addition is individually assessed with the same scoped V validator. Partial failures retain accepted additions and are visible. Reference/scorer is evaluation-only. The old V control runs unchanged alongside the new arm.

Files: new data/exp_a/.kaggle/v_recall/{recall.py,runner.py,build.py,bootstrap.template.py,README.md,release_20261026_v1}; scripts/exp_a/pilot/test_v_recall.py. Do not modify older releases or shared extraction code.

Constraints: Qwen3-8B frozen revision/NF4/greedy; same pilot50, draft hashes, source, prompt, scorer/reference; max 3 logical calls x2048 output tokens, including inherited draft; <=2 new calls. No training. Development cohort with AI reference, human validation pending. F2=5TP/(5TP+4FN+FP), aggregate and per facet. Actual costs differ despite equal ceilings.

Review focus: additions from already-cited sentences; invalid/unknown evidence and malformed replies; preserving existing labels and non-target facets; budget/seed/cost/inherited provenance; no reference leakage or scorer drift.

- [x] Task 1: failing behavioral tests; implement annotate and add-only validation with real frozen validator. Verify same-sentence omissions, tasks, duplicates, malformed/truncated replies, partial rejection, cost and immutability.
- [x] Task 2: build paired V/V-recall frozen release, evaluation recall/F2 and per-paper added/matched/unmatched labels. Verify packaged tests, baseline hashes and pilot regression suite.
- [x] Task 3: fresh review; address material findings; launch a separate private two-T4 Kaggle kernel; pull cloud code and compare to release, report actual status.

Ruling: work in a dedicated experiment directory on the existing exp_A checkout, preserving previous artifacts and uncommitted review downloads. No branch reset or unrelated commit. User approved the concrete experiment; no additional design approval loop.

Task 1 complete: missing-module RED, then 8 behavior tests GREEN; extended to 10 including exact first-review message/seed equivalence and F2. Packaged runtime also 10/10. TemporaryDirectory default Windows sandbox temp was inaccessible; tests now use experiment-local temp paths.

Task 2 complete: frozen 50-source/draft preflight, packaged 10/10 behavior tests and 50-paper offline reporting smoke passed. Source/code/settings hashes and private metadata rechecked. Independent read-only reviewer found no material blockers; report saved in release/code_review.json. Full A regression initial run: 252 tests, 1 tokenizer metadata network error; retry with network in progress.

Task 3 complete: full A suite 252/252 GREEN with tokenizer metadata network access. Independent reviewer no blockers. Submitted separate private kernel htnkhi/exp-a-v-recall-pilot50 version 1 using two-T4 accelerator. Pulled code byte-identical; metadata and frozen hashes verified. Kaggle RUNNING; no scores or worker startup evidence yet. An initial authentication attempt submitted nothing; official SDK refreshed existing OAuth in memory and exactly one version was submitted. No secrets saved in project. No old files changed; untracked local change kept for user, no merge/PR.
