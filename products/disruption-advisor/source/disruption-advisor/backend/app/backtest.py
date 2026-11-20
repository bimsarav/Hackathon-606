"""Backtest: replay real delays from ``ops/history_flights.parquet`` through the engine's delay propagation.

For every real *primary* delay (a flight at least ``PRIMARY_MIN_DELAY`` minutes late although its aircraft was on
the ground in time), the engine's ``propagate`` predicts the knock-on delay of the same aircraft's next legs. The
prediction is compared with the delays that really happened.

Read the results with care: the actual delays also contain new, unrelated delays on later legs, and recovery
actions taken on the day (for example a tail swap ends the aircraft's chain in the data).

Run:  DATA_DIR=/data python -m app.backtest   ->  DATA_DIR/ops/backtest_report.json
"""

from __future__ import annotations

import json
import os
import sys
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

import duckdb

from app.config import Settings
from app.engine.network import Turn, TurnTimes, propagate, turn_at
from app.engine.store import Leg

PRIMARY_MIN_DELAY = 60  # minutes late at departure for a delay to be replayed
DELAYED = 15  # a leg counts as delayed from this many minutes (industry on-time limit)
MAX_NEXT_LEGS = 4  # next legs of the same aircraft that are compared
HORIZON = timedelta(hours=24)  # ... departing within this time of the replayed flight

COLUMNS = (
    "flight_id, flight_number, tail, origin, destination, std, sta, atd, ata, dep_dly, next_from_same_station, leg_no"
)


@dataclass(frozen=True)
class HistLeg:
    flight_id: str
    flight_number: str
    tail: str
    origin: str
    destination: str
    std: datetime
    sta: datetime
    atd: datetime | None
    ata: datetime | None
    dep_dly: float | None
    next_from_same_station: bool | None
    leg_no: int | None

    def as_leg(self) -> Leg:
        return Leg(
            self.flight_id, self.flight_number, "G9", self.tail, self.origin, self.destination,
            self.std, self.sta, 0, 0, 0, "", "history",
        )  # fmt: skip

    @property
    def actual_delay(self) -> int:
        return max(int(self.dep_dly or 0), 0)


def load_chains(history: Path) -> dict[str, list[HistLeg]]:
    """Operated legs per aircraft, in actual order (the chain built by the ingest)."""
    rows = duckdb.connect().execute(
        f"SELECT {COLUMNS} FROM '{history}' "  # noqa: S608 - path from configuration, no user input
        "WHERE operated AND leg_no IS NOT NULL AND sta IS NOT NULL ORDER BY tail, leg_no"
    )
    chains: dict[str, list[HistLeg]] = defaultdict(list)
    for r in rows.fetchall():
        leg = HistLeg(*r)
        chains[leg.tail].append(leg)
    return chains


def events(chains: dict[str, list[HistLeg]], turn: Turn) -> list[tuple[HistLeg, list[HistLeg]]]:
    """Primary delays and the next legs of the same aircraft that followed them."""
    out = []
    for legs in chains.values():
        for i, leg in enumerate(legs):
            if leg.atd is None or leg.actual_delay < PRIMARY_MIN_DELAY:
                continue
            prev = legs[i - 1] if i > 0 else None
            arrived_late = (
                prev is not None
                and prev.next_from_same_station
                and prev.ata is not None
                and prev.ata + turn_at(turn, leg.origin) > leg.std
            )
            if arrived_late:
                continue  # the aircraft arrived late: knock-on delay, not primary
            nxt: list[HistLeg] = []
            for j in range(i + 1, min(i + 1 + MAX_NEXT_LEGS, len(legs))):
                if not legs[j - 1].next_from_same_station or legs[j].std - leg.std > HORIZON:
                    break  # chain broken (other station, swap) or too far ahead
                nxt.append(legs[j])
            if nxt:
                out.append((leg, nxt))
    return out


def score(evts: list[tuple[HistLeg, list[HistLeg]]], turn: Turn | None) -> dict[str, Any]:
    """Compare predicted and actual delays of the next legs. ``turn=None`` predicts no knock-on (baseline)."""
    pairs: list[tuple[int, int, int]] = []  # (position, predicted, actual)
    for leg, nxt in evts:
        if turn is None:
            predicted = [0] * len(nxt)
        else:
            timings = propagate([leg.as_leg()] + [n.as_leg() for n in nxt], leg.atd or leg.std, turn, leg.tail)
            predicted = [t.delay_minutes for t in timings[1:]]
        pairs += [(k + 1, p, n.actual_delay) for k, (p, n) in enumerate(zip(predicted, nxt, strict=True))]

    def stats(rows: list[tuple[int, int, int]]) -> dict[str, Any]:
        n = len(rows)
        if not n:
            return {"legs": 0}
        tp = sum(1 for _, p, a in rows if p >= DELAYED and a >= DELAYED)
        fp = sum(1 for _, p, a in rows if p >= DELAYED and a < DELAYED)
        fn = sum(1 for _, p, a in rows if p < DELAYED and a >= DELAYED)
        precision = tp / (tp + fp) if tp + fp else None
        recall = tp / (tp + fn) if tp + fn else None
        return {
            "legs": n,
            "mean_abs_error_min": round(sum(abs(p - a) for _, p, a in rows) / n, 1),
            "within_15_min_share": round(sum(1 for _, p, a in rows if abs(p - a) <= 15) / n, 3),
            "delayed_legs_actual": tp + fn,
            "delayed_legs_predicted": tp + fp,
            "precision": round(precision, 3) if precision is not None else None,
            "recall": round(recall, 3) if recall is not None else None,
            "knock_on_minutes_predicted": sum(p for _, p, _ in rows),
            "knock_on_minutes_actual": sum(a for _, _, a in rows),
        }

    return {
        "all_next_legs": stats(pairs),
        "by_position": {str(k): stats([r for r in pairs if r[0] == k]) for k in range(1, MAX_NEXT_LEGS + 1)},
    }


def _turns(shj: int, other: int) -> TurnTimes:
    return TurnTimes(timedelta(minutes=other), {"SHJ": timedelta(minutes=shj)})


def run(history: Path, settings: Settings) -> dict[str, Any]:
    measured = TurnTimes(
        timedelta(minutes=settings.min_turn_minutes),
        {k: timedelta(minutes=v) for k, v in settings.min_turn_by_station.items()},
    )
    flat40 = timedelta(minutes=40)
    chains = load_chains(history)
    evts = events(chains, measured)  # same events for every variant, so the scores compare like with like
    return {
        "method": (
            f"Real primary delays >= {PRIMARY_MIN_DELAY} min (aircraft on the ground in time) are replayed through "
            f"the engine's propagate(); the next {MAX_NEXT_LEGS} legs of the same aircraft within "
            f"{HORIZON.total_seconds() / 3600:.0f} h are compared with their actual departure delays. Delayed = "
            f"{DELAYED}+ min. Actual delays also include new, unrelated delays and recovery actions."
        ),
        "events": len(evts),
        "aircraft": len({e[0].tail for e in evts}),
        "period": [str(min(e[0].std for e in evts)), str(max(e[0].std for e in evts))] if evts else None,
        "variants": {
            "measured_turns": score(evts, measured),
            "flat_40_min_turn": score(evts, flat40),
            # turns measured when the aircraft arrived late (history): quartile and median per station
            "recovery_turns_p25_52_41": score(evts, _turns(52, 41)),
            "recovery_turns_median_60_48": score(evts, _turns(60, 48)),
            "no_knock_on_baseline": score(evts, None),
        },
    }


def main() -> int:
    data_dir = Path(os.environ.get("DATA_DIR", "/data"))
    history = data_dir / "ops" / "history_flights.parquet"
    if not history.exists():
        print(f"{history} not found: run the ingest first (python -m app.ingest)", file=sys.stderr)
        return 1
    settings = Settings(database_url=os.environ.get("DATABASE_URL", "postgresql+psycopg://unused"))
    report = run(history, settings)
    (data_dir / "ops" / "backtest_report.json").write_text(json.dumps(report, indent=2))
    print(json.dumps(report, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
