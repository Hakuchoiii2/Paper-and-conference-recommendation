# Gold400: improvement investigation — 2026-10-27

Scope: offline diagnosis of the completed htnkhi/exp-a-v-recall-human-gold400 run. No model rerun, pipeline modification, reference modification or scorer change. Sources are the downloaded three evaluation reports, coverage_addition_audit.json, experiment_summary.json and immutable release_20261026_v1 code/source.

## Verified baseline

All three evaluation reports contain 400 unique papers and 3346 reference concepts. Micro F1: Draft 44.3832%, V-review1 44.3410%, V-recall 43.4636%. Draft is currently the strongest observed F1 baseline; intermediate outputs reuse the same run and are not independently generated experiment arms.

Draft -> V-review1: per-paper F1 improves for 65, declines for 53, stays equal for 282. V-review1 -> V-recall: improves for 19, declines for 144, stays equal for 237. Per-paper comparisons aggregate TP/FP/FN across facets before calculating F1.

## Measured failure modes

1. Coverage accepts 240 additions: task 98 (8 matched to gold), method 142 (18 matched). Net matching change is +22 TP and +218 FP, not +26 TP: one-to-one matching can reassign an existing match. Task changes +7 TP/+91 FP; method +15 TP/+127 FP. The 26 item match flags must not be interpreted as 26 newly recovered gold concepts.
2. 434 candidate items are rejected across 216 papers: 415 source-word/order violations, 16 item-schema violations, 3 negation violations. Replaying every rejected item through the immutable apply_additions function with its original paper and an empty base reproduces all 434 rejections. This is a deterministic validator diagnostic, not a scored replacement run.
3. Among 415 lexical/order failures: 356 contain words absent from their cited sentence under the existing word-form matching; 59 have only ordering/sequence issues. Only 12 match another supplied source sentence; 403 match no supplied sentence. Alternative lexical support alone does not establish the correct semantic role.
4. Diagnostic normalization of the evidence alias into evidence_id, only where it is an existing supplied ID, makes 7 rejected items pass the complete unchanged validator. This does not demonstrate F1 improvement and is too small to address the main failure mode.
5. Unmatched Draft predictions contain unmatched gold strings as literal substrings in 64 task pairs and 215 method pairs. These are candidate pairs, not unique papers or proven errors in the scorer. Example: task prediction “investigate the performance of two machine learning algorithms in anti-spam filtering” versus gold “anti-spam filtering”. Method examples merge “online learning” and “mining knowledge” into one broad phrase. The existing prompt already asks for concise independent labels, so adding the same instruction again is a weak intervention.

## Recommended next experiment

Prefer improving source-grounded extraction and targeted repair before expanding coverage. Reuse the existing indexed-patch repair path, which protects unrelated items, rather than rewriting whole annotations. Make task/method outputs compact independent source phrases; consider selecting explicit source spans with deterministic text reconstruction if a simpler prompt still fails. Preserve conditions and negation on problem/contribution; do not globally shorten all facets.

Compare alternatives separately:

- A: Compact source extraction + targeted repair, without the current broad additions pass. Smallest promising change; directly addresses lexical failures and combined labels. Risk: overly compact labels can lose meaningful scope. Retain dataset filtering and all semantic safeguards.
- B: Candidate additions followed by an explicit independent verification of role, novelty versus the existing annotation and evidence. Addresses the observed false-positive problem but costs an extra call or requires redistributing the current three-call budget. Evidence grounding and exact-string deduplication alone do not establish a useful new concept.
- C: Alias/schema normalization only. Small mechanical improvement; full-validator replay recovers 7 items. Not recommended as the main improvement strategy.

Recommendation: A first, with one change per ablation and an unchanged model/scorer. Treat higher F1 as the primary target unless the user instead prioritizes recall. Track precision, recall, F1/F2, per-facet scores, fallback, actual calls/tokens and item preservation. Keep the current releases immutable.

## Evaluation limits

Gold400 has now been inspected for development and must not be presented as a fresh independent holdout. Freeze the proposed intervention before evaluating on an untouched cohort, or report any reuse as exploratory/development results. Do not pick per-paper winners, tune the scorer threshold, delete difficult papers or infer semantic correctness solely from approximate embedding matches. No improvement in F1 has yet been demonstrated for a new pipeline.
