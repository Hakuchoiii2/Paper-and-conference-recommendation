# Independent semantic review of pilot40

Reviewer: independent AI reviewer. Human review: pending.
This report reviews provisional AI references, not human gold, model accuracy, or test scores.

## Coverage and blinding

- Read all 40 supplied titles/abstracts and evidence options under policy_v2_1 and prompt_v2_1 before revealing any old/provisional labels.
- Saved and SHA256-sealed 40 independent extractions, source notes and separate exact evidence quotes before unblinding. See BLIND_SEAL.json.
- Blind annotation SHA256: 7304e2ddaaed699fe03b144835cdd77665b70e9ff6dbed4434fc6eac81c75ae0.
- 40 exact matching IDs; all 200 facets reviewed. Sources: 37 CSFCube, 3 SciFact. Train/dev × existing/additional-reference strata each contain 10 papers.
- All 40 sealed drafts and all 40 concrete proposed revisions pass v2.1 ground_response. Lexical/schema validity is not semantic certification.
- The source sample is stratified with SciFact coverage; disagreement counts do not estimate corpus error rates.
- No v1 labels, held-out test, student predictions or model scores were changed or used.

## Dispositions

| Disposition | Facets |
| --- | ---: |
| Accept exact independent/provisional content | 95 |
| Accept provisional after source reconciliation | 79 |
| Concrete correction required | 12 |
| Evidence-context completion required | 6 |
| Source comparator pending | 1 |
| Policy boundary pending | 2 |
| Advisory granularity/coverage | 5 |
| Total | 200 |

There are 21 material facets across 19 papers, plus 5 advisory facets. The accepted 174 facets include cases where the provisional version was better than the blind draft. These counts are review dispositions, not error/accuracy metrics.

## Concrete corrections

Every entry below has executable replace/add/remove operations, exact replacement items, ordered evidence_ids and source quotes in semantic_findings.jsonl. proposed_annotations.jsonl applies concrete material operations only; it leaves the two policy-pending facets at their provisional contents and excludes advisory edits.

| Paper/facet | Action |
| --- | --- |
| P001479 task | Restore large directed graphs to the indexing objective (T0). |
| P002108 contribution | Restore This suggests; add A5 for these partitions and A6 for the A7 inference. |
| P002263 task | Add explicitly studied classifier-design generalizability to new courses (A2). |
| P003166 method | Add temporal first/peak/last frame annotation (A7). |
| P003166 contribution | Add the designed elicitation procedure, distinct from CASME (A5). |
| P003168 contribution | Suspend 97%-of-performance claim: denominator is missing from supplied input (A6); preserve quote as pending. |
| P003628 contribution | Add released AZ classifier (A10); retain QA/summarization scopes on A7/A8 findings. |
| P001150 contribution | Add event-data corroboration finding with A6+A7; preserve observational rather than causal wording. |
| P002993 problem | Restore antecedent class of unsupervised lower-dimensional ensemble methods with A1+A2. |
| P001860 problem | Identify the deficient cooccurrence-pattern vector method with A1+A2; do not attribute its limitations to compositional methods. |
| P002110 problem | Restore speech/large-scale application scope and labeled-data context (A0+A1). |
| P002110 contribution | Tie utility finding to the framework and speech/pronunciation experiment (A2+A4+A5). |
| P003587 contribution | Identify merging plus splitting as the combination measured, using A5+A6+A8; keep at least equivalent. |
| P000349 contribution | Add A4 to A9/A10 to ground the reported approach. |
| P000501 contribution | Add A4 to A5 for the resulting MPHF data structure. |
| P003918 contribution | Add A4 to A6 for these discourse relations. |
| P001080 contribution | Add A2 to A3 for this methodology. |
| P001790 contribution | Add A5 to A7 for the proposed classifier in both approaches. |
| P000841 contribution | Add A4 to A6 for both discourse varieties. |

Evidence-completion items do not allege that the reported comparison is false. They repair the minimal evidence set required to establish its subject/scope under the multi-sentence policy.

The five advisory facets concern the two-stage intent procedure, multimodal learning objective, MDLClass qualitative capability, French identity of the treebank artifact, and splitting Code/data into separate artifacts. These are deliberately separated from actual claim/scope defects.

## Policy decisions

See policy_decisions.json for alternatives and the recommended boundary.

1. Survey methods (P003879): the tentative rule that a topical survey labels actually performed review/synthesis/taxonomy procedures, while empirically compared techniques qualify as study methods, is defensible. It is not fully explicit in v2.1. A methodological demonstration should require actual supplied examples/procedure. P002633's reflexivity role can use A0+A7+A10, not merely its review mention. Do not label A11 recommendations as methods already used.
2. Ontology datasets (P004130): Klout Topics is named, introduced and operational. It qualifies if dataset explicitly includes named structured knowledge resources/ontologies. The present corpus/benchmark/database/lexicon list does not state that extension. Under a strict list use []; under the recommended broadened definition retain Klout Topics. User count and Klout.com are never datasets.

If these clarifications change eligible labels, they are operational semantic rule changes. Version the rule and test a fresh source-first train/dev sample under it, as section 6.5 requires. This sealed v2.1 pass does not retroactively test language written after unblinding.

## Source quality and provenance

The five existing source-quality cases were reviewed after the seal using the parent's supplemental report, without independently fetching those websites. That report supplies quality evidence, not label text. The hybrid-model antecedent in P004191 is supported by A9+A10. Keep BioProp excluded on abstract-only role evidence, raw OpenStreatMap spelling, and conservative labels for the partial Harris paragraph. Book/source eligibility for P000779 and completeness of P000271 remain versioned data-quality decisions.

The newly identified 97% denominator gap is recorded separately. A safe annotation decision is to suspend that asserted quantitative item and retain the exact original sentence in pending metadata; external facts cannot complete its label.

## Assessment

Material disagreement remains in the provisional annotation set as reviewed. The proposed concrete corrections are reviewable and schema-valid, but require adjudication; the policy-boundary decisions and any changed-policy fresh sample remain open. No semantic-stability certification and no 667-paper rollout are recommended yet. Human review remains pending.

Artifacts:
- semantic_review.jsonl: all 200 facet dispositions with blind/provisional/proposed items.
- semantic_findings.jsonl: 26 flagged facets and concrete operations/alternatives.
- proposed_annotations.jsonl: 40 concrete proposed revisions, not final gold.
- policy_decisions.json: explicit unresolved choices and fresh-sample implications.
- source_quality_review.jsonl: 5 existing source cases and the new comparator gap.
- REVIEW_SUMMARY.json: counts, input hashes and verification results.
- BLIND_SEAL.json: immutable first-phase hashes.
