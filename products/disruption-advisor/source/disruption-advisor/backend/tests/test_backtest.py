"""Backtest on a hand-made history: one primary delay, one knock-on leg, one chain break."""

from datetime import datetime, timedelta
from pathlib import Path

import duckdb

from app.backtest import events, load_chains, score
from app.engine.network import TurnTimes


def t(h: int, m: int = 0) -> datetime:
    return datetime(2026, 5, 1, h, m)


def _write(path: Path) -> Path:
    # tail A6-AAA: leg 1 leaves 90 min late (primary: nothing before it). Leg 2 is planned 60 min after leg 1's
    # scheduled arrival and really left 70 min late. Leg 3 starts at another station, so the chain breaks.
    rows = [
        ("L1", "G9001", "A6-AAA", "SHJ", "KHI", t(6), t(8), t(7, 30), t(9, 30), 90.0, True, 1),
        ("L2", "G9002", "A6-AAA", "KHI", "SHJ", t(9), t(11), t(10, 10), t(12, 10), 70.0, False, 2),
        ("L3", "G9003", "A6-AAA", "DOH", "SHJ", t(13), t(14), t(13), t(14), 0.0, True, 3),
    ]
    out = path / "history_flights.parquet"
    con = duckdb.connect()
    con.execute(
        "CREATE TABLE h (flight_id VARCHAR, flight_number VARCHAR, tail VARCHAR, origin VARCHAR, destination VARCHAR, "
        "std TIMESTAMP, sta TIMESTAMP, atd TIMESTAMP, ata TIMESTAMP, dep_dly DOUBLE, next_from_same_station BOOLEAN, "
        "leg_no INTEGER, operated BOOLEAN)"
    )
    con.executemany("INSERT INTO h VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, TRUE)", rows)
    con.execute(f"COPY h TO '{out}' (FORMAT parquet)")
    return out


def test_replays_primary_delay_and_scores_knock_on(tmp_path: Path) -> None:
    chains = load_chains(_write(tmp_path))
    turns = TurnTimes(timedelta(minutes=40))
    evts = events(chains, turns)

    assert [(e.flight_id, [n.flight_id for n in nxt]) for e, nxt in evts] == [("L1", ["L2"])]  # L3: chain broken

    s = score(evts, turns)["all_next_legs"]
    # L1 arrives 09:30, + 40 min turn -> L2 leaves 10:10: predicted 70 min, actual 70 min
    assert s["legs"] == 1
    assert s["mean_abs_error_min"] == 0
    assert s["precision"] == 1
    assert s["recall"] == 1

    baseline = score(evts, None)["all_next_legs"]
    assert baseline["recall"] == 0
    assert baseline["mean_abs_error_min"] == 70
