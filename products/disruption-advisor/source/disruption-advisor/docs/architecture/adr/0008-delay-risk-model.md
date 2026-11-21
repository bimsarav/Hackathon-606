# ADR-0008: Delay-risk prediction with LightGBM and TreeSHAP reasons

- **Status:** Accepted (2026-11-21, phase 2 approved by the user)
- **Context:** Phase 2 must flag flights likely to be late in the next 7 days, with reasons, and estimate each connecting passenger's misconnect risk. Data: 63k operated G9 flights (Jan – 18 Nov 2026) with actual times; 36% depart 15+ minutes late, 10% 60+ minutes; strong seasonality (16% in June, 45% in October). Explanations are mandatory (GDPR Art. 22, ADR 0007).
- **Decision:**
  - **Model:** one LightGBM binary classifier per threshold (5, 15, 30, 60, 120, 180 min), trained with recency weights (half-life 60 days), then made monotone across thresholds, giving a delay curve S(t). LightGBM's own probabilities are used: isotonic calibration on a later month was tested and dropped (2026-11-21) because month-to-month shifts in the delay level made it worse (model card).
  - **Features:** only what is known 7 days ahead (schedule, aircraft plan, bookings, lagged station and route delay rates). No same-day actuals, so the score is honest for the 7-day horizon.
  - **Validation:** time-ordered split (train on the older history, test on the latest 28 days), compared with a route × departure-hour historical rate. Metrics are written to a model card and shown in the UI.
  - **Reasons:** LightGBM TreeSHAP contributions (`pred_contrib`), top three per flight, mapped to plain phrases.
  - **Runs in the ingest** (stage 3): retrains and rescores whenever the data changes; deterministic.
- **Alternatives considered:**
  - **Logistic regression:** fully transparent, but misses interactions (station × hour × season) that matter here. Kept as the baseline idea (route × hour rate).
  - **Quantile regression of the delay minutes:** gives the delay distribution directly, but calibration per threshold is harder to check and explain than probabilities.
  - **Deep learning / sequence models:** too little data per route and harder to explain.
- **Consequences:**
  - One new dependency (LightGBM 4.7; scikit-learn was dropped, the metrics are computed with NumPy) and the OpenMP runtime in the image.
  - Training adds about 30 seconds to the ingest on the server.
  - The probabilities are only as good as the history; seasonal shifts are partly covered by the lagged rates. The model card makes the test-period performance visible, and predictions never trigger actions by themselves.
