# Eight methods under one common ranking policy

Exploratory selection on the same previously inspected mock pilot; not an independent test.
Dataset, original estimators, C weights and intent_scores unchanged. The shared activation policy changes ranking behavior for every row.
Unique inferred focus: context+focus active, other facets ignore. Missing/ambiguous focus: explicit profile-similar fallback.
Accuracy/coverage use raw predictions BEFORE ranking fallback. No hidden focus, weights or labels enter any method.

| Method | Direction accuracy | Joint accuracy | Coverage | nDCG@10 | Grade 2 at rank 1 |
|---|---:|---:|---:|---:|---:|
| fixed_similar | 50.00% | 0.00% | 100.00% | 0.8029 | 50.00% |
| profile_similar | 50.00% | 0.00% | 100.00% | 0.8019 | 50.00% |
| query_only | 33.33% | 33.33% | 33.33% | 0.8623 | 66.44% |
| direction_behavior | 95.83% | 95.83% | 96.80% | 0.9597 | 93.63% |
| direction_search | 96.91% | 96.91% | 97.84% | 0.9632 | 94.56% |
| vote | 91.74% | 91.74% | 92.05% | 0.9523 | 91.59% |
| bayes_h | 91.51% | 91.51% | 91.82% | 0.9518 | 91.36% |
| ordinal_intent | 81.13% | 81.13% | 81.13% | 0.9374 | 87.00% |

Ordinal-Intent uses graded differences including ties and marginalizes a fixed strength grid. It is not trained or calibrated.
The neutral ordinal likelihood and equal rank spacing are assumptions, not the known mock generator likelihood.
Shared scorer/adapter prevents a ranking-policy benefit from being attributed only to a new estimator.
fixed_similar retains its original uniform weights; all other methods share frozen C weights.
Grouped results separate real-only and mixed candidate pools, query modes and feedback noise.
Paired intervals resample the 12 anchor workgroups; repeats are not treated as independent sessions.
Intervals describe this pilot and do not correct post-result model selection. No thresholds were searched in this run.
