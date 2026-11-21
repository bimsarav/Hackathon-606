# Model Card: Delay-Risk Model (Phase 2)

Code: `backend/app/ml/delay_risk.py`. Design: [ADR 0008](../architecture/adr/0008-delay-risk-model.md), [SYSTEM_ARCHITECTURE.md](../architecture/SYSTEM_ARCHITECTURE.md) §10. The live model card (the numbers of the last training run) is served at `GET /api/v1/risk/model` and shown in the app under "How good are these predictions?".

## Purpose
- Rank the flights of the next 7 days by their chance of a late departure, and say why in plain words.
- Estimate, for each connecting passenger, the chance of missing the onward flight.
- Pre-fill a delay scenario (Scenario A) with a planning delay.

**Intended use:** predictions rank and pre-fill; a person runs and approves the scenario. The model never triggers an action by itself, and it does not replace the delay-propagation engine of phase 1.

**Not intended for:** same-day tactical decisions (it uses no actual times of the day itself), single-passenger commitments, or any automated decision about a person.

## Data
- **Source:** `history_flights.parquet`, built by the ingest from `Flight_Punctuality_Jan-Nov_2026_Combined.xlsx`. G9 flights from 1 Jan 2026 to the start of the operating window, with scheduled and actual times. Only operated, non-diverted flights are used.
- **Scored flights:** every flight in the operating window (`flights.parquet`, 19–30 Nov 2026), with its tail plan and bookings.
- **Connecting passengers:** `pax_segments.parquet` (infants excluded) and the hub MCT table (`mct.parquet`).

## Labels and thresholds
- **Target:** departure delay (actual minus scheduled departure) of at least *t* minutes, for *t* = 5, 15, 30, 60, 120 and 180.
- One binary classifier per threshold. The probabilities are then made non-increasing across thresholds, which gives a delay curve S(t) = P(delay ≥ t).
- A second set of classifiers, with the same recipe, predicts the **arrival** delay. It is used only for missed connections.
- **Planning delay:** the delay that is exceeded with a 20% chance, read from the curve. "On time" when even a 5-minute delay is less likely than 20%.
- **Risk band** (on P(delay ≥ 60 min); base rate about 10%): **high** = 30% or more, **medium** = 15–30%, **low** = below 15%.

## Features
Only information known 7 days ahead. No actual times of the day itself are used.

| Feature | Meaning |
|---|---|
| `origin`, `destination` | Departure and arrival station |
| `prev_origin` | Where the aircraft comes from before this flight |
| `aircraft_model` | Aircraft type (inferred or assumed where the extracts lack it) |
| `hour_local`, `weekday` | Local departure hour and day of the week |
| `leg_of_day` | Position of the flight in the aircraft's day (hub time, SHJ) |
| `turn_buffer` | Scheduled minutes between the previous arrival and this departure (0–12 h, else missing) |
| `load_factor` | Booked passengers / capacity (capped at 1.5) |
| `station_rate`, `route_rate`, `network_rate` | Share of flights 15+ min late at the station, on the route and in the whole network, over days 35 to 7 before the flight |

## Training
- LightGBM 4.7, binary objective, tuned settings (120 rounds, 11 leaves, at least 60 rows per leaf, learning rate 0.039, L2 17, row sampling 0.86), fixed seed and deterministic mode, so the same data gives the same model. How they were chosen: [model-selection.md](model-selection.md).
- **Recency weights:** a flight's weight halves every 109 days of age. Delay levels change a lot by season (16% of flights 15+ min late in June, 45% in October), so recent months count more.
- **Retraining:** every ingest run that rebuilds the operating picture (ingest stage 3). A new data drop retrains and rescores. There is no separate training service.

## Validation (time-ordered, never random)
- **Evaluation model:** trained on all history before the last 28 days, tested on the last 28 days.
- **Production model:** the same recipe on all history. It scores the window.
- **Baseline:** the historical rate of the same route at the same local departure hour, smoothed toward the overall rate.

> The results below are from the production run before tuning. The tuned model's numbers are in [model-selection.md](model-selection.md) and replace these at the next redeploy.

## Results (production run on the server, verified 2026-11-21)
Train 2026-01-01 .. 2026-10-21 (57,104 flights); test 2026-10-21 .. 2026-11-18 (5,956 flights).

| Delay of at least | Model AUC | Route × hour baseline AUC |
|---|---|---|
| 15 min | **0.798** | 0.741 |
| 60 min | **0.757** | 0.676 |

AUC is the chance that a late flight is ranked above an on-time one (0.5 = coin toss, 1.0 = perfect). The model card also records the Brier score, a climatology Brier score and a reliability table for the 60-minute model, for every threshold. Evidence: docs/testing/test-report.md.

At verification the watchlist held 1,491 flights in the next 7 days: 18 high and 140 medium risk.

## Flagging accuracy (confusion matrices, test weeks 21 Oct – 18 Nov, 5,956 flights)
Computed on every retrain and stored in `model_card.json` (`evaluation.classification`); shown in the app under "How good are these predictions?". Production run of 21 Nov 2026 01:46Z:

| Question and cut-off | Caught | False alarms | Missed | Correct no | Precision | Recall | F1 | Accuracy | Specificity |
|---|---|---|---|---|---|---|---|---|---|
| Departure 15+ min, flag at 50% | 1,532 | 750 | 812 | 2,862 | 0.67 | 0.65 | 0.66 | 0.74 | 0.79 |
| Departure 60+ min, High (30%) | 180 | 569 | 343 | 4,864 | 0.24 | 0.34 | 0.28 | 0.85 | 0.90 |
| Departure 60+ min, Medium or High (15%) | 354 | 1,553 | 169 | 3,880 | 0.19 | 0.68 | 0.29 | 0.71 | 0.71 |
| Arrival 15+ min, flag at 50% | 1,576 | 748 | 948 | 2,684 | 0.68 | 0.62 | 0.65 | 0.72 | 0.78 |
| Arrival 60+ min, flag at 30% | 161 | 538 | 363 | 4,894 | 0.23 | 0.31 | 0.26 | 0.85 | 0.90 |

**Top 10% riskiest flights:** 25.7% left 60+ min late against 8.8% overall (lift 2.9); 81.9% left 15+ min late against 39.4% (lift 2.1).

**Choosing another cut-off (departure 60+ min):**

| Flag at | Flights flagged | Precision | Recall | F1 |
|---|---|---|---|---|
| 10% | 43% | 0.16 | 0.78 | 0.26 |
| 20% | 24% | 0.20 | 0.54 | 0.29 |
| 30% (High) | 13% | 0.24 | 0.34 | 0.28 |
| 40% | 6% | 0.28 | 0.20 | 0.23 |
| 50% | 3% | 0.35 | 0.11 | 0.17 |

## Month by month (walk-forward, `evaluation.rolling_monthly`)
Each month is predicted by a model trained (same recipe) only on the months before it. This is a fairer view than the single test period above, which was also used to choose the recency half-life and to drop the isotonic step.

| Month | Flights | 15+ late | AUC 15 model / baseline | 60+ late | AUC 60 model / baseline |
|---|---|---|---|---|---|
| Jul 2026 | 6,993 | 40.1% | 0.73 / 0.64 | 13.7% | 0.67 / 0.54 |
| Aug 2026 | 7,517 | 40.3% | 0.71 / 0.69 | 11.5% | 0.69 / 0.70 |
| Sep 2026 | 6,873 | 33.1% | 0.71 / 0.71 | 6.9% | 0.73 / 0.71 |
| Oct 2026 | 6,934 | 44.8% | 0.77 / 0.74 | 12.3% | 0.73 / 0.73 |
| Nov 2026 (1–18) | 3,766 | 38.5% | 0.83 / 0.76 | 8.4% | 0.78 / 0.72 |

**Reading:** the model is never clearly worse than the route × hour baseline, and it is better in July and November. From August to October its ranking is about the same as the baseline (AUC difference 0.00–0.03), and its Brier score is slightly worse in July and September (seasonal level shifts). The headline test numbers come from the model's best period. Expect an AUC of about 0.71–0.83 for 15+ min and 0.67–0.78 for 60+ min.

## Calibration decision
LightGBM's own probabilities are used. An isotonic calibration step, fitted on a separate later month, was tested and **dropped**: it made calibration worse on the test weeks, because delay levels shift from month to month. Recency weighting handles the drift better. This also removed scikit-learn as a dependency.

## Explanations
- Method: LightGBM's built-in TreeSHAP contributions (`pred_contrib`) of the 60-minute model.
- Per flight, the top three features that **raise** the risk (contribution above 0.02 log-odds) are turned into plain phrases, for example "this route was late 78% of the time recently" or "only *N* minutes between the previous arrival and this departure".
- The phrases describe what the model used. They are not proven causes.

## Missed-connection risk
- **Connecting passenger:** same booking and person, arriving at a station and leaving it 15 minutes to 20 hours later (decision Q8).
- **Slack** = connection time − MCT. The MCT comes from the hub table for the journey; where there is no rule, the default MCT (`DEFAULT_MCT_MINUTES`, 50) is used and flagged in the UI.
- **Risk** = P(inbound arrival delay − onward departure delay > slack). It combines the inbound flight's arrival-delay curve and the onward flight's departure-delay curve, taken as independent. So a late onward flight can save a connection.
- Per flight, **expected missed connections** = the sum of its passengers' risks.
- **Backtest** (test weeks, flight pairs arriving at SHJ and leaving 15–240 min later, default MCT): in the "no slack" band the model predicted a 0.70 miss rate against 0.69 observed. Evidence: docs/testing/test-report.md.

## Limitations and assumptions
- **Seven-day view only.** Same-day information (actual inbound delay, weather, ATC slots) is not used, so on the day the delay-propagation engine of Scenario A is the better tool.
- **Independence.** Inbound and onward delays are treated as independent. In reality they share causes (weather at the hub), so the risk can be over- or under-stated on bad days.
- **Delay curve bands.** The miss probability uses a representative delay per band of the curve (for example 45 min for 30–60 min), so it is approximate.
- **Long delays.** Delays of 2 hours or more are rare (under 1% in the test weeks) and the model over-estimates them. Treat P(120+) and P(180+) as a ranking, not a level.
- **Seasonal drift.** The model follows recent months; a sudden change (new schedule, new station) is learned only after it shows up in the history.
- **Synthetic and inferred inputs.** Aircraft type and seat capacity are inferred or assumed for many window flights, so `aircraft_model` and `load_factor` carry that uncertainty. Passengers are linked by a synthetic `customer_key`. If `DEMO_SCENARIO=true`, the labelled synthetic demo flights are scored like the others.
- **G9 only.** Partner and other carriers are not in the history or the window.

## Outputs
Written by ingest stage 3 into the ops data folder (Docker volume `ops-data`):
- `flight_risk.parquet`: per window flight, P(departure delay ≥ t), arrival curve, planning delay, band, reasons, connecting passengers and expected missed connections.
- `connection_risk.parquet`: per connecting passenger, connection time, MCT, slack and misconnect risk.
- `model_card.json`: data ranges, features, metrics by threshold, reliability, arrival-model metrics, connection backtest and assumptions.

## Live departure and arrival models (ADR 0014)
Same data (`Flight_Punctuality_Jan-Nov_2026_Combined.xlsx`), same last-28-day holdout (5,956 unseen G9 flights), scored once. The planning models above are unchanged; the live models add what is known on the day. Inputs: delay of the aircraft's previous leg (arrival and departure) and, for arrival, this flight's own departure delay.

| Model | AUC 15+ | AUC 60+ | Brier skill 60+ | Mean abs. error of expected delay (min) |
|---|---|---|---|---|
| Departure, planning (7 days ahead) | 0.801 | 0.770 | 0.079 | 19.6 |
| Departure, inbound delay known | 0.908 | 0.900 | 0.429 | 13.3 |
| Arrival, planning | 0.765 | 0.762 | 0.011 | 21.2 |
| Arrival, inbound delay known | 0.840 | 0.887 | 0.294 | 16.4 |
| Arrival, departure delay known | 0.930 | 0.974 | 0.601 | 10.0 |

Planning features that did not help (tested on the same holdout): destination arrival-delay rate, scheduled block time (AUC change under 0.003). Expected delay is the mean of the curve with representative band values, so the minutes error is approximate. P(120+) and P(180+) stay rankings, not levels. Artifacts: `live_models/*.txt`, `live_model_card.json`, `window_features.parquet` in the ops folder; training results: docs/testing/test-report.md.
