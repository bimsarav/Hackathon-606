# Reward Preference Model: Selection and Hyperparameter Tuning

Tool: `backend/tools/reward_model_selection.py`. Re-running the tool reproduces the raw results. Method: baseline first, candidates compared, controlled tuning, decision on validation results.

> **SYNTHETIC DATA.** The outcomes are simulated (see [reward-model-card.md](reward-model-card.md)). This run measures how well each model recovers the assumed behaviour, not how real customers behave.

## Protocol
- 300,000 simulated offers for 111,503 real passenger profiles. Whole passengers are never split between train and test.
- **Final test:** 20% of the passengers (59,312 offers), scored once at the end.
- **Validation:** the other 80% in 4 grouped folds. All comparison and tuning used these only.
- **Selection metric:** mean log-loss (lower is better). The reward plan uses the probabilities themselves, so calibration matters more than ranking. AUC and Brier are shown too.
- Optuna (TPE, seed 7): 40 trials for LightGBM and 25 for XGBoost.
- Because the simulator's own probability is known, the **oracle** (the best any model could score) is reported.

## Validation results (mean of the folds)
| Model | Log-loss | Brier | AUC |
|---|---|---|---|
| LightGBM, tuned | 0.6153 | 0.2133 | 0.7016 |
| CatBoost, default | 0.6153 | 0.2134 | 0.7016 |
| LightGBM, current settings | 0.6157 | 0.2135 | 0.7012 |
| XGBoost, tuned | 0.6157 | 0.2135 | 0.7012 |
| XGBoost, default | 0.6161 | 0.2137 | 0.7005 |
| random forest | 0.6179 | 0.2145 | 0.6982 |
| logistic regression | 0.6381 | 0.2235 | 0.6619 |
| type average (baseline) | 0.6551 | 0.2314 | 0.6126 |

## Final test (scored once)
| Model | AUC | Brier | Log-loss |
|---|---|---|---|
| type average (baseline) | 0.6128 | 0.2315 | 0.6552 |
| proxy rules (first version) | 0.6666 | n/a | n/a |
| logistic regression | 0.6615 | 0.2237 | 0.6384 |
| LightGBM, previous settings | 0.7018 | 0.2134 | 0.6151 |
| **LightGBM, tuned (adopted)** | 0.7023 | 0.2132 | 0.6147 |
| Oracle: the best any model could do | 0.7386 | 0.2019 | 0.5890 |

## Decision
- **LightGBM with the tuned settings** is kept as the production model: 200 rounds, 37 leaves, at least 192 rows per leaf, learning rate 0.0347 (before: 250 rounds, 31 leaves, 100 rows, 0.05).
- **The gain from tuning is negligible:** log-loss 0.6157 to 0.6153 on validation, 0.6151 to 0.6147 on the final test. The previous settings were already at the plateau. LightGBM, XGBoost and CatBoost are indistinguishable (all within 0.001 log-loss), and the random forest is only slightly behind.
- **The model class matters, the tuning does not:** logistic regression is clearly worse (log-loss 0.6384, it misses the interactions) and the type average is the weakest.
- **Distance to the limit:** against the type-average baseline (0.6552) and the oracle (0.5890), the tuned model closes 61% of the possible log-loss gap, logistic regression 25%. The rest is each passenger's personal taste in the simulator (random noise no feature can explain). On real data the ceiling is unknown.
- Class weights were not tried: the plan needs calibrated probabilities, and balancing the classes would distort them (as in the delay model: docs/testing/model-selection.md).
- The proxy rules of the first version score AUC 0.6666 on the same test.

## Re-check after the upcoming-flight features and the family-lifted tier (local, 2026-11-21)
The model gained four inputs after this tuning: the number of later flights, a connection, a return, and the family-lifted loyalty tier. The same grouped folds and final test were run again with the tuned and the previous settings:

| Settings | Validation log-loss | Validation AUC | Final log-loss | Final AUC | Final Brier |
|---|---|---|---|---|---|
| Previous default (250 rounds) | 0.6097 | 0.7026 | 0.6081 | 0.7047 | 0.2103 |
| Tuned (200 rounds), kept | 0.6095 | 0.7028 | 0.6081 | 0.7050 | 0.2102 |
| Type-average baseline | n/a | n/a | 0.6494 | 0.6164 | n/a |
| Oracle (best possible) | n/a | n/a | 0.5825 | 0.7403 | n/a |

The settings still tie with the default, so no new search was needed. The model closes about 62% of the log-loss gap between the baseline and the oracle (it was 61% before the new inputs); the new signals therefore add a little, and the simulated personal taste remains the limit.
