# Gold-compatible V-recall validator — 2026-10-28

Current local release: `release_20261028_v5`. Policy: `source_attributed_paraphrase_v1`.

Update: user approved upload and requested push. The v5 private input dataset is ready and private kernel version1 is RUNNING, checked2026-10-28T02:45:50Z. Cloud code hash and input binding are verified. Training steps are not yet confirmed; see `release_20261028_v5/launch_report.json`. The earlier pending-upload note below is historical and resolved.

## Verification

- Same unchanged accepted gold: 400 papers /3,346 labels. Previous gate flagged191 papers /269 error entries. New gate rejects zero papers.
- Full packaged three-call pipeline, with model responses replaced by reviewed labels: all3,346 labels survive unchanged, including final dataset filtering. This is an integration check, not new model inference or an F1 result.
- 16 new tests and20 existing V-recall regression tests pass. Independent review verified final dataset filtering, exponent-aware numeric parsing, and explicit/qualified negation handling.

## Changes

Allow faithful paraphrases, word reordering and context from the supplied title/abstract. Keep a primary evidence ID mandatory. Lexical and scope heuristics now produce audit warnings rather than hard rejection. Preserve meaningful name symbols (bAbI+ versus bAbI; C++, C and C#). Accept capitalized named resources beginning with Corpus. Independent findings and limitations can occupy separate labels without repeating the entire sentence.

Malformed schemas, wrong IDs, non-source evidence, duplicate identities, numeric values absent from the supplied source, explicit aligned-claim polarity reversals and clearly generic resource descriptions still fail. Normalize numeric separators, multipliers and scientific notation. Differently worded negatives such as with-no/without remain eligible for semantic review.

The validator imports no gold/reference data and contains no paper-ID or gold-label allowlist. Gold appears only in tests and offline compatibility reporting. Lexical/scope warnings remain in attempt and final audits.

`score_kind=structural_source_consistency_not_semantic_confidence` removes the lexical-copying and facet-population preference. `semantic_entailment_verified=false` is explicit. Passing does not prove entailment, facet role, novelty, complete coverage, correct attribution of a number to an experiment, or every condition/negation scope. The source-review pass still checks those. No broad semantic classifier was added.

## Integration

The new package wires the policy into repair assessment, coverage deduplication and final dataset filtering. Extraction, review and coverage instructions consistently allow source-supported paraphrases. No gold-specific example answers appear in those instructions. Model revision, decoder, three-call budget and embedding scorer remain fixed. Baseline and adapter will both use this revised policy and instructions on the same test60; historical scores are not a paired comparison with this changed policy.

Splits remain train280/valid60/test60, seed42; no test SFT examples. Checkpoints are chosen by validation F1 then Recall before test. Gold400 was previously inspected during development; this is an exploratory split, not an external pristine holdout. Original historical artifacts remain unchanged.

Gold SHA256: `3612e60fbcb302766ec18ca332ef7e72e103ca26b7b10e7d6d39b62ffc23c20c`.
Settings signature: `f8973981a6d9506a658c9d5f9bafe76e29fcbe2285af88c10a4774d04adc1cce`.
Bundle SHA256: `41936f5b1b9d1e2bc9e60de4bd224ce2e55bbe8c1ae4f550a1509c95fd479ef9`.
Details: `release_20261028_v5/preflight.json`.

No Kaggle upload or new GPU run occurred. The earlier automatic-review upload block remains pending explicit approval for the named private Kaggle destination. This request authorized validator changes, not upload.
