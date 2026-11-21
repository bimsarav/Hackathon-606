# ADR-0008: Delay-risk prediction with LightGBM and TreeSHAP reasons

- **Status:** Accepted (2026-11-21, phase 2 approved by the user)
- **Context:** Phase 2 must flag flights likely to be late in the next 7 days, with reasons, and estimate each connecting passenger's misconnect risk. Data: 63k operated G9 flights (Jan – 18 Nov 2026) with actual times; 36% depart 15+ minutes late, 10% 60+ minutes; strong seasonality (16% in June, 45% in October). Explanations are mandatory (GDPR Art. 22, ADR 0007).
- **Decision:**
  - **Model:** one LightGBM binary classifier per threshold (5, 15, 30, 60, 120, 180 min), trained with recency weights (half-life 109 days after tuning), then made monotone across thresholds, giving a delay curve S(t). LightGBM's own probabilities are used: isotonic calibration on a later month was tested and dropped (2026-11-21) because month-to-month shifts in the delay level made it worse (model card).
  - **Features:** only what is known 7 days ahead (schedule, aircraft plan, bookings, lagged station and route delay rates). No same-day actuals, so the score is honest for the 7-day horizon.
  - **Validation:** time-ordered split (train on the older history, test on the latest 28 days), compared with a route × departure-hour historical rate. Metrics are written to a model card and shown in the UI.
  - **Reasons:** LightGBM TreeSHAP contributions (`pred_contrib`), top three per flight, mapped to plain phrases.
  - **Runs in the ingest** (stage 3): retrains and rescores whenever the data or the code changes; deterministic.
  - **Saved (21 Nov 2026):** stage 3 also writes the production departure and arrival boosters, the category levels and the settings they need to `ops/delay_model/`. `delay_risk.load_models` refuses a model built for another feature list, thresholds or LightGBM version. `score_test_flights` scores flights that were not in the ingest run (uploaded test flights, ADR 0013) with it, using the live history for their delay-rate features; nothing is retrained.
- **Selection and tuning (T-511, 2026-11-21):** compared with a route × hour baseline, prior, logistic regression, random forest, XGBoost and CatBoost on three time-ordered validation blocks; LightGBM and XGBoost tuned with Optuna; final test scored once. LightGBM with tuned settings was kept (see `docs/testing/model-selection.md`).
- **Alternatives considered:**
  - **Logistic regression:** fully transparent, but misses interactions (station × hour × season) that matter here. Measured in T-511: final-test AUC 60 of 0.715 against 0.761 for tuned LightGBM. Kept as a reference.
  - **Quantile regression of the delay minutes:** gives the delay distribution directly, but calibration per threshold is harder to check and explain than probabilities.
  - **Deep learning / sequence models:** too little data per route and harder to explain.
- **Consequences:**
  - One new dependency (LightGBM 4.7; scikit-learn was dropped, the metrics are computed with NumPy) and the OpenMP runtime in the image.
  - Training adds about 30 seconds to the ingest on the server.
  - The probabilities are only as good as the history; seasonal shifts are partly covered by the lagged rates. The model card makes the test-period performance visible, and predictions never trigger actions by themselves.
