# Backtest: delay propagation against real history

Command: `DATA_DIR=<data dir> python -m app.backtest` (after the ingest). Output: `ops/backtest_report.json`.

## Method
- Source: `ops/history_flights.parquet`, G9 flights 1 Jan to 18 Nov 2026 with actual times.
- Events: real **primary** delays of 60+ min (the aircraft was on the ground in time, so the delay started on that flight). 1,634 events on 71 aircraft.
- Each event's actual delay is replayed through the engine's `propagate()`. The next 4 legs of the same aircraft within 24 h (5,314 legs) are compared with their actual departure delays. A leg is delayed from 15 min.
- Limits: actual delays also contain new, unrelated delays, and recovery actions on the day (a tail swap ends the chain in the data).

## Results (run 2026-11-21 on the real extracts)
| Variant (minimum turn SHJ / elsewhere) | Mean abs. error | Within 15 min | Precision | Recall | Knock-on minutes predicted / actual |
|---|---|---|---|---|---|
| Measured minimum, fastest 5% (51 / 36), current default | 25.2 min | 55.6% | 97.7% | 62.8% | 179,515 / 303,492 |
| Flat 40 (MVP before) | 25.4 min | 55.9% | 98.6% | 60.6% | 179,003 / 303,492 |
| Recovery turn, quartile (52 / 41) | 23.7 min | 58.9% | 96.8% | 65.2% | 194,498 / 303,492 |
| **Recovery turn, median (60 / 48)** | **22.2 min** | **61.0%** | 91.2% | **72.3%** | 231,482 / 303,492 |
| No knock-on (baseline) | 57.1 min | 38.4% | – | 0% | 0 / 303,492 |

By next-leg position (measured minimum): leg 1 recall 96.7% at 99.7% precision; leg 2 47%; leg 3 30%; leg 4 18.5%.

## Findings
1. The engine more than halves the error of ignoring knock-on (57 → 22–25 min) and almost never raises a false alarm on the next leg.
2. It under-predicts knock-on: when an aircraft arrives late, the real turn takes a median 60 min at SHJ and 48 min elsewhere (history), longer than the fastest-5% minimum. The minimum is right for "what is still possible"; the median recovery turn is better for "what will probably happen".
3. Recall falls on later legs because new delays add up during the day; the engine only propagates the known delay.

Recovery turns per station are measured in the history: legs where the aircraft arrived less than 30 min before the scheduled departure.
