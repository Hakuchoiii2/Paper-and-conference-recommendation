# Experiment D — CPU methods

Dataset: **synthetic_observation_overlay**, status: **pilot**, evaluation: **d_synthetic_observation_overlay_v1**, cases: **30**.

| Model | Group | Cases | Positive cases | direction_accuracy | direction_coverage | importance_mae | intent_compliance@10 | intent_compliance@5 | mrr@10 | mrr@5 | ndcg@10 | ndcg@5 | precision@10 | precision@5 | recall@10 | recall@5 | direction_macro_f1 |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| direction_behavior__no_observations | ambiguous | 10 | 10 | 0.5000 | 0.5000 | 0.2283 | 0.3400 | 0.4600 | 0.9000 | 0.9000 | 0.7951 | 0.8077 | 0.3400 | 0.4600 | 0.7800 | 0.6400 | 0.4000 |
| direction_behavior__no_observations | clear | 10 | 10 | 0.5000 | 0.5000 | 0.2173 | 0.3100 | 0.4600 | 1.0000 | 1.0000 | 0.8354 | 0.8551 | 0.3200 | 0.4600 | 0.7967 | 0.6733 | 0.4000 |
| direction_behavior__no_observations | none | 10 | 10 | 0.5000 | 0.5000 | 0.2223 | 0.3300 | 0.4400 | 0.9500 | 0.9500 | 0.8611 | 0.8636 | 0.3300 | 0.4400 | 0.8600 | 0.7200 | 0.4000 |
| direction_behavior__no_observations | overall | 30 | 30 | 0.5000 | 0.5000 | 0.2226 | 0.3267 | 0.4533 | 0.9500 | 0.9500 | 0.8305 | 0.8421 | 0.3300 | 0.4533 | 0.8122 | 0.6778 | 0.4000 |
| direction_behavior__synthetic_observations | ambiguous | 10 | 10 | 0.9000 | 0.9500 | 0.2283 | 0.3400 | 0.4600 | 0.9000 | 0.9000 | 0.7951 | 0.8077 | 0.3400 | 0.4600 | 0.7800 | 0.6400 | 0.8589 |
| direction_behavior__synthetic_observations | clear | 10 | 10 | 0.9500 | 0.9500 | 0.2173 | 0.3100 | 0.4600 | 1.0000 | 1.0000 | 0.8354 | 0.8551 | 0.3200 | 0.4600 | 0.7967 | 0.6733 | 0.9444 |
| direction_behavior__synthetic_observations | none | 10 | 10 | 1.0000 | 1.0000 | 0.2223 | 0.3200 | 0.4400 | 0.9500 | 0.9500 | 0.8547 | 0.8636 | 0.3200 | 0.4400 | 0.8500 | 0.7200 | 1.0000 |
| direction_behavior__synthetic_observations | overall | 30 | 30 | 0.9500 | 0.9667 | 0.2226 | 0.3233 | 0.4533 | 0.9500 | 0.9500 | 0.8284 | 0.8421 | 0.3267 | 0.4533 | 0.8089 | 0.6778 | 0.9389 |
| direction_search__no_observations | ambiguous | 10 | 10 | 0.5000 | 0.5000 | 0.2283 | 0.3400 | 0.4600 | 0.9000 | 0.9000 | 0.7951 | 0.8077 | 0.3400 | 0.4600 | 0.7800 | 0.6400 | 0.4000 |
| direction_search__no_observations | clear | 10 | 10 | 1.0000 | 1.0000 | 0.2173 | 0.3100 | 0.4600 | 1.0000 | 1.0000 | 0.8354 | 0.8551 | 0.3200 | 0.4600 | 0.7967 | 0.6733 | 1.0000 |
| direction_search__no_observations | none | 10 | 10 | 0.5000 | 0.5000 | 0.2223 | 0.3300 | 0.4400 | 0.9500 | 0.9500 | 0.8611 | 0.8636 | 0.3300 | 0.4400 | 0.8600 | 0.7200 | 0.4000 |
| direction_search__no_observations | overall | 30 | 30 | 0.6667 | 0.6667 | 0.2226 | 0.3267 | 0.4533 | 0.9500 | 0.9500 | 0.8305 | 0.8421 | 0.3300 | 0.4533 | 0.8122 | 0.6778 | 0.6875 |
| direction_search__synthetic_observations | ambiguous | 10 | 10 | 0.9000 | 0.9500 | 0.2283 | 0.3400 | 0.4600 | 0.9000 | 0.9000 | 0.7951 | 0.8077 | 0.3400 | 0.4600 | 0.7800 | 0.6400 | 0.8589 |
| direction_search__synthetic_observations | clear | 10 | 10 | 1.0000 | 1.0000 | 0.2173 | 0.3100 | 0.4600 | 1.0000 | 1.0000 | 0.8354 | 0.8551 | 0.3200 | 0.4600 | 0.7967 | 0.6733 | 1.0000 |
| direction_search__synthetic_observations | none | 10 | 10 | 1.0000 | 1.0000 | 0.2223 | 0.3200 | 0.4400 | 0.9500 | 0.9500 | 0.8547 | 0.8636 | 0.3200 | 0.4400 | 0.8500 | 0.7200 | 1.0000 |
| direction_search__synthetic_observations | overall | 30 | 30 | 0.9667 | 0.9833 | 0.2226 | 0.3233 | 0.4533 | 0.9500 | 0.9500 | 0.8284 | 0.8421 | 0.3267 | 0.4533 | 0.8089 | 0.6778 | 0.9588 |
| fixed_similar__no_observations | ambiguous | 10 | 10 | 0.7500 | 1.0000 | 0.2400 | 0.3400 | 0.4600 | 0.9000 | 0.9000 | 0.7946 | 0.8077 | 0.3400 | 0.4600 | 0.7800 | 0.6400 | 0.4286 |
| fixed_similar__no_observations | clear | 10 | 10 | 0.7500 | 1.0000 | 0.2400 | 0.3100 | 0.4600 | 1.0000 | 1.0000 | 0.8354 | 0.8551 | 0.3200 | 0.4600 | 0.7967 | 0.6733 | 0.4286 |
| fixed_similar__no_observations | none | 10 | 10 | 0.7500 | 1.0000 | 0.2400 | 0.3300 | 0.4400 | 0.9500 | 0.9500 | 0.8611 | 0.8636 | 0.3300 | 0.4400 | 0.8600 | 0.7200 | 0.4286 |
| fixed_similar__no_observations | overall | 30 | 30 | 0.7500 | 1.0000 | 0.2400 | 0.3267 | 0.4533 | 0.9500 | 0.9500 | 0.8304 | 0.8421 | 0.3300 | 0.4533 | 0.8122 | 0.6778 | 0.4286 |
| fixed_similar__synthetic_observations | ambiguous | 10 | 10 | 0.7500 | 1.0000 | 0.2400 | 0.3400 | 0.4600 | 0.9000 | 0.9000 | 0.7946 | 0.8077 | 0.3400 | 0.4600 | 0.7800 | 0.6400 | 0.4286 |
| fixed_similar__synthetic_observations | clear | 10 | 10 | 0.7500 | 1.0000 | 0.2400 | 0.3100 | 0.4600 | 1.0000 | 1.0000 | 0.8354 | 0.8551 | 0.3200 | 0.4600 | 0.7967 | 0.6733 | 0.4286 |
| fixed_similar__synthetic_observations | none | 10 | 10 | 0.7500 | 1.0000 | 0.2400 | 0.3300 | 0.4400 | 0.9500 | 0.9500 | 0.8611 | 0.8636 | 0.3300 | 0.4400 | 0.8600 | 0.7200 | 0.4286 |
| fixed_similar__synthetic_observations | overall | 30 | 30 | 0.7500 | 1.0000 | 0.2400 | 0.3267 | 0.4533 | 0.9500 | 0.9500 | 0.8304 | 0.8421 | 0.3300 | 0.4533 | 0.8122 | 0.6778 | 0.4286 |
| intent_active_behavior__no_observations | ambiguous | 10 | 10 | 0.5000 | 0.5000 | 0.2283 | 0.3400 | 0.4600 | 0.9000 | 0.9000 | 0.7951 | 0.8077 | 0.3400 | 0.4600 | 0.7800 | 0.6400 | 0.4000 |
| intent_active_behavior__no_observations | clear | 10 | 10 | 0.5000 | 0.5000 | 0.2173 | 0.3100 | 0.4600 | 1.0000 | 1.0000 | 0.8354 | 0.8551 | 0.3200 | 0.4600 | 0.7967 | 0.6733 | 0.4000 |
| intent_active_behavior__no_observations | none | 10 | 10 | 0.5000 | 0.5000 | 0.2223 | 0.3300 | 0.4400 | 0.9500 | 0.9500 | 0.8611 | 0.8636 | 0.3300 | 0.4400 | 0.8600 | 0.7200 | 0.4000 |
| intent_active_behavior__no_observations | overall | 30 | 30 | 0.5000 | 0.5000 | 0.2226 | 0.3267 | 0.4533 | 0.9500 | 0.9500 | 0.8305 | 0.8421 | 0.3300 | 0.4533 | 0.8122 | 0.6778 | 0.4000 |
| intent_active_behavior__synthetic_observations | ambiguous | 10 | 10 | 0.9000 | 0.9500 | 0.0896 | 0.4200 | 0.5000 | 1.0000 | 1.0000 | 0.9471 | 0.9208 | 0.4200 | 0.5000 | 0.9500 | 0.7500 | 0.8589 |
| intent_active_behavior__synthetic_observations | clear | 10 | 10 | 0.9500 | 0.9500 | 0.0562 | 0.4400 | 0.6000 | 1.0000 | 1.0000 | 0.9934 | 1.0000 | 0.4600 | 0.6400 | 0.9900 | 0.8500 | 0.9444 |
| intent_active_behavior__synthetic_observations | none | 10 | 10 | 1.0000 | 1.0000 | 0.0625 | 0.4300 | 0.5600 | 1.0000 | 1.0000 | 0.9821 | 0.9723 | 0.4300 | 0.5600 | 0.9800 | 0.8100 | 1.0000 |
| intent_active_behavior__synthetic_observations | overall | 30 | 30 | 0.9500 | 0.9667 | 0.0694 | 0.4300 | 0.5533 | 1.0000 | 1.0000 | 0.9742 | 0.9644 | 0.4367 | 0.5667 | 0.9733 | 0.8033 | 0.9389 |
| intent_active_search__no_observations | ambiguous | 10 | 10 | 0.5000 | 0.5000 | 0.2283 | 0.3400 | 0.4600 | 0.9000 | 0.9000 | 0.7951 | 0.8077 | 0.3400 | 0.4600 | 0.7800 | 0.6400 | 0.4000 |
| intent_active_search__no_observations | clear | 10 | 10 | 1.0000 | 1.0000 | 0.0380 | 0.4400 | 0.6000 | 1.0000 | 1.0000 | 0.9934 | 1.0000 | 0.4600 | 0.6400 | 0.9900 | 0.8500 | 1.0000 |
| intent_active_search__no_observations | none | 10 | 10 | 0.5000 | 0.5000 | 0.2223 | 0.3300 | 0.4400 | 0.9500 | 0.9500 | 0.8611 | 0.8636 | 0.3300 | 0.4400 | 0.8600 | 0.7200 | 0.4000 |
| intent_active_search__no_observations | overall | 30 | 30 | 0.6667 | 0.6667 | 0.1629 | 0.3700 | 0.5000 | 0.9500 | 0.9500 | 0.8832 | 0.8904 | 0.3767 | 0.5133 | 0.8767 | 0.7367 | 0.6875 |
| intent_active_search__synthetic_observations | ambiguous | 10 | 10 | 0.9000 | 0.9500 | 0.0896 | 0.4200 | 0.5000 | 1.0000 | 1.0000 | 0.9471 | 0.9208 | 0.4200 | 0.5000 | 0.9500 | 0.7500 | 0.8589 |
| intent_active_search__synthetic_observations | clear | 10 | 10 | 1.0000 | 1.0000 | 0.0380 | 0.4400 | 0.6000 | 1.0000 | 1.0000 | 0.9934 | 1.0000 | 0.4600 | 0.6400 | 0.9900 | 0.8500 | 1.0000 |
| intent_active_search__synthetic_observations | none | 10 | 10 | 1.0000 | 1.0000 | 0.0625 | 0.4300 | 0.5600 | 1.0000 | 1.0000 | 0.9821 | 0.9723 | 0.4300 | 0.5600 | 0.9800 | 0.8100 | 1.0000 |
| intent_active_search__synthetic_observations | overall | 30 | 30 | 0.9667 | 0.9833 | 0.0634 | 0.4300 | 0.5533 | 1.0000 | 1.0000 | 0.9742 | 0.9644 | 0.4367 | 0.5667 | 0.9733 | 0.8033 | 0.9588 |
| intent_priority_behavior__no_observations | ambiguous | 10 | 10 | 0.5000 | 0.5000 | 0.2283 | 0.3400 | 0.4600 | 0.9000 | 0.9000 | 0.7951 | 0.8077 | 0.3400 | 0.4600 | 0.7800 | 0.6400 | 0.4000 |
| intent_priority_behavior__no_observations | clear | 10 | 10 | 0.5000 | 0.5000 | 0.2173 | 0.3100 | 0.4600 | 1.0000 | 1.0000 | 0.8354 | 0.8551 | 0.3200 | 0.4600 | 0.7967 | 0.6733 | 0.4000 |
| intent_priority_behavior__no_observations | none | 10 | 10 | 0.5000 | 0.5000 | 0.2223 | 0.3300 | 0.4400 | 0.9500 | 0.9500 | 0.8611 | 0.8636 | 0.3300 | 0.4400 | 0.8600 | 0.7200 | 0.4000 |
| intent_priority_behavior__no_observations | overall | 30 | 30 | 0.5000 | 0.5000 | 0.2226 | 0.3267 | 0.4533 | 0.9500 | 0.9500 | 0.8305 | 0.8421 | 0.3300 | 0.4533 | 0.8122 | 0.6778 | 0.4000 |
| intent_priority_behavior__synthetic_observations | ambiguous | 10 | 10 | 0.9000 | 0.9500 | 0.2283 | 0.4300 | 0.5200 | 1.0000 | 1.0000 | 0.9559 | 0.9339 | 0.4300 | 0.5200 | 0.9600 | 0.7700 | 0.8589 |
| intent_priority_behavior__synthetic_observations | clear | 10 | 10 | 0.9500 | 0.9500 | 0.2173 | 0.4400 | 0.6000 | 1.0000 | 1.0000 | 0.9934 | 1.0000 | 0.4600 | 0.6400 | 0.9900 | 0.8500 | 0.9444 |
| intent_priority_behavior__synthetic_observations | none | 10 | 10 | 1.0000 | 1.0000 | 0.2223 | 0.4500 | 0.6000 | 1.0000 | 1.0000 | 1.0000 | 1.0000 | 0.4500 | 0.6000 | 1.0000 | 0.8500 | 1.0000 |
| intent_priority_behavior__synthetic_observations | overall | 30 | 30 | 0.9500 | 0.9667 | 0.2226 | 0.4400 | 0.5733 | 1.0000 | 1.0000 | 0.9831 | 0.9780 | 0.4467 | 0.5867 | 0.9833 | 0.8233 | 0.9389 |
| intent_priority_search__no_observations | ambiguous | 10 | 10 | 0.5000 | 0.5000 | 0.2283 | 0.3400 | 0.4600 | 0.9000 | 0.9000 | 0.7951 | 0.8077 | 0.3400 | 0.4600 | 0.7800 | 0.6400 | 0.4000 |
| intent_priority_search__no_observations | clear | 10 | 10 | 1.0000 | 1.0000 | 0.2173 | 0.4500 | 0.6000 | 1.0000 | 1.0000 | 1.0000 | 1.0000 | 0.4700 | 0.6400 | 1.0000 | 0.8500 | 1.0000 |
| intent_priority_search__no_observations | none | 10 | 10 | 0.5000 | 0.5000 | 0.2223 | 0.3300 | 0.4400 | 0.9500 | 0.9500 | 0.8611 | 0.8636 | 0.3300 | 0.4400 | 0.8600 | 0.7200 | 0.4000 |
| intent_priority_search__no_observations | overall | 30 | 30 | 0.6667 | 0.6667 | 0.2226 | 0.3733 | 0.5000 | 0.9500 | 0.9500 | 0.8854 | 0.8904 | 0.3800 | 0.5133 | 0.8800 | 0.7367 | 0.6875 |
| intent_priority_search__synthetic_observations | ambiguous | 10 | 10 | 0.9000 | 0.9500 | 0.2283 | 0.4300 | 0.5200 | 1.0000 | 1.0000 | 0.9559 | 0.9339 | 0.4300 | 0.5200 | 0.9600 | 0.7700 | 0.8589 |
| intent_priority_search__synthetic_observations | clear | 10 | 10 | 1.0000 | 1.0000 | 0.2173 | 0.4500 | 0.6000 | 1.0000 | 1.0000 | 1.0000 | 1.0000 | 0.4700 | 0.6400 | 1.0000 | 0.8500 | 1.0000 |
| intent_priority_search__synthetic_observations | none | 10 | 10 | 1.0000 | 1.0000 | 0.2223 | 0.4500 | 0.6000 | 1.0000 | 1.0000 | 1.0000 | 1.0000 | 0.4500 | 0.6000 | 1.0000 | 0.8500 | 1.0000 |
| intent_priority_search__synthetic_observations | overall | 30 | 30 | 0.9667 | 0.9833 | 0.2226 | 0.4433 | 0.5733 | 1.0000 | 1.0000 | 0.9853 | 0.9780 | 0.4500 | 0.5867 | 0.9867 | 0.8233 | 0.9588 |
| oracle_intent__no_observations | ambiguous | 10 | 10 | 1.0000 | 1.0000 | 0.0000 | 0.4400 | 0.5600 | 1.0000 | 1.0000 | 0.9863 | 0.9699 | 0.4400 | 0.5600 | 0.9900 | 0.8100 | 1.0000 |
| oracle_intent__no_observations | clear | 10 | 10 | 1.0000 | 1.0000 | 0.0000 | 0.4400 | 0.6000 | 1.0000 | 1.0000 | 0.9934 | 1.0000 | 0.4600 | 0.6400 | 0.9900 | 0.8500 | 1.0000 |
| oracle_intent__no_observations | none | 10 | 10 | 1.0000 | 1.0000 | 0.0000 | 0.4500 | 0.5600 | 1.0000 | 1.0000 | 0.9951 | 0.9723 | 0.4500 | 0.5600 | 1.0000 | 0.8100 | 1.0000 |
| oracle_intent__no_observations | overall | 30 | 30 | 1.0000 | 1.0000 | 0.0000 | 0.4433 | 0.5733 | 1.0000 | 1.0000 | 0.9916 | 0.9807 | 0.4500 | 0.5867 | 0.9933 | 0.8233 | 1.0000 |
| oracle_intent__synthetic_observations | ambiguous | 10 | 10 | 1.0000 | 1.0000 | 0.0000 | 0.4400 | 0.5600 | 1.0000 | 1.0000 | 0.9863 | 0.9699 | 0.4400 | 0.5600 | 0.9900 | 0.8100 | 1.0000 |
| oracle_intent__synthetic_observations | clear | 10 | 10 | 1.0000 | 1.0000 | 0.0000 | 0.4400 | 0.6000 | 1.0000 | 1.0000 | 0.9934 | 1.0000 | 0.4600 | 0.6400 | 0.9900 | 0.8500 | 1.0000 |
| oracle_intent__synthetic_observations | none | 10 | 10 | 1.0000 | 1.0000 | 0.0000 | 0.4500 | 0.5600 | 1.0000 | 1.0000 | 0.9951 | 0.9723 | 0.4500 | 0.5600 | 1.0000 | 0.8100 | 1.0000 |
| oracle_intent__synthetic_observations | overall | 30 | 30 | 1.0000 | 1.0000 | 0.0000 | 0.4433 | 0.5733 | 1.0000 | 1.0000 | 0.9916 | 0.9807 | 0.4500 | 0.5867 | 0.9933 | 0.8233 | 1.0000 |
| profile_similar__no_observations | ambiguous | 10 | 10 | 0.7500 | 1.0000 | 0.2283 | 0.3400 | 0.4600 | 0.9000 | 0.9000 | 0.7951 | 0.8077 | 0.3400 | 0.4600 | 0.7800 | 0.6400 | 0.4286 |
| profile_similar__no_observations | clear | 10 | 10 | 0.7500 | 1.0000 | 0.2173 | 0.3100 | 0.4600 | 1.0000 | 1.0000 | 0.8354 | 0.8551 | 0.3200 | 0.4600 | 0.7967 | 0.6733 | 0.4286 |
| profile_similar__no_observations | none | 10 | 10 | 0.7500 | 1.0000 | 0.2223 | 0.3300 | 0.4400 | 0.9500 | 0.9500 | 0.8611 | 0.8636 | 0.3300 | 0.4400 | 0.8600 | 0.7200 | 0.4286 |
| profile_similar__no_observations | overall | 30 | 30 | 0.7500 | 1.0000 | 0.2226 | 0.3267 | 0.4533 | 0.9500 | 0.9500 | 0.8305 | 0.8421 | 0.3300 | 0.4533 | 0.8122 | 0.6778 | 0.4286 |
| profile_similar__synthetic_observations | ambiguous | 10 | 10 | 0.7500 | 1.0000 | 0.2283 | 0.3400 | 0.4600 | 0.9000 | 0.9000 | 0.7951 | 0.8077 | 0.3400 | 0.4600 | 0.7800 | 0.6400 | 0.4286 |
| profile_similar__synthetic_observations | clear | 10 | 10 | 0.7500 | 1.0000 | 0.2173 | 0.3100 | 0.4600 | 1.0000 | 1.0000 | 0.8354 | 0.8551 | 0.3200 | 0.4600 | 0.7967 | 0.6733 | 0.4286 |
| profile_similar__synthetic_observations | none | 10 | 10 | 0.7500 | 1.0000 | 0.2223 | 0.3300 | 0.4400 | 0.9500 | 0.9500 | 0.8611 | 0.8636 | 0.3300 | 0.4400 | 0.8600 | 0.7200 | 0.4286 |
| profile_similar__synthetic_observations | overall | 30 | 30 | 0.7500 | 1.0000 | 0.2226 | 0.3267 | 0.4533 | 0.9500 | 0.9500 | 0.8305 | 0.8421 | 0.3300 | 0.4533 | 0.8122 | 0.6778 | 0.4286 |

## Protocol and limits

- Real source anchors, candidates, labels, queries and C profiles are unchanged.
- Synthetic observations are controlled facet constructions, NOT real papers or A silver.
- Repeated matched synthetic profiles are feedback draws, not independent real-paper evidence.
- Candidate TF-IDF is frozen on original real facets in both conditions; no IDF confound.
- No-observation vs synthetic-observation conditions share every input except observations/reactions.
- This pilot establishes behavior under the specified simulator, not human relevance or novelty.
- Hidden intent is used by simulator and evaluator only; public scorer receives no hidden fields.
- Development diagnostic; no training, tuning or held-out generalization claim.
- Original baseline predictions preserved; same candidates, labels and cutoffs.
- Estimator directions/confidence unchanged; only ranking policy changes.
- Priority tiers use observed concept overlap; active policy masks C weights.
- Focus chosen from unique strongest non-context observed direction; ties/unknown fall back.
- Priority can bypass missing-facet penalties on inactive facets; not a semantic encoder gain.

Per-case labels and metrics: `details.jsonl`; ranked scores: `predictions.jsonl`.
Undefined nDCG/Recall/MRR for cases without positives are excluded from their means;
`defined_cases` in report.json records each metric denominator.
