# ADR 0014: Live departure and arrival delay models

Status: accepted (2026-11-21) · Builds on ADR 0008 (delay-risk model)

## Context
The planning models (ADR 0008) use only what is known 7 days ahead. On the last 28 days of
`Flight_Punctuality_Jan-Nov_2026_Combined.xlsx` (5,956 unseen G9 flights) they reach AUC about 0.77 for a
departure delay of 60+ minutes and 0.76 for an arrival delay of 60+ minutes. Tuning and extra planning features
(destination arrival rate, block time, month) moved this by less than 0.01: the planning information is exhausted.

The punctuality data holds more signal on the day itself: the previous leg of the same aircraft (its arrival and
departure delay) and, for arrival, this flight's own departure delay.

## Decision
Keep the planning models for the 7-day watchlist. Add three live model sets (`app/ml/live_delay.py`), each one
LightGBM classifier per threshold (5, 15, 30, 60, 120, 180 min), trained on the same flights, features, recency weights
and tuned parameters, plus extra inputs:

| Set | Target | Extra inputs |
|---|---|---|
| `dep` | departure delay (atd − std) | inbound aircraft arrival delay, inbound departure delay |
| `arr_in` | arrival delay (ata − sta) | inbound aircraft arrival delay, inbound departure delay |
| `arr_dep` | arrival delay (ata − sta) | the above plus this flight's own departure delay |

Inbound = the previous operated leg of the same tail, at most 12 hours earlier. Missing inputs stay missing (LightGBM
handles them). API: `POST /api/v1/risk/flights/{id}/predict` returns departure and arrival curves; with no live input it
returns the planning curves. The UI (watchlist, flight detail, "Predict departure and arrival") lets a person enter the
inbound delay and/or the flight's own departure delay (actual or what-if).

## Evidence (held-out last 28 days, scored once; `docs/testing/model-card.md`)
| Prediction | AUC 60+ planning → live | AUC 15+ planning → live | Mean abs. error of expected delay |
|---|---|---|---|
| Departure, inbound delay known | 0.770 → 0.900 | 0.801 → 0.908 | 19.6 → 13.3 min |
| Arrival, inbound delay known | 0.762 → 0.887 | 0.765 → 0.840 | 21.2 → 16.4 min |
| Arrival, departure delay known | 0.762 → 0.974 | 0.765 → 0.930 | 21.2 → 10.0 min |

## Consequences
- The big gain needs a live input. For a flight 7 days away the honest answer is still the planning curve; the UI says
  which mode produced each number.
- Departure delay is a strong input for arrival delay by construction (flight time varies little); the value is in using
  it early, e.g. for a flight that has pushed back late.
- Inbound delay is the actual arrival delay of the previous leg, or its current ETA when airborne. The ingest
  does not feed live operations data yet; a live feed (ACARS/OPS) is the next step so the fields are filled automatically.
- The what-if arrival model and the connection logic (`miss_probability`) still use the planning arrival curves; wiring
  live curves into missed-connection risk is a possible follow-up.
