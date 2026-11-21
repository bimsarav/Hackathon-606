"""Extracts into PostgreSQL (schema `extracts`): types, row counts, skip when unchanged, reload, modes."""

from datetime import datetime
from pathlib import Path

import psycopg
import pyarrow as pa
import pyarrow.parquet as pq
import pytest
from alembic.config import Config

from app.ingest import to_postgres as tp


@pytest.fixture
def raw(tmp_path: Path) -> Path:
    r = tmp_path / "raw"
    r.mkdir()
    small = {
        "rotation": {"reg": ["A6-AAA", "A6-BBB"], "sai": ["G9001", "G9002"],
                     "std": [datetime(2026, 11, 20, 8), datetime(2026, 11, 20, 9)], "pax": ["150", None]},
        "schedule": {"flight_number": ["G9001"], "is_bus": [False]},
        "inventory": {"flight_number": ["G9001"], "dep_utc": [datetime(2026, 11, 20, 8)], "adult_capacity": [174]},
        "mct": {"ond_code": ["KHI/SHJ/CAI"], "min_conn_time_mins": [55.0]},
        "punctuality": {"reg": ["A6-AAA"], "sai": ["G9001"], "dep_dly": [12.0], "dlycode": ['5min-93L, "quoted"']},
    }  # fmt: skip
    for name, cols in small.items():
        pq.write_table(pa.table(cols), r / f"{name}.parquet")
    for month, pnrs in (("2026-11", ["P1", "P2"]), ("2026-12", ["P3"])):
        part = r / "bookings" / f"dep_month={month}"
        part.mkdir(parents=True)
        pq.write_table(
            pa.table({"pnr": pnrs, "flight_number": ["G9001"] * len(pnrs), "customer_key": ["k"] * len(pnrs),
                      "passenger_id": ["PAX1"] * len(pnrs), "dep_utc": [datetime(2026, 11, 20, 8)] * len(pnrs),
                      "total_fare": [500.0] * len(pnrs), "meals": ["", None][: len(pnrs)]}),
            part / "data_0.parquet",
        )  # fmt: skip
    return r


@pytest.fixture
def url(alembic_config: Config) -> str:
    value = alembic_config.get_main_option("sqlalchemy.url")
    assert value
    with psycopg.connect(tp.conninfo(value), autocommit=True) as pg:
        pg.execute("DROP SCHEMA IF EXISTS extracts CASCADE")
    return value


def _query(url: str, q: str) -> list[tuple[object, ...]]:
    with psycopg.connect(tp.conninfo(url)) as pg:
        return pg.execute(q).fetchall()


def _pairs(rows: list[tuple[object, ...]]) -> dict[object, object]:
    return {r[0]: r[1] for r in rows}


def test_all_extracts_are_loaded_with_types_and_logged(url: str, raw: Path) -> None:
    result = tp.load(url, raw.parent, "all", "fp-1")
    assert result["loaded"] == {"rotation": 2, "schedule": 1, "inventory": 1, "mct": 1, "punctuality": 1, "bookings": 3}
    types = _pairs(
        _query(
            url,
            """SELECT column_name, data_type FROM information_schema.columns
                                WHERE table_schema = 'extracts' AND table_name = 'bookings'""",
        )
    )
    assert types["dep_utc"] == "timestamp without time zone"
    assert types["total_fare"] == "double precision"
    assert types["dep_month"] == "text"
    assert "first_name" not in types
    assert _query(url, "SELECT dlycode FROM extracts.punctuality") == [('5min-93L, "quoted"',)]
    assert _query(url, "SELECT count(*) FROM extracts.rotation WHERE pax IS NULL") == [(1,)]
    assert _query(url, "SELECT meals FROM extracts.bookings WHERE pnr = 'P1'") == [("",)]  # empty string kept
    assert _query(url, "SELECT count(*) FROM extracts.bookings WHERE meals IS NULL") == [(1,)]
    log = _pairs(_query(url, "SELECT table_name, row_count FROM extracts.load_log"))
    assert log["bookings"] == 3
    indexes = {r[0] for r in _query(url, "SELECT indexname FROM pg_indexes WHERE schemaname = 'extracts'")}
    assert {"bookings_ix0", "bookings_ix1", "inventory_ix0"} <= indexes


def test_unchanged_sources_are_skipped_and_changed_ones_reloaded(url: str, raw: Path) -> None:
    tp.load(url, raw.parent, "all", "fp-1")
    again = tp.load(url, raw.parent, "all", "fp-1")
    assert again["loaded"] == {}
    assert len(again["unchanged"]) == 6
    pq.write_table(pa.table({"flight_number": ["G9001", "G9003"], "is_bus": [False, True]}), raw / "schedule.parquet")
    changed = tp.load(url, raw.parent, "all", "fp-2")
    assert changed["loaded"]["schedule"] == 2
    assert _query(url, "SELECT count(*) FROM extracts.schedule") == [(2,)]


def test_modes(url: str, raw: Path) -> None:
    assert tp.load(url, raw.parent, "off", "fp-1")["loaded"] == {}
    result = tp.load(url, raw.parent, "no-bookings", "fp-1")
    assert "bookings" not in result["loaded"]
    assert len(result["loaded"]) == 5
    with pytest.raises(ValueError, match="EXTRACTS_TO_DB"):
        tp.tables_for("everything")
