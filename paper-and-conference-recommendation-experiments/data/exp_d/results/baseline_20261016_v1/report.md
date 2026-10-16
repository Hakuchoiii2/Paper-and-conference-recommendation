# Experiment D — CPU methods

Dataset: **mock**, status: **complete**, evaluation: **session_prefix**, cases: **1500**.

| Model | Group | Cases | Positive cases | direction_accuracy | direction_coverage | importance_mae | intent_compliance@10 | intent_compliance@5 | mrr@10 | mrr@5 | ndcg@10 | ndcg@5 | precision@10 | precision@5 | recall@10 | recall@5 | direction_macro_f1 |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| direction_behavior | ambiguous | 500 | 500 | 0.5000 | 0.5000 | 0.2196 | 0.3464 | 0.5056 | 0.9667 | 0.9640 | 0.8791 | 0.8950 | 0.3546 | 0.5192 | 0.8761 | 0.7476 | 0.4000 |
| direction_behavior | clear | 500 | 500 | 0.5000 | 0.5000 | 0.2222 | 0.3440 | 0.4908 | 0.9774 | 0.9750 | 0.8770 | 0.8882 | 0.3518 | 0.5004 | 0.8712 | 0.7373 | 0.4000 |
| direction_behavior | none | 500 | 500 | 0.5000 | 0.5000 | 0.2197 | 0.3516 | 0.4988 | 0.9698 | 0.9672 | 0.8776 | 0.8895 | 0.3628 | 0.5160 | 0.8779 | 0.7343 | 0.4000 |
| direction_behavior | overall | 1500 | 1500 | 0.5000 | 0.5000 | 0.2205 | 0.3473 | 0.4984 | 0.9713 | 0.9687 | 0.8779 | 0.8909 | 0.3564 | 0.5119 | 0.8751 | 0.7397 | 0.4000 |
| direction_search | ambiguous | 500 | 500 | 0.5000 | 0.5000 | 0.2196 | 0.3464 | 0.5056 | 0.9667 | 0.9640 | 0.8791 | 0.8950 | 0.3546 | 0.5192 | 0.8761 | 0.7476 | 0.4000 |
| direction_search | clear | 500 | 500 | 1.0000 | 1.0000 | 0.2222 | 0.3446 | 0.4924 | 0.9764 | 0.9740 | 0.8772 | 0.8888 | 0.3524 | 0.5020 | 0.8718 | 0.7385 | 1.0000 |
| direction_search | none | 500 | 500 | 0.5000 | 0.5000 | 0.2197 | 0.3516 | 0.4988 | 0.9698 | 0.9672 | 0.8776 | 0.8895 | 0.3628 | 0.5160 | 0.8779 | 0.7343 | 0.4000 |
| direction_search | overall | 1500 | 1500 | 0.6667 | 0.6667 | 0.2205 | 0.3475 | 0.4989 | 0.9710 | 0.9684 | 0.8779 | 0.8911 | 0.3566 | 0.5124 | 0.8753 | 0.7401 | 0.6875 |
| fixed_similar | ambiguous | 500 | 500 | 0.7500 | 1.0000 | 0.2400 | 0.3466 | 0.5044 | 0.9629 | 0.9600 | 0.8775 | 0.8921 | 0.3548 | 0.5180 | 0.8763 | 0.7450 | 0.4286 |
| fixed_similar | clear | 500 | 500 | 0.7500 | 1.0000 | 0.2400 | 0.3436 | 0.4916 | 0.9774 | 0.9750 | 0.8768 | 0.8888 | 0.3514 | 0.5012 | 0.8708 | 0.7379 | 0.4286 |
| fixed_similar | none | 500 | 500 | 0.7500 | 1.0000 | 0.2400 | 0.3496 | 0.4976 | 0.9698 | 0.9672 | 0.8763 | 0.8889 | 0.3608 | 0.5148 | 0.8759 | 0.7331 | 0.4286 |
| fixed_similar | overall | 1500 | 1500 | 0.7500 | 1.0000 | 0.2400 | 0.3466 | 0.4979 | 0.9700 | 0.9674 | 0.8769 | 0.8900 | 0.3557 | 0.5113 | 0.8743 | 0.7386 | 0.4286 |
| oracle_intent | ambiguous | 500 | 500 | 1.0000 | 1.0000 | 0.0000 | 0.4368 | 0.5836 | 1.0000 | 1.0000 | 0.9914 | 0.9884 | 0.4476 | 0.6020 | 0.9898 | 0.8348 | 1.0000 |
| oracle_intent | clear | 500 | 500 | 1.0000 | 1.0000 | 0.0000 | 0.4364 | 0.5900 | 1.0000 | 1.0000 | 0.9919 | 0.9929 | 0.4470 | 0.6056 | 0.9894 | 0.8393 | 1.0000 |
| oracle_intent | none | 500 | 500 | 1.0000 | 1.0000 | 0.0000 | 0.4448 | 0.5848 | 1.0000 | 1.0000 | 0.9911 | 0.9895 | 0.4606 | 0.6116 | 0.9888 | 0.8255 | 1.0000 |
| oracle_intent | overall | 1500 | 1500 | 1.0000 | 1.0000 | 0.0000 | 0.4393 | 0.5861 | 1.0000 | 1.0000 | 0.9915 | 0.9903 | 0.4517 | 0.6064 | 0.9893 | 0.8332 | 1.0000 |
| profile_similar | ambiguous | 500 | 500 | 0.7500 | 1.0000 | 0.2196 | 0.3464 | 0.5056 | 0.9667 | 0.9640 | 0.8791 | 0.8950 | 0.3546 | 0.5192 | 0.8761 | 0.7476 | 0.4286 |
| profile_similar | clear | 500 | 500 | 0.7500 | 1.0000 | 0.2222 | 0.3440 | 0.4908 | 0.9774 | 0.9750 | 0.8770 | 0.8882 | 0.3518 | 0.5004 | 0.8712 | 0.7373 | 0.4286 |
| profile_similar | none | 500 | 500 | 0.7500 | 1.0000 | 0.2197 | 0.3516 | 0.4988 | 0.9698 | 0.9672 | 0.8776 | 0.8895 | 0.3628 | 0.5160 | 0.8779 | 0.7343 | 0.4286 |
| profile_similar | overall | 1500 | 1500 | 0.7500 | 1.0000 | 0.2205 | 0.3473 | 0.4984 | 0.9713 | 0.9687 | 0.8779 | 0.8909 | 0.3564 | 0.5119 | 0.8751 | 0.7397 | 0.4286 |

## Protocol and limits

- Contract/evaluation 2.0: C is preference inference; D is automatic session direction (formerly D/C).
- B–E are mock scenarios on real papers/silver facets; scores do not establish human relevance or novelty.
- Public scorers receive only observable prefixes and fixed candidate IDs, never labels or latent profiles.
- All methods in each case share candidates and cutoffs; unobserved papers are not labeled negative.
- nDCG gain is 2^grade-1; positive means grade > 0. Ties use ascending paper ID.
- TF-IDF and query parsing are lexical CPU references; parameters are fixed before test.
- A facet-importance MAE exists only for models returning normalized facet importance.
- Oracle_intent alone receives true session directions/importance, in the evaluator; it is a privileged reference.
- Direction macro-F1 pools active similar/different facets across cases; unknown counts as a missed prediction.
- True ignore facets are excluded from direction F1/coverage; unknown is not interpreted as ignore.
- D controls one similar context facet and one similar/different focus facet, across all five facets; arbitrary multi-facet combinations need additional scenarios.
- Intent compliance counts grade=2; grade=1 is related but violates the requested direction.
- Matched exposure pairs control other facets overlap states; this is not a causal claim on real logs.

Per-case labels and metrics: `details.jsonl`; ranked scores: `predictions.jsonl`.
Undefined nDCG/Recall/MRR for cases without positives are excluded from their means;
`defined_cases` in report.json records each metric denominator.
