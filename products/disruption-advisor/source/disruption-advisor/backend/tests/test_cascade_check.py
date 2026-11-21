"""Cascade formula check: next departure = max(STD, previous arrival + 40 min) against what really happened."""

import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

import duckdb

from app import cascade_check as cc

T0 = datetime(2026, 11, 10, 6, 0)


def leg(
    tail: str, flt: str, origin: str, dest: str, std: datetime, sta_min: int, dep_delay: int, arr_delay: int
) -> tuple[Any, ...]:
    sta = std + timedelta(minutes=sta_min)
    return (
        tail,
        flt,
        origin,
        dest,
        std,
        sta,
        std + timedelta(minutes=dep_delay),
        sta + timedelta(minutes=arr_delay),
        True,
        False,
    )


def write_history(path: Path, legs: list[tuple[Any, ...]]) -> Path:
    ops = path / "ops"
    ops.mkdir(parents=True, exist_ok=True)
    con = duckdb.connect()
    con.execute(
        "CREATE TABLE h (tail VARCHAR, flight_number VARCHAR, origin VARCHAR, destination VARCHAR, std TIMESTAMP, "
        "sta TIMESTAMP, atd TIMESTAMP, ata TIMESTAMP, operated BOOLEAN, diverted BOOLEAN)"
    )
    con.executemany("INSERT INTO h VALUES (?,?,?,?,?,?,?,?,?,?)", legs)
    con.execute(f"COPY h TO '{ops}/history_flights.parquet' (FORMAT parquet)")
    return ops


def test_formula_and_kpis_on_a_small_history(tmp_path: Path) -> None:
    legs = []
    # A: previous arrives 30 min late, next STD 20 min after STA -> formula ETD = STA+30+40 -> knock-on 50; actual 60
    legs += [
        leg("A6-A", "G9001", "SHJ", "CAI", T0, 180, 0, 30),
        leg("A6-A", "G9002", "CAI", "SHJ", T0 + timedelta(minutes=200), 180, 60, 0),
    ]
    # B: arrives on time with a 90 min turn -> formula says no knock-on: not a cascade pair
    legs += [
        leg("A6-B", "G9003", "SHJ", "DEL", T0, 180, 0, 0),
        leg("A6-B", "G9004", "DEL", "SHJ", T0 + timedelta(minutes=270), 180, 0, 0),
    ]
    # C: formula knock-on 45, actual 0 (over-estimate by 45 > 15)
    legs += [
        leg("A6-C", "G9005", "SHJ", "BOM", T0, 180, 0, 25),
        leg("A6-C", "G9006", "BOM", "SHJ", T0 + timedelta(minutes=200), 180, 0, 0),
    ]
    # D: extreme outlier (actual knock-on 700 min): listed apart, left out of the figures
    legs += [
        leg("A6-D", "G9007", "SHJ", "NBO", T0, 180, 0, 20),
        leg("A6-D", "G9008", "NBO", "SHJ", T0 + timedelta(minutes=200), 180, 700, 0),
    ]
    # E: different station (aircraft repositioned): not a pair
    legs += [
        leg("A6-E", "G9009", "SHJ", "DOH", T0, 180, 0, 60),
        leg("A6-E", "G9010", "RUH", "SHJ", T0 + timedelta(minutes=200), 180, 80, 0),
    ]
    ops = write_history(tmp_path, legs)

    out = cc.run(ops)
    card = json.loads((ops / "cascade_check.json").read_text())
    assert out == {"pairs": 2, "excluded": 1}
    assert [r["flight"] for r in card["rows"]] == ["G9002", "G9006"]
    a, c = card["rows"]
    assert (a["formula_ko"], a["actual_ko"], a["delta"]) == (50, 60, 10)
    assert (c["formula_ko"], c["actual_ko"], c["delta"]) == (45, 0, -45)
    assert a["formula_etd"] == (T0 + timedelta(minutes=200 + 50)).strftime("%H:%M")
    k = card["kpis"]
    assert k["pairs"] == 2
    assert k["mean_delta"] == -17.5
    assert k["within_15"] == 1
    assert k["underestimates"] == 0
    assert k["overestimates"] == 1
    assert sum(b["count"] for b in card["histogram"]) == 2
    assert [e["flight"] for e in card["excluded"]] == ["G9008"]
    assert "40 min" in card["formula"]


def test_pairs_older_than_a_month_are_left_out(tmp_path: Path) -> None:
    old = T0 - timedelta(days=45)
    legs = [
        leg("A6-A", "G9001", "SHJ", "CAI", old, 180, 0, 30),
        leg("A6-A", "G9002", "CAI", "SHJ", old + timedelta(minutes=200), 180, 60, 0),
        leg("A6-B", "G9003", "SHJ", "CAI", T0, 180, 0, 30),
        leg("A6-B", "G9004", "CAI", "SHJ", T0 + timedelta(minutes=200), 180, 60, 0),
    ]
    ops = write_history(tmp_path, legs)
    cc.run(ops)
    card = json.loads((ops / "cascade_check.json").read_text())
    assert [r["flight"] for r in card["rows"]] == ["G9004"]
