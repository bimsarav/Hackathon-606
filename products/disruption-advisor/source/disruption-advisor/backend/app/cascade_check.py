"""Cascade formula check: the simple knock-on rule against what really happened (ingest stage 3b).

Rule under test:  next departure = max(scheduled departure, previous arrival + FORMULA_TURN_MINUTES).
Pairs: consecutive operated flights of the same aircraft, the second leaving from where the first arrived, scheduled
gap 0-24 h, over the last MONTH_DAYS days of the punctuality history. A *cascade pair* is one where the rule predicts a
knock-on (previous arrival + turn is later than the next scheduled departure).
  formula KO  = minutes the rule says the next flight leaves late
  actual KO   = minutes it really left late (never below 0)
  delta       = actual KO - formula KO (positive: the rule under-estimated)
Extreme outliers (actual KO of EXTREME_KO minutes or more, for example an overnight technical failure) are listed
apart and left out of the figures and the charts, as one such flight would dominate the mean.

Output (ops folder): cascade_check.json. Read-only data for the 7-day tab; it changes no recommendation.
"""

from __future__ import annotations

import json
import logging
from datetime import timedelta
from pathlib import Path
from typing import Any

import duckdb

log = logging.getLogger("ingest.cascade_check")
FORMULA_TURN_MINUTES = 40
MONTH_DAYS = 30
EXTREME_KO = 360
BAND = 15  # "within +-15 min"; also the threshold for under- and over-estimates
WIDE_BAND = 30
MAX_ROWS = 3000
BINS = (
    ("< -15", None, -15),
    ("-15 to 0", -15, 0),
    ("0 to 15", 0, 15),
    ("15 to 30", 15, 30),
    ("30 to 60", 30, 60),
    ("> 60", 60, None),
)


def _hhmm(value: Any) -> str:
    return str(value.strftime("%H:%M"))


def run(ops: Path) -> dict[str, Any]:
    con = duckdb.connect()
    turn = f"INTERVAL {FORMULA_TURN_MINUTES} MINUTE"
    rows = con.execute(
        f"""
        WITH h AS (
            SELECT tail, flight_number, origin, destination, std, sta, atd, ata
            FROM '{ops}/history_flights.parquet'
            WHERE operated AND NOT coalesce(diverted, FALSE) AND atd IS NOT NULL AND ata IS NOT NULL),
        p AS (
            SELECT *, lag(flight_number) OVER w AS prev_flt, lag(destination) OVER w AS prev_dest,
                   lag(sta) OVER w AS prev_sta, lag(ata) OVER w AS prev_ata
            FROM h WINDOW w AS (PARTITION BY tail ORDER BY std)),
        c AS (
            SELECT *, date_diff('minute', prev_sta, prev_ata) AS prev_arr_delay,
                   prev_ata + {turn} AS ready,
                   greatest(0, date_diff('minute', std, prev_ata + {turn})) AS formula_ko,
                   greatest(0, date_diff('minute', std, atd)) AS actual_ko
            FROM p WHERE prev_dest = origin AND date_diff('minute', prev_sta, std) BETWEEN 0 AND 1440)
        SELECT std, tail, prev_flt, prev_arr_delay, flight_number, origin, destination, atd,
               greatest(std, ready) AS formula_etd, formula_ko, actual_ko, (SELECT max(std) FROM h) AS last_std
        FROM c
        WHERE formula_ko > 0 AND std >= (SELECT max(std) FROM h) - INTERVAL {MONTH_DAYS} DAY
        ORDER BY std, tail"""
    ).fetchall()

    pairs: list[dict[str, Any]] = []
    excluded: list[dict[str, Any]] = []
    last = rows[0][-1] if rows else None
    for std, tail, prev_flt, prev_arr, flt, origin, dest, atd, etd, fko, ako, _ in rows:
        record = {
            "date": std.strftime("%Y-%m-%d"),
            "tail": tail,
            "prev_flight": prev_flt,
            "prev_arrival_delay": int(prev_arr),
            "flight": flt,
            "route": f"{origin}>{dest}",
            "std": _hhmm(std),
            "formula_etd": _hhmm(etd),
            "actual_atd": _hhmm(atd),
            "formula_ko": int(fko),
            "actual_ko": int(ako),
            "delta": int(ako - fko),
        }
        (excluded if ako >= EXTREME_KO else pairs).append(record)

    n = len(pairs)
    deltas = [p["delta"] for p in pairs]
    within = sum(1 for d in deltas if abs(d) <= BAND)
    within_wide = sum(1 for d in deltas if abs(d) <= WIDE_BAND)
    histogram = [
        {
            "label": label,
            "count": sum(1 for d in deltas if (lo is None or d >= lo) and (hi is None or d < hi)),
        }
        for label, lo, hi in BINS
    ]
    result = {
        "formula": f"next departure = max(scheduled departure, previous arrival + {FORMULA_TURN_MINUTES} min)",
        "definition": (
            f"Consecutive operated flights of the same aircraft, the second leaving from where the first arrived, "
            f"scheduled gap up to 24 h, last {MONTH_DAYS} days of the punctuality history. A cascade pair is one where "
            "the formula predicts a knock-on delay. Delta = actual knock-on minus formula knock-on."
        ),
        "from": (last - timedelta(days=MONTH_DAYS)).strftime("%Y-%m-%d") if last else None,
        "to": last.strftime("%Y-%m-%d") if last else None,
        "kpis": {
            "pairs": n,
            "mean_delta": round(sum(deltas) / n, 1) if n else None,
            "within_15": within,
            "within_15_share": round(within / n, 4) if n else None,
            "within_30": within_wide,
            "within_30_share": round(within_wide / n, 4) if n else None,
            "underestimates": sum(1 for d in deltas if d > BAND),
            "overestimates": sum(1 for d in deltas if d < -BAND),
        },
        "histogram": histogram,
        "excluded": excluded,
        "excluded_rule": f"actual knock-on of {EXTREME_KO} min or more",
        "rows_total": n,
        "rows": pairs[-MAX_ROWS:],
    }
    (ops / "cascade_check.json").write_text(json.dumps(result))
    log.info("cascade check: %d pairs, %d within +-%d min", n, within, BAND)
    return {"pairs": n, "excluded": len(excluded)}
