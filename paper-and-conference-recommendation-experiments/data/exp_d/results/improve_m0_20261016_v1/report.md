# D: development reranking trial

Same saved public predictions, inputs and evaluator; no training or parameter search.
This is a development diagnostic, not a held-out final evaluation.

| Condition | Method | Baseline | Delta nDCG@10 | Delta compliance@5 | Fallback cases |
|---|---|---|---:|---:|---:|
| canonical | intent_active_behavior | direction_behavior | +0.0000 | +0.0000 | 1500 |
| canonical | intent_active_search | direction_search | +0.0381 | +0.0325 | 1000 |
| canonical | intent_priority_behavior | direction_behavior | +0.0000 | +0.0000 | 1500 |
| canonical | intent_priority_search | direction_search | +0.0409 | +0.0359 | 1000 |
| seed_42_noise_0.2 | intent_active_behavior__no_observations | direction_behavior__no_observations | +0.0000 | +0.0000 | 30 |
| seed_42_noise_0.2 | intent_active_behavior__synthetic_observations | direction_behavior__synthetic_observations | +0.1588 | +0.1200 | 0 |
| seed_42_noise_0.2 | intent_active_search__no_observations | direction_search__no_observations | +0.0526 | +0.0467 | 20 |
| seed_42_noise_0.2 | intent_active_search__synthetic_observations | direction_search__synthetic_observations | +0.1588 | +0.1200 | 0 |
| seed_42_noise_0.2 | intent_priority_behavior__no_observations | direction_behavior__no_observations | +0.0000 | +0.0000 | 30 |
| seed_42_noise_0.2 | intent_priority_behavior__synthetic_observations | direction_behavior__synthetic_observations | +0.1716 | +0.1467 | 0 |
| seed_42_noise_0.2 | intent_priority_search__no_observations | direction_search__no_observations | +0.0549 | +0.0467 | 20 |
| seed_42_noise_0.2 | intent_priority_search__synthetic_observations | direction_search__synthetic_observations | +0.1716 | +0.1467 | 0 |
| seed_42_noise_0.5 | intent_active_behavior__no_observations | direction_behavior__no_observations | +0.0000 | +0.0000 | 30 |
| seed_42_noise_0.5 | intent_active_behavior__synthetic_observations | direction_behavior__synthetic_observations | +0.1026 | +0.0733 | 4 |
| seed_42_noise_0.5 | intent_active_search__no_observations | direction_search__no_observations | +0.0526 | +0.0467 | 20 |
| seed_42_noise_0.5 | intent_active_search__synthetic_observations | direction_search__synthetic_observations | +0.1213 | +0.1000 | 2 |
| seed_42_noise_0.5 | intent_priority_behavior__no_observations | direction_behavior__no_observations | +0.0000 | +0.0000 | 30 |
| seed_42_noise_0.5 | intent_priority_behavior__synthetic_observations | direction_behavior__synthetic_observations | +0.1335 | +0.0933 | 4 |
| seed_42_noise_0.5 | intent_priority_search__no_observations | direction_search__no_observations | +0.0549 | +0.0467 | 20 |
| seed_42_noise_0.5 | intent_priority_search__synthetic_observations | direction_search__synthetic_observations | +0.1522 | +0.1200 | 2 |
| seed_43_noise_0.2 | intent_active_behavior__no_observations | direction_behavior__no_observations | +0.0000 | +0.0000 | 30 |
| seed_43_noise_0.2 | intent_active_behavior__synthetic_observations | direction_behavior__synthetic_observations | +0.1588 | +0.1200 | 0 |
| seed_43_noise_0.2 | intent_active_search__no_observations | direction_search__no_observations | +0.0526 | +0.0467 | 20 |
| seed_43_noise_0.2 | intent_active_search__synthetic_observations | direction_search__synthetic_observations | +0.1588 | +0.1200 | 0 |
| seed_43_noise_0.2 | intent_priority_behavior__no_observations | direction_behavior__no_observations | +0.0000 | +0.0000 | 30 |
| seed_43_noise_0.2 | intent_priority_behavior__synthetic_observations | direction_behavior__synthetic_observations | +0.1716 | +0.1467 | 0 |
| seed_43_noise_0.2 | intent_priority_search__no_observations | direction_search__no_observations | +0.0549 | +0.0467 | 20 |
| seed_43_noise_0.2 | intent_priority_search__synthetic_observations | direction_search__synthetic_observations | +0.1716 | +0.1467 | 0 |
| seed_43_noise_0.5 | intent_active_behavior__no_observations | direction_behavior__no_observations | +0.0000 | +0.0000 | 30 |
| seed_43_noise_0.5 | intent_active_behavior__synthetic_observations | direction_behavior__synthetic_observations | +0.1588 | +0.1200 | 0 |
| seed_43_noise_0.5 | intent_active_search__no_observations | direction_search__no_observations | +0.0526 | +0.0467 | 20 |
| seed_43_noise_0.5 | intent_active_search__synthetic_observations | direction_search__synthetic_observations | +0.1588 | +0.1200 | 0 |
| seed_43_noise_0.5 | intent_priority_behavior__no_observations | direction_behavior__no_observations | +0.0000 | +0.0000 | 30 |
| seed_43_noise_0.5 | intent_priority_behavior__synthetic_observations | direction_behavior__synthetic_observations | +0.1716 | +0.1467 | 0 |
| seed_43_noise_0.5 | intent_priority_search__no_observations | direction_search__no_observations | +0.0549 | +0.0467 | 20 |
| seed_43_noise_0.5 | intent_priority_search__synthetic_observations | direction_search__synthetic_observations | +0.1716 | +0.1467 | 0 |
| seed_44_noise_0.2 | intent_active_behavior__no_observations | direction_behavior__no_observations | +0.0000 | +0.0000 | 30 |
| seed_44_noise_0.2 | intent_active_behavior__synthetic_observations | direction_behavior__synthetic_observations | +0.1588 | +0.1200 | 0 |
| seed_44_noise_0.2 | intent_active_search__no_observations | direction_search__no_observations | +0.0526 | +0.0467 | 20 |
| seed_44_noise_0.2 | intent_active_search__synthetic_observations | direction_search__synthetic_observations | +0.1588 | +0.1200 | 0 |
| seed_44_noise_0.2 | intent_priority_behavior__no_observations | direction_behavior__no_observations | +0.0000 | +0.0000 | 30 |
| seed_44_noise_0.2 | intent_priority_behavior__synthetic_observations | direction_behavior__synthetic_observations | +0.1716 | +0.1467 | 0 |
| seed_44_noise_0.2 | intent_priority_search__no_observations | direction_search__no_observations | +0.0549 | +0.0467 | 20 |
| seed_44_noise_0.2 | intent_priority_search__synthetic_observations | direction_search__synthetic_observations | +0.1716 | +0.1467 | 0 |
| seed_44_noise_0.5 | intent_active_behavior__no_observations | direction_behavior__no_observations | +0.0000 | +0.0000 | 30 |
| seed_44_noise_0.5 | intent_active_behavior__synthetic_observations | direction_behavior__synthetic_observations | +0.1458 | +0.1000 | 2 |
| seed_44_noise_0.5 | intent_active_search__no_observations | direction_search__no_observations | +0.0526 | +0.0467 | 20 |
| seed_44_noise_0.5 | intent_active_search__synthetic_observations | direction_search__synthetic_observations | +0.1458 | +0.1000 | 1 |
| seed_44_noise_0.5 | intent_priority_behavior__no_observations | direction_behavior__no_observations | +0.0000 | +0.0000 | 30 |
| seed_44_noise_0.5 | intent_priority_behavior__synthetic_observations | direction_behavior__synthetic_observations | +0.1547 | +0.1200 | 2 |
| seed_44_noise_0.5 | intent_priority_search__no_observations | direction_search__no_observations | +0.0549 | +0.0467 | 20 |
| seed_44_noise_0.5 | intent_priority_search__synthetic_observations | direction_search__synthetic_observations | +0.1569 | +0.1200 | 1 |
