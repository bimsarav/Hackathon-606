# Model Card: Reward Preference Model (Phase 5)

Code: `backend/app/ml/reward_pref.py` (ingest stage 4). Design: [REWARDS_DESIGN.md](../architecture/REWARDS_DESIGN.md), [ADR 0012](../architecture/adr/0012-passenger-reward-recommendation.md).

> **SYNTHETIC TRAINING DATA.** No real reward-redemption history exists. The offers and outcomes are simulated from an assumed behaviour model, so this model reproduces those assumptions, not real customer choices. Retrain on the airline's offer log when it exists (replace `generate_history`; nothing else changes).

## Purpose
Estimate P(accept) for a given passenger, reward type, amount and disruption severity. The reward plan uses it to choose the reward type and amount that a passenger is most likely to take, within the budget. It never contacts a passenger.

## Data
- Real passenger profiles (the operating window's bookings and customer table, revenue passengers only, infants excluded): 111,503 passengers.
- 300,000 simulated offers (two per passenger), with a simulated accepted/declined outcome. Whole passengers are held out together: 238,836 offers train, 61,164 test.
- Each passenger also carries what else is booked after the flight (later segments, a connection, a return), computed from the real bookings: 35% of the profiles have a later flight, 30% a connection and 6% a return.
- Reward types and amounts (AED): meal 50, gift voucher 100/200/400, lounge 120, miles worth 100/200/400 (members only), free ticket 600 (severe disruptions only).

## Assumed behaviour used to simulate outcomes
- A passenger who bought a meal on the booking, or travels with children, is more likely to accept a meal voucher.
- Online and app bookers and price-conscious fares (Basic, Value) are more likely to accept gift vouchers.
- Passengers who paid for a seat, Ultimate fares and frequent travellers are more likely to accept a lounge pass; families are less likely.
- Miles are accepted almost only by loyalty members, more by frequent travellers and Silver tier or above.
- Free tickets are accepted more by frequent travellers, Gold or Platinum members, Ultimate fares and groups.
- Everyone accepts more after a more severe disruption; each passenger also has a personal taste (random effect), and acceptance of an amount peaks when it matches the severity.

## Features
`fare_family`, `sales_channel`, `loyalty_tier`, `frequency`, `reward_type`, `has_meal`, `has_seat`, `ancillaries`, `fare`, `baggage_kg`, `pnr_size`, `children`, `infants`, `flown_12m`, `is_member`, `amount_aed`, `severity`.

## Model
LightGBM binary classifier, tuned settings (200 rounds, 37 leaves, at least 192 rows per leaf, learning rate 0.0347), fixed seed, deterministic. How they were chosen and what else was compared: [reward-model-selection.md](reward-model-selection.md).

## Results on held-out passengers (synthetic outcomes)
| Model | AUC | Brier |
|---|---|---|
| **Trained model** | **0.701** | **0.2138** |
| Average acceptance of the reward type | 0.615 | 0.2316 |
| First version: proxy rules | 0.665 | n/a |

Observed acceptance rate 58%. The AUC is modest because every simulated passenger also has a personal taste (random noise) that no feature explains.

| Reward type | Test offers | Acceptance | AUC |
|---|---|---|---|
| MEAL | 18,048 | 63% | 0.675 |
| VOUCHER | 17,993 | 66% | 0.629 |
| LOUNGE | 18,132 | 44% | 0.673 |
| MILES | 3,559 | 79% | 0.647 |
| TICKET | 3,432 | 46% | 0.639 |

## Limits
- The numbers measure how well the model recovers the simulated behaviour. They say nothing about real acceptance.
- Miles are only ever offered to loyalty members in the history, so the model cannot score miles for non-members; the plan never offers them.
- The budget counts the value offered, not the expected cost after declines.
