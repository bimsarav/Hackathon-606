# UC5 synthetic data and data assumptions (generated 2026-11-20, NOT airline data)

User decisions (2026-11-20, `execution/QUESTIONS_UC5.md`): the open data questions (Q4–Q11) are filled with synthetic data built from the given data plus domain knowledge, and the open rule questions (Q12–Q15) use the agent's proposals. Every synthetic value is labelled `*_synthetic` or listed below, so real files can replace it later. This folder is git-ignored with the dataset (it holds derived passenger data).

Regenerate: `python load_bookings.py "<Past & Future Booking Data.zip>" bookings.duckdb`, then `python generate_synthetic.py bookings.duckdb` (deterministic).
Demo "now" = 2026-11-20 00:00 UTC. Window = flights 2026-11-19 → 2026-11-30 (the rotation file's range). History = the 12 months before "now".

## Files
| File | Rows | Answers | How it is built |
|---|---|---|---|
| `aircraft_registry_synthetic.csv` | 120 | Q25/Q30 | Registration → model/seats. 51 rows exact from inventory matches, 69 assumed A320/174 (low confidence). Seat availability itself always comes from the inventory allocation (curtail/oversell) |
| `customer_profile_synthetic.csv` | 174,723 | Q4 | One row per passenger in the window. `customer_key` = SHA-256 prefix of the normalised name (the only identity field available). `flown_segments_12m` and `bookings_12m` are **real counts** from history. `ambiguous_common_name` = in more than 60 PNRs in 12 months (common/placeholder names): frequency unreliable, tier capped at Blue. `loyalty_tier_synthetic` (members only): ≥24 segments Platinum, ≥12 Gold, ≥6 Silver, else Blue. `travel_frequency_band` covers non-members too (5,197 frequent non-members) |
| `booking_class_map_synthetic.csv` | 388 | Q7, Q8 | Booking code → `revenue_type` + `fare_family_synthetic`. Non-revenue = codes whose active bookings are zero-fare: VI, DU, DT, Z, DUMKT, GD, DUFAM. E-ladder codes (E + number) ordered by average fare and split by passenger share: 50% Basic, 35% Value, 15% Ultimate. Other codes (P, PC, SE, CSS, SPS, G30B30, …) = "Other (promo/corporate/agency)". BUS = bus leg |
| `ssr_synthetic.csv` | 4,360 | Q5 | Window passengers only. **Data-derived:** INFT for every infant, linked to an adult in the same PNR (2,527/2,527 linked). (UMNR was derived for children without an adult; unaccompanied minors are out of scope since 2026-11-21, so the product no longer derives it.) **Synthetic, deterministic** (adults): WCHR 0.60%, WCHS 0.15%, WCHC 0.05%, BLND 0.03%, DEAF 0.03%, MEDA 0.05%, PREG 0.10%. These rates are assumptions, not airline statistics |
| `delay_code_groups_synthetic.csv` | 162 | Q11 | Codes seen in the punctuality file (`NNmin-CCX`), treated as IATA AHM 730/731 two-digit codes plus sub-code letter, grouped by IATA range. Reactionary codes 91–96 = about 2.19M of 2.88M coded delay minutes (departure + arrival codes, so some double counting): rotation knock-on dominates |
| `load_bookings.py`, `generate_synthetic.py` | – | – | Reproducible loaders/generators |

## Data assumptions (no extra file needed)
| Q | Assumption | Basis |
|---|---|---|
| 6 | One booking row = one passenger on one segment; `TOTAL_FARE` etc. are per passenger per segment | Verified: fares differ between a passenger's segments in 90% of 2-segment journeys |
| 6 | Currency AED | Assumed (Sharjah-based carrier) [VALIDATE] |
| 6 | Active booking = `RES_STATUS=CNF`, `SEG_STATUS=CNF`, `FLIGHT_STATUS=ACT` (14.07M of 27.88M rows). OHD (on hold) excluded from impact by default but countable on request | Profile: cancelled segments carry zero fares |
| 6 | `TNFSEG`/`MODSEG`/`CNXSEG` = segment transferred / modified / cancelled flags (informational only) | Assumed from names [VALIDATE] |
| 6 | Duplicate passenger-segment rows (1.83M) are booking history; the latest active row wins | Profile |
| 10 | Inventory snapshot time = 2026-11-19 13:26 UTC (same extract time as the connection-time file) | Assumed [VALIDATE] |
| 9 | Times: `EST_TIME_DEPARTURE_ZULU` and schedule times are UTC; inventory has both local and UTC; airport offsets come from a public time-zone dataset (Q22) | User answers Q9, Q22 |
| 8 | Connection = same passenger, same PNR, arriving at SHJ then departing SHJ 15 min–20 h later (3.8M such pairs in history) | User answer Q8 |
| – | 4 malformed CSV lines (Oct 2025) rejected and logged | Loader |

## Rule defaults (Q12–Q15, agent proposals approved by the user 2026-11-20)
- **Priority (Q12), in strict tiers, not one blended score:**
  1. Hard feasibility: safety, seats, MCT 15 min–20 h, passenger rights.
  2. Mandated care: special assistance (WCH*/BLND/DEAF/MEDA/PREG), UMNR, families with infants.
  3. Urgency: onward connection, last flight of the day, journey length.
  4. Configurable weighted score as tie-breaker: loyalty tier, travel frequency, fare value, ancillaries, journey complexity, booking characteristics. Non-revenue passengers come after all revenue passengers.
- **Passenger rights (Q12):** EU261 on flights departing an EU/EEA airport (care, rerouting, refund, €250/400/600 compensation). UAE and other regimes use generic care rules (meals after 2 h, hotel overnight), configurable [VALIDATE].
- **Crew (Q13):** out of scope, because no crew data was supplied. Stated as a limitation; the recovery must be checked by crew control.
- **Rebooking scope (Q14):** own G9 flights only, within 24 h (partner and other carriers removed from scope on 2026-11-21; future enhancement). After that, next day plus hotel and meals. No other airlines (no data).
- **Costs (Q15), assumed and configurable:**
  - delay cost per minute by aircraft size (default AED 400/min);
  - hotel AED 350 per night; meal voucher AED 50;
  - re-accommodation handling AED 25 per passenger;
  - EU261 compensation by distance band;
  - cancellation cost = lost revenue + care + compensation.
