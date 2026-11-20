"""Stage 1 bookings format (2026-11-21): name-free, synthetic identity, partitioned by departure month."""

from pathlib import Path

import duckdb
import pytest

from app.ingest import convert

ROWS = """
    ('P1', 'Ali', 'Khan',  'SHJ', 'KHI', TIMESTAMP '2026-11-20 05:00:00'),
    ('P1', 'Ali', 'Khan',  'KHI', 'SHJ', TIMESTAMP '2026-12-02 09:00:00'),
    ('P2', 'ALI ', 'khan', 'SHJ', 'CAI', TIMESTAMP '2027-01-10 07:00:00'),
    ('P3', 'Sara', 'Noor', 'SHJ', 'DOH', TIMESTAMP '2026-11-21 10:00:00'),
    ('P4', NULL,   NULL,   'SHJ', 'DOH', TIMESTAMP '2026-11-21 10:00:00')"""


def _bookings_with_names() -> duckdb.DuckDBPyConnection:
    con = duckdb.connect()
    con.execute(f"""CREATE TABLE b AS SELECT *, 'G9500' AS flight_number FROM (VALUES {ROWS})
                    AS t(pnr, first_name, last_name, origin, destination, dep_utc)""")
    return con


def _read(folder: Path) -> list[tuple[object, ...]]:
    return (
        duckdb.connect()
        .execute(
            f"""SELECT pnr, dep_month, customer_key, passenger_id, passport_number_synthetic, national_id_synthetic
            FROM read_parquet('{folder}/*/*.parquet', hive_partitioning = true) ORDER BY dep_utc"""
        )
        .fetchall()
    )


def test_bookings_are_written_without_names_by_month(tmp_path: Path) -> None:
    persons = convert.write_bookings_without_names(_bookings_with_names(), tmp_path / "bookings")
    columns = {
        r[0]
        for r in duckdb.connect()
        .execute(f"DESCRIBE SELECT * FROM read_parquet('{tmp_path}/bookings/*/*.parquet', hive_partitioning = true)")
        .fetchall()
    }
    assert not {"first_name", "last_name"} & columns
    assert sorted(p.name for p in (tmp_path / "bookings").iterdir()) == [
        "dep_month=2026-11",
        "dep_month=2026-12",
        "dep_month=2027-01",
    ]
    rows = {(r[0], r[1]): r for r in _read(tmp_path / "bookings")}
    ali_1, ali_2, ali_3 = rows["P1", "2026-11"], rows["P1", "2026-12"], rows["P2", "2027-01"]
    # the same (normalised) name is one person across bookings: same key, passenger ID and documents
    assert ali_1[2:] == ali_2[2:] == ali_3[2:]
    assert rows["P3", "2026-11"][3] != ali_1[3]
    assert rows["P3", "2026-11"][4] != ali_1[4]
    assert str(ali_1[3]).startswith("PAX")
    assert str(ali_1[5]).startswith("784-")
    assert rows["P4", "2026-11"][2:] == (None, None, None, None)  # no name: no identity, row kept
    assert persons == 2


def test_supplied_bookings_need_every_column_and_no_names(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    good = tmp_path / "in" / "parquet" / "raw" / "bookings"
    good.parent.mkdir(parents=True)
    convert.write_bookings_without_names(_bookings_with_names(), good)
    assert convert.supplied_bookings(tmp_path / "in") == good
    with pytest.raises(ValueError, match="lack the columns"):
        convert.copy_supplied_bookings(good, tmp_path / "out")  # the tiny sample lacks fares etc.

    named = tmp_path / "named"
    con = duckdb.connect()
    con.execute(f"""COPY (SELECT *, 'x' AS first_name FROM read_parquet('{good}/*/*.parquet',
                    hive_partitioning = true)) TO '{named}' (FORMAT parquet, PARTITION_BY (dep_month))""")
    monkeypatch.setattr(convert, "BOOKING_COLUMNS", frozenset({"pnr", "dep_month"}))
    with pytest.raises(ValueError, match="passenger names"):
        convert.copy_supplied_bookings(named, tmp_path / "out")
    result = convert.copy_supplied_bookings(good, tmp_path / "out")
    assert result["loaded"] == 5
    assert result["persons"] == 2
    assert any((tmp_path / "out" / "bookings").glob("dep_month=*/*.parquet"))


def test_no_supplied_bookings_means_convert_the_zip(tmp_path: Path) -> None:
    assert convert.supplied_bookings(tmp_path) is None


def test_identity_does_not_depend_on_row_order(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """A common name is split by home airport; a PNR with two first legs at the same minute must get one home."""
    monkeypatch.setattr(convert, "COMMON_NAME_BOOKINGS", 1)  # every repeated name counts as common
    monkeypatch.setattr(convert, "BOOKINGS_PER_PERSON", 1)
    rows = [
        "('T1', 'Ali', 'Khan', 'SHJ', 'KHI', TIMESTAMP '2026-03-06 03:05:00')",
        "('T1', 'Ali', 'Khan', 'DXB', 'KHI', TIMESTAMP '2026-03-06 03:05:00')",  # tie with the leg above
        "('T2', 'Ali', 'Khan', 'SHJ', 'DOH', TIMESTAMP '2026-04-01 10:00:00')",
        "('T3', 'Ali', 'Khan', 'DXB', 'CAI', TIMESTAMP '2026-05-01 10:00:00')",
    ]
    results = []
    for n, order in enumerate((rows, rows[::-1], rows[1:] + rows[:1])):
        con = duckdb.connect()
        con.execute(f"""CREATE TABLE b AS SELECT *, 'G9500' AS flight_number FROM (VALUES {", ".join(order)})
                        AS t(pnr, first_name, last_name, origin, destination, dep_utc)""")
        convert.write_bookings_without_names(con, tmp_path / f"run{n}")
        results.append(sorted(_read(tmp_path / f"run{n}")))
    assert results[0] == results[1] == results[2]
