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
| hybrid_active_behavior__no_observations | ambiguous | 10 | 10 | 0.5000 | 0.5000 | 0.2283 | 0.3400 | 0.4600 | 0.9000 | 0.9000 | 0.7951 | 0.8077 | 0.3400 | 0.4600 | 0.7800 | 0.6400 | 0.4000 |
| hybrid_active_behavior__no_observations | clear | 10 | 10 | 0.5000 | 0.5000 | 0.2173 | 0.3100 | 0.4600 | 1.0000 | 1.0000 | 0.8354 | 0.8551 | 0.3200 | 0.4600 | 0.7967 | 0.6733 | 0.4000 |
| hybrid_active_behavior__no_observations | none | 10 | 10 | 0.5000 | 0.5000 | 0.2223 | 0.3300 | 0.4400 | 0.9500 | 0.9500 | 0.8611 | 0.8636 | 0.3300 | 0.4400 | 0.8600 | 0.7200 | 0.4000 |
| hybrid_active_behavior__no_observations | overall | 30 | 30 | 0.5000 | 0.5000 | 0.2226 | 0.3267 | 0.4533 | 0.9500 | 0.9500 | 0.8305 | 0.8421 | 0.3300 | 0.4533 | 0.8122 | 0.6778 | 0.4000 |
| hybrid_active_behavior__synthetic_observations | ambiguous | 10 | 10 | 0.9000 | 0.9500 | 0.0896 | 0.4200 | 0.5000 | 1.0000 | 1.0000 | 0.9460 | 0.9208 | 0.4200 | 0.5000 | 0.9500 | 0.7500 | 0.8589 |
| hybrid_active_behavior__synthetic_observations | clear | 10 | 10 | 0.9500 | 0.9500 | 0.0562 | 0.4400 | 0.5800 | 1.0000 | 1.0000 | 0.9910 | 0.9869 | 0.4600 | 0.6200 | 0.9900 | 0.8300 | 0.9444 |
| hybrid_active_behavior__synthetic_observations | none | 10 | 10 | 1.0000 | 1.0000 | 0.0625 | 0.4200 | 0.5600 | 1.0000 | 1.0000 | 0.9750 | 0.9723 | 0.4200 | 0.5600 | 0.9700 | 0.8100 | 1.0000 |
| hybrid_active_behavior__synthetic_observations | overall | 30 | 30 | 0.9500 | 0.9667 | 0.0694 | 0.4267 | 0.5467 | 1.0000 | 1.0000 | 0.9706 | 0.9600 | 0.4333 | 0.5600 | 0.9700 | 0.7967 | 0.9389 |
| hybrid_active_search__no_observations | ambiguous | 10 | 10 | 0.5000 | 0.5000 | 0.2283 | 0.3400 | 0.4600 | 0.9000 | 0.9000 | 0.7951 | 0.8077 | 0.3400 | 0.4600 | 0.7800 | 0.6400 | 0.4000 |
| hybrid_active_search__no_observations | clear | 10 | 10 | 1.0000 | 1.0000 | 0.0380 | 0.4400 | 0.5800 | 1.0000 | 1.0000 | 0.9910 | 0.9869 | 0.4600 | 0.6200 | 0.9900 | 0.8300 | 1.0000 |
| hybrid_active_search__no_observations | none | 10 | 10 | 0.5000 | 0.5000 | 0.2223 | 0.3300 | 0.4400 | 0.9500 | 0.9500 | 0.8611 | 0.8636 | 0.3300 | 0.4400 | 0.8600 | 0.7200 | 0.4000 |
| hybrid_active_search__no_observations | overall | 30 | 30 | 0.6667 | 0.6667 | 0.1629 | 0.3700 | 0.4933 | 0.9500 | 0.9500 | 0.8824 | 0.8860 | 0.3767 | 0.5067 | 0.8767 | 0.7300 | 0.6875 |
| hybrid_active_search__synthetic_observations | ambiguous | 10 | 10 | 0.9000 | 0.9500 | 0.0896 | 0.4200 | 0.5000 | 1.0000 | 1.0000 | 0.9460 | 0.9208 | 0.4200 | 0.5000 | 0.9500 | 0.7500 | 0.8589 |
| hybrid_active_search__synthetic_observations | clear | 10 | 10 | 1.0000 | 1.0000 | 0.0380 | 0.4400 | 0.5800 | 1.0000 | 1.0000 | 0.9910 | 0.9869 | 0.4600 | 0.6200 | 0.9900 | 0.8300 | 1.0000 |
| hybrid_active_search__synthetic_observations | none | 10 | 10 | 1.0000 | 1.0000 | 0.0625 | 0.4200 | 0.5600 | 1.0000 | 1.0000 | 0.9750 | 0.9723 | 0.4200 | 0.5600 | 0.9700 | 0.8100 | 1.0000 |
| hybrid_active_search__synthetic_observations | overall | 30 | 30 | 0.9667 | 0.9833 | 0.0634 | 0.4267 | 0.5467 | 1.0000 | 1.0000 | 0.9706 | 0.9600 | 0.4333 | 0.5600 | 0.9700 | 0.7967 | 0.9588 |
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
| semantic_active_behavior__no_observations | ambiguous | 10 | 10 | 0.5000 | 0.5000 | 0.2283 | 0.3400 | 0.4600 | 0.9000 | 0.9000 | 0.7951 | 0.8077 | 0.3400 | 0.4600 | 0.7800 | 0.6400 | 0.4000 |
| semantic_active_behavior__no_observations | clear | 10 | 10 | 0.5000 | 0.5000 | 0.2173 | 0.3100 | 0.4600 | 1.0000 | 1.0000 | 0.8354 | 0.8551 | 0.3200 | 0.4600 | 0.7967 | 0.6733 | 0.4000 |
| semantic_active_behavior__no_observations | none | 10 | 10 | 0.5000 | 0.5000 | 0.2223 | 0.3300 | 0.4400 | 0.9500 | 0.9500 | 0.8611 | 0.8636 | 0.3300 | 0.4400 | 0.8600 | 0.7200 | 0.4000 |
| semantic_active_behavior__no_observations | overall | 30 | 30 | 0.5000 | 0.5000 | 0.2226 | 0.3267 | 0.4533 | 0.9500 | 0.9500 | 0.8305 | 0.8421 | 0.3300 | 0.4533 | 0.8122 | 0.6778 | 0.4000 |
| semantic_active_behavior__synthetic_observations | ambiguous | 10 | 10 | 0.9000 | 0.9500 | 0.0896 | 0.3900 | 0.4400 | 0.9500 | 0.9500 | 0.9028 | 0.8592 | 0.3900 | 0.4400 | 0.9100 | 0.7200 | 0.8589 |
| semantic_active_behavior__synthetic_observations | clear | 10 | 10 | 0.9500 | 0.9500 | 0.0562 | 0.4300 | 0.5200 | 0.9200 | 0.9200 | 0.9438 | 0.9131 | 0.4500 | 0.5600 | 0.9800 | 0.7700 | 0.9444 |
| semantic_active_behavior__synthetic_observations | none | 10 | 10 | 1.0000 | 1.0000 | 0.0625 | 0.3900 | 0.5600 | 1.0000 | 1.0000 | 0.9494 | 0.9723 | 0.3900 | 0.5600 | 0.9300 | 0.8100 | 1.0000 |
| semantic_active_behavior__synthetic_observations | overall | 30 | 30 | 0.9500 | 0.9667 | 0.0694 | 0.4033 | 0.5067 | 0.9567 | 0.9567 | 0.9320 | 0.9148 | 0.4100 | 0.5200 | 0.9400 | 0.7667 | 0.9389 |
| semantic_active_search__no_observations | ambiguous | 10 | 10 | 0.5000 | 0.5000 | 0.2283 | 0.3400 | 0.4600 | 0.9000 | 0.9000 | 0.7951 | 0.8077 | 0.3400 | 0.4600 | 0.7800 | 0.6400 | 0.4000 |
| semantic_active_search__no_observations | clear | 10 | 10 | 1.0000 | 1.0000 | 0.0380 | 0.4300 | 0.5200 | 0.9200 | 0.9200 | 0.9438 | 0.9131 | 0.4500 | 0.5600 | 0.9800 | 0.7700 | 1.0000 |
| semantic_active_search__no_observations | none | 10 | 10 | 0.5000 | 0.5000 | 0.2223 | 0.3300 | 0.4400 | 0.9500 | 0.9500 | 0.8611 | 0.8636 | 0.3300 | 0.4400 | 0.8600 | 0.7200 | 0.4000 |
| semantic_active_search__no_observations | overall | 30 | 30 | 0.6667 | 0.6667 | 0.1629 | 0.3667 | 0.4733 | 0.9233 | 0.9233 | 0.8666 | 0.8615 | 0.3733 | 0.4867 | 0.8733 | 0.7100 | 0.6875 |
| semantic_active_search__synthetic_observations | ambiguous | 10 | 10 | 0.9000 | 0.9500 | 0.0896 | 0.3900 | 0.4400 | 0.9500 | 0.9500 | 0.9028 | 0.8592 | 0.3900 | 0.4400 | 0.9100 | 0.7200 | 0.8589 |
| semantic_active_search__synthetic_observations | clear | 10 | 10 | 1.0000 | 1.0000 | 0.0380 | 0.4300 | 0.5200 | 0.9200 | 0.9200 | 0.9438 | 0.9131 | 0.4500 | 0.5600 | 0.9800 | 0.7700 | 1.0000 |
| semantic_active_search__synthetic_observations | none | 10 | 10 | 1.0000 | 1.0000 | 0.0625 | 0.3900 | 0.5600 | 1.0000 | 1.0000 | 0.9494 | 0.9723 | 0.3900 | 0.5600 | 0.9300 | 0.8100 | 1.0000 |
| semantic_active_search__synthetic_observations | overall | 30 | 30 | 0.9667 | 0.9833 | 0.0634 | 0.4033 | 0.5067 | 0.9567 | 0.9567 | 0.9320 | 0.9148 | 0.4100 | 0.5200 | 0.9400 | 0.7667 | 0.9588 |
| semantic_full_behavior__no_observations | ambiguous | 10 | 10 | 0.5000 | 0.5000 | 0.2283 | 0.3100 | 0.4200 | 0.7833 | 0.7833 | 0.7357 | 0.7398 | 0.3100 | 0.4200 | 0.7400 | 0.6200 | 0.4000 |
| semantic_full_behavior__no_observations | clear | 10 | 10 | 0.5000 | 0.5000 | 0.2173 | 0.2900 | 0.4000 | 0.8750 | 0.8750 | 0.7595 | 0.7620 | 0.3000 | 0.4000 | 0.7567 | 0.6133 | 0.4000 |
| semantic_full_behavior__no_observations | none | 10 | 10 | 0.5000 | 0.5000 | 0.2223 | 0.3100 | 0.4400 | 0.9500 | 0.9500 | 0.8428 | 0.8636 | 0.3100 | 0.4400 | 0.8300 | 0.7200 | 0.4000 |
| semantic_full_behavior__no_observations | overall | 30 | 30 | 0.5000 | 0.5000 | 0.2226 | 0.3033 | 0.4200 | 0.8694 | 0.8694 | 0.7793 | 0.7885 | 0.3067 | 0.4200 | 0.7756 | 0.6511 | 0.4000 |
| semantic_full_behavior__synthetic_observations | ambiguous | 10 | 10 | 0.9000 | 0.9500 | 0.2283 | 0.3100 | 0.4200 | 0.7833 | 0.7833 | 0.7342 | 0.7384 | 0.3100 | 0.4200 | 0.7400 | 0.6200 | 0.8589 |
| semantic_full_behavior__synthetic_observations | clear | 10 | 10 | 0.9500 | 0.9500 | 0.2173 | 0.2900 | 0.3800 | 0.9200 | 0.9200 | 0.7632 | 0.7599 | 0.3000 | 0.3800 | 0.7567 | 0.5933 | 0.9444 |
| semantic_full_behavior__synthetic_observations | none | 10 | 10 | 1.0000 | 1.0000 | 0.2223 | 0.3100 | 0.4400 | 0.9500 | 0.9500 | 0.8428 | 0.8636 | 0.3100 | 0.4400 | 0.8300 | 0.7200 | 1.0000 |
| semantic_full_behavior__synthetic_observations | overall | 30 | 30 | 0.9500 | 0.9667 | 0.2226 | 0.3033 | 0.4133 | 0.8844 | 0.8844 | 0.7801 | 0.7873 | 0.3067 | 0.4133 | 0.7756 | 0.6444 | 0.9389 |
| semantic_full_search__no_observations | ambiguous | 10 | 10 | 0.5000 | 0.5000 | 0.2283 | 0.3100 | 0.4200 | 0.7833 | 0.7833 | 0.7357 | 0.7398 | 0.3100 | 0.4200 | 0.7400 | 0.6200 | 0.4000 |
| semantic_full_search__no_observations | clear | 10 | 10 | 1.0000 | 1.0000 | 0.2173 | 0.2900 | 0.3800 | 0.9200 | 0.9200 | 0.7635 | 0.7599 | 0.3000 | 0.3800 | 0.7567 | 0.5933 | 1.0000 |
| semantic_full_search__no_observations | none | 10 | 10 | 0.5000 | 0.5000 | 0.2223 | 0.3100 | 0.4400 | 0.9500 | 0.9500 | 0.8428 | 0.8636 | 0.3100 | 0.4400 | 0.8300 | 0.7200 | 0.4000 |
| semantic_full_search__no_observations | overall | 30 | 30 | 0.6667 | 0.6667 | 0.2226 | 0.3033 | 0.4133 | 0.8844 | 0.8844 | 0.7806 | 0.7878 | 0.3067 | 0.4133 | 0.7756 | 0.6444 | 0.6875 |
| semantic_full_search__synthetic_observations | ambiguous | 10 | 10 | 0.9000 | 0.9500 | 0.2283 | 0.3100 | 0.4200 | 0.7833 | 0.7833 | 0.7342 | 0.7384 | 0.3100 | 0.4200 | 0.7400 | 0.6200 | 0.8589 |
| semantic_full_search__synthetic_observations | clear | 10 | 10 | 1.0000 | 1.0000 | 0.2173 | 0.2900 | 0.3800 | 0.9200 | 0.9200 | 0.7635 | 0.7599 | 0.3000 | 0.3800 | 0.7567 | 0.5933 | 1.0000 |
| semantic_full_search__synthetic_observations | none | 10 | 10 | 1.0000 | 1.0000 | 0.2223 | 0.3100 | 0.4400 | 0.9500 | 0.9500 | 0.8428 | 0.8636 | 0.3100 | 0.4400 | 0.8300 | 0.7200 | 1.0000 |
| semantic_full_search__synthetic_observations | overall | 30 | 30 | 0.9667 | 0.9833 | 0.2226 | 0.3033 | 0.4133 | 0.8844 | 0.8844 | 0.7802 | 0.7873 | 0.3067 | 0.4133 | 0.7756 | 0.6444 | 0.9588 |

## Protocol and limits

- Real source anchors, candidates, labels, queries and C profiles are unchanged.
- Synthetic observations are controlled facet constructions, NOT real papers or A silver.
- Repeated matched synthetic profiles are feedback draws, not independent real-paper evidence.
- Candidate TF-IDF is frozen on original real facets in both conditions; no IDF confound.
- No-observation vs synthetic-observation conditions share every input except observations/reactions.
- This pilot establishes behavior under the specified simulator, not human relevance or novelty.
- Hidden intent is used by simulator and evaluator only; public scorer receives no hidden fields.
- Development diagnostic, frozen all-MiniLM-L6-v2; no fine-tuning or label-based selection.
- Directions and confidence unchanged. Original predictions and lexical context gate preserved.
- Full dense changes representation only; dense active and fixed 50/50 hybrid compare with lexical active.
- Unknown/tied focus falls back exactly in active policies; dense full does not require focus.
- All model and temporary caches configured in data/exp_d/model before library imports.

Per-case labels and metrics: `details.jsonl`; ranked scores: `predictions.jsonl`.
Undefined nDCG/Recall/MRR for cases without positives are excluded from their means;
`defined_cases` in report.json records each metric denominator.
