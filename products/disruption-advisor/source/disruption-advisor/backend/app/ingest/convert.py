"""Stage 1 of the ingest: convert every raw airline extract to typed Parquet (engineering standards §9.25).

All later work reads these Parquet files, never the raw CSV/Excel. Nothing here edits the input files.

Raw inputs (folder ``INPUT_DIR``):
  parquet/raw/bookings/dep_month=YYYY-MM/*.parquet
                                      bookings already in the name-free format below (supplied 2026-11-21); used
                                      as they are when present, otherwise:
  Past & Future Booking Data.zip      18 monthly CSVs in nested zips, Latin-1, ~28M rows
  Flight Rotation.xls                 rotation / movement extract (UTC)
  Flight_Punctuality_Jan-Nov_2026_Combined.xlsx
  Flight Inventory.csv                seat allocation per flight and booking class
  Flight Schedule.csv                 seasonal schedule (times UTC despite the *_LOCAL names, PO answer Q9)
  Connection Time.xlsx                hub MCT per origin/hub/destination

Outputs (folder ``<DATA_DIR>/raw``):
  bookings/dep_month=YYYY-MM/*.parquet
                                      one row per passenger per segment, all statuses, WITHOUT names: first and
                                      last name are replaced by customer_key (hash of the name) and a synthetic
                                      identity (passenger_id, passport_number_synthetic, national_id_synthetic,
                                      identity_rule); partitioned by departure month, sorted, zstd
  rotation.parquet, punctuality.parquet, inventory.parquet, schedule.parquet, mct.parquet
  bookings_rejects.txt                malformed lines (wrong field count or unterminated quote)
"""

from __future__ import annotations

import csv
import io
import logging
import os
import shutil
import tempfile
import zipfile
from collections.abc import Iterator
from datetime import datetime
from pathlib import Path
from typing import Any

import duckdb
import pyarrow as pa
import pyarrow.parquet as pq
from python_calamine import CalamineWorkbook

log = logging.getLogger(__name__)

BOOKINGS_ZIP = "Past & Future Booking Data.zip"
ROTATION_XLS = "Flight Rotation.xls"
PUNCTUALITY_XLSX = "Flight_Punctuality_Jan-Nov_2026_Combined.xlsx"
INVENTORY_CSV = "Flight Inventory.csv"
SCHEDULE_CSV = "Flight Schedule.csv"
MCT_XLSX = "Connection Time.xlsx"

_YN = "CASE WHEN {c} = 'Y' THEN TRUE WHEN {c} = 'N' THEN FALSE END"


def _monthly_booking_lines(zip_path: Path) -> Iterator[tuple[str, Iterator[str]]]:
    """Yield (month tag, decoded lines) for each monthly CSV inside the nested zip."""
    outer = zipfile.ZipFile(zip_path)
    for name in sorted(n for n in outer.namelist() if n.endswith(".csv.zip") and not n.startswith("__MACOSX")):
        inner = zipfile.ZipFile(io.BytesIO(outer.read(name)))
        member = inner.namelist()[0]
        with inner.open(member) as raw:
            yield member.removesuffix(".csv"), io.TextIOWrapper(raw, encoding="latin-1", newline="")


def convert_bookings(input_dir: Path, out_dir: Path, work_dir: Path) -> dict[str, int]:
    """Clean line by line, then write typed, partitioned, sorted Parquet in one DuckDB COPY."""
    clean_dir = work_dir / "bookings_clean"
    clean_dir.mkdir(parents=True, exist_ok=True)
    stats = {"loaded": 0, "rejected": 0}
    with open(out_dir / "bookings_rejects.txt", "w", encoding="utf-8") as rejects:
        for tag, lines in _monthly_booking_lines(input_dir / BOOKINGS_ZIP):
            header: list[str] | None = None
            with open(clean_dir / f"{tag}.csv", "w", encoding="utf-8", newline="") as out:
                writer = csv.writer(out)
                for raw_line in lines:
                    line = raw_line.rstrip("\r\n")
                    if not line:
                        continue
                    try:
                        record = next(csv.reader([line]))
                    except csv.Error:
                        record = []
                    if header is None:
                        header = record
                        writer.writerow([*header, "SRC_FILE"])
                    elif len(record) == len(header) and line.count('"') % 2 == 0:
                        writer.writerow([*record, tag])
                        stats["loaded"] += 1
                    else:
                        stats["rejected"] += 1
                        rejects.write(f"{tag}\t{line[:300]}\n")
            log.info("bookings month cleaned", extra={"month": tag})
    con = duckdb.connect(str(work_dir / "bookings.duckdb"))  # names stay in this temporary database only
    con.execute(f"SET temp_directory='{work_dir / 'duckdb_tmp'}'")
    con.execute(f"SET memory_limit='{os.environ.get('INGEST_MEMORY_LIMIT', '4GB')}'")  # spills to disk beyond this
    con.execute(f"""
        CREATE TABLE b AS
          SELECT
            PNR AS pnr,
            try_strptime(BOOKING_TIMESTAMP, '%Y-%m-%d %H:%M:%S') AS booking_ts,
            SALES_CHANNEL AS sales_channel,
            RES_STATUS AS res_status,
            IS_LMS_MEMBER = 'Y' AS is_lms_member,
            PAX_TYPE_CODE AS pax_type,
            FIRST_NAME AS first_name,
            LAST_NAME AS last_name,
            FLIGHT_NUMBER AS flight_number,
            try_strptime(EST_TIME_DEPARTURE_ZULU, '%Y-%m-%d %H:%M:%S') AS dep_utc,
            SEGMENT_CODE AS segment_code,
            split_part(SEGMENT_CODE, '/', 1) AS origin,
            split_part(SEGMENT_CODE, '/', 2) AS destination,
            FLIGHT_STATUS AS flight_status,
            SEG_STATUS AS seg_status,
            BOOKING_CODE AS booking_code,
            PAX_STATUS AS pax_status,
            try_cast(TOTAL_FARE AS DOUBLE) AS total_fare,
            try_cast(TOTAL_SURCHARGES AS DOUBLE) AS total_surcharges,
            try_cast(TOTAL_TAXES AS DOUBLE) AS total_taxes,
            try_cast(ANCI_CHARGES AS DOUBLE) AS anci_charges,
            try_cast(INSURANCE_CHARGES AS DOUBLE) AS insurance_charges,
            try_cast(BAGGAGE_WEIGHT AS INTEGER) AS baggage_kg,
            MEALS AS meals,
            SEAT_CODE AS seat_code,
            INSURANCE_POLICY IS NOT NULL AS has_insurance,
            {_YN.format(c="TNFSEG")} AS tnf_seg,
            {_YN.format(c="MODSEG")} AS mod_seg,
            {_YN.format(c="CNXSEG")} AS cnx_seg,
            SRC_FILE AS src_file
          FROM read_csv('{clean_dir}/*.csv', header = true, all_varchar = true)""")
    stats["persons"] = write_bookings_without_names(con, out_dir / "bookings")
    for f in clean_dir.glob("*.csv"):
        f.unlink()
    return stats


# Synthetic identity (the extracts have no passenger ID or documents). A name is one person unless it is common
# (more than COMMON_NAME_BOOKINGS bookings); then its bookings are split by home airport (origin of the booking's
# first leg) and grouped about BOOKINGS_PER_PERSON per person, so repeat travellers keep one ID across bookings.
# Documents are unique: the serial is a shuffled rank of the person.
COMMON_NAME_BOOKINGS = 60
BOOKINGS_PER_PERSON = 6
BOOKING_COLUMNS = frozenset(
    {
        "pnr",
        "booking_ts",
        "res_status",
        "is_lms_member",
        "pax_type",
        "flight_number",
        "dep_utc",
        "origin",
        "destination",
        "flight_status",
        "seg_status",
        "booking_code",
        "total_fare",
        "anci_charges",
        "baggage_kg",
        "meals",
        "seat_code",
        "sales_channel",
        "customer_key",
        "passenger_id",
        "passport_number_synthetic",
        "national_id_synthetic",
        "identity_rule",
        "dep_month",
    }
)


def write_bookings_without_names(con: duckdb.DuckDBPyConnection, target: Path) -> int:
    """Table ``b`` (typed bookings with names) -> name-free bookings by departure month. Returns persons."""
    con.execute(f"""
        CREATE TEMP TABLE ident AS
        WITH n AS (SELECT pnr, lower(trim(first_name)) || '|' || lower(trim(last_name)) AS name_key, origin, dep_utc
                   FROM b WHERE first_name IS NOT NULL AND last_name IS NOT NULL),
             home AS (SELECT pnr, arg_min(origin, (dep_utc, origin)) AS home FROM n GROUP BY 1),  -- ties: lowest code
             people AS (SELECT DISTINCT pnr, name_key FROM n),
             named AS (SELECT p.*, h.home, count(*) OVER (PARTITION BY p.name_key) AS n_name,
                              count(*) OVER (PARTITION BY p.name_key, h.home) AS n_home
                       FROM people p JOIN home h USING (pnr)),
             seed AS (SELECT *, n_name > {COMMON_NAME_BOOKINGS} AS common,
                             CASE WHEN n_name > {COMMON_NAME_BOOKINGS}
                                  THEN substr(sha256(name_key), 1, 16) || '|' || home || '|' ||
                                       ((('0x' || substr(md5('bk|' || pnr), 1, 8))::UBIGINT)
                                        % greatest(ceil(n_home / {BOOKINGS_PER_PERSON})::UBIGINT, 1))::VARCHAR
                                  ELSE substr(sha256(name_key), 1, 16) END AS person_seed
                      FROM named),
             k AS (SELECT person_seed, row_number() OVER (ORDER BY sha256('pp|' || person_seed)) AS k
                   FROM (SELECT DISTINCT person_seed FROM seed))
        SELECT s.pnr, s.name_key, substr(sha256(s.name_key), 1, 16) AS customer_key,
               'PAX' || upper(substr(sha256('pid|' || s.person_seed), 1, 12)) AS passenger_id,
               chr(65 + (('0x' || substr(sha256('pp|' || s.person_seed), 1, 4))::INTEGER % 26)::INTEGER)
                   || lpad((10000000 + k.k)::VARCHAR, 8, '0') AS passport_number_synthetic,
               -- Emirates ID layout 784-YYYY-NNNNNNN-C (birth year, serial, check digit); demo format for everyone
               '784-' || (1955 + (('0x' || substr(sha256('ny|' || s.person_seed), 1, 4))::INTEGER % 50))::VARCHAR
                   || '-' || lpad(k.k::VARCHAR, 7, '0') || '-'
                   || ((('0x' || substr(sha256('nc|' || s.person_seed), 1, 2))::INTEGER % 10))::VARCHAR
                   AS national_id_synthetic,
               CASE WHEN s.common THEN 'common-name: split by home airport' ELSE 'one-person-per-name' END
                   AS identity_rule
        FROM seed s JOIN k USING (person_seed)""")
    con.execute(f"""
        COPY (
            SELECT b.* EXCLUDE (first_name, last_name),
                   strftime(b.dep_utc, '%Y-%m') AS dep_month,
                   i.customer_key, i.passenger_id, i.passport_number_synthetic, i.national_id_synthetic,
                   i.identity_rule
            FROM b LEFT JOIN ident i
              ON i.pnr = b.pnr AND i.name_key = lower(trim(b.first_name)) || '|' || lower(trim(b.last_name))
            ORDER BY dep_month, b.dep_utc, b.flight_number, b.pnr
        ) TO '{target}' (FORMAT parquet, COMPRESSION zstd, PARTITION_BY (dep_month), OVERWRITE_OR_IGNORE)""")
    row = con.execute("SELECT count(DISTINCT passenger_id) FROM ident").fetchone()
    return int(row[0]) if row else 0


def supplied_bookings(input_dir: Path) -> Path | None:
    """Bookings already in the name-free format (INPUT_DIR/parquet/raw/bookings/dep_month=*), if supplied."""
    folder = input_dir / "parquet" / "raw" / "bookings"
    return folder if any(folder.glob("dep_month=*/*.parquet")) else None


def copy_supplied_bookings(source: Path, out_dir: Path) -> dict[str, int]:
    """Check the supplied name-free bookings have every column the build needs, then copy them in."""
    con = duckdb.connect()
    glob = f"read_parquet('{source}/*/*.parquet', hive_partitioning = true)"
    columns = {r[0] for r in con.execute(f"DESCRIBE SELECT * FROM {glob}").fetchall()}
    missing = sorted(BOOKING_COLUMNS - columns)
    if missing:
        raise ValueError(f"supplied bookings in {source} lack the columns {missing}")
    if {"first_name", "last_name"} & columns:
        raise ValueError(f"supplied bookings in {source} still contain passenger names")
    target = out_dir / "bookings"
    if target.exists():
        shutil.rmtree(target)
    shutil.copytree(source, target)
    row = con.execute(f"SELECT count(*), count(DISTINCT passenger_id) FROM {glob}").fetchone() or (0, 0)
    return {"loaded": int(row[0]), "rejected": 0, "persons": int(row[1]), "supplied_parquet": 1}


def _sheet_table(path: Path, sheet: str | None = None) -> pa.Table:
    """Read one worksheet as a pyarrow table; header row → snake_case names; cells keep their native types."""
    wb = CalamineWorkbook.from_path(str(path))
    rows = wb.get_sheet_by_name(sheet or wb.sheet_names[0]).to_python()
    header = [
        str(h).strip().lower().replace(".", "_").replace(" ", "_").replace("(", "").replace(")", "") for h in rows[0]
    ]
    columns: dict[str, list[Any]] = {h: [] for h in header}
    for row in rows[1:]:
        if not any(v not in ("", None) for v in row):
            continue
        for h, v in zip(header, row, strict=False):
            columns[h].append(None if v == "" else v)
    return pa.table({h: _column(v) for h, v in columns.items()})


def _column(values: list[Any]) -> pa.Array:
    """Typed column: all datetimes → timestamp, all numbers → float64, else string (IDs keep leading zeros)."""
    present = [v for v in values if v is not None]
    if present and all(isinstance(v, datetime) for v in present):
        return pa.array(values, type=pa.timestamp("s"))
    if present and all(isinstance(v, (int, float)) and not isinstance(v, bool) for v in present):
        return pa.array(values, type=pa.float64())
    return pa.array([None if v is None else str(v) for v in values], type=pa.string())


def convert_excel(input_dir: Path, out_dir: Path) -> dict[str, int]:
    counts = {}
    for src, name in ((ROTATION_XLS, "rotation"), (PUNCTUALITY_XLSX, "punctuality"), (MCT_XLSX, "mct")):
        table = _sheet_table(input_dir / src)
        pq.write_table(table, out_dir / f"{name}.parquet", compression="zstd")
        counts[name] = table.num_rows
    return counts


def convert_csvs(input_dir: Path, out_dir: Path) -> dict[str, int]:
    con = duckdb.connect()
    con.execute(f"""
        COPY (
          SELECT flight_number,
                 strptime(departure_date_time_local, '%Y-%m-%d %H:%M:%S.%g') AS dep_local,
                 strptime(departure_date_time_zulu, '%Y-%m-%d %H:%M:%S.%g') AS dep_utc,
                 aircraft_model, adult_capacity::INTEGER AS adult_capacity,
                 curtail_oversell_count::INTEGER AS curtail_oversell_count, curtail_oversell,
                 bc_code AS booking_code, allocated_seats::INTEGER AS allocated_seats,
                 available_seats::INTEGER AS available_seats
          FROM read_csv('{input_dir / INVENTORY_CSV}', header = true, all_varchar = true, ignore_errors = true)
          ORDER BY dep_utc, flight_number, booking_code
        ) TO '{out_dir / "inventory.parquet"}' (FORMAT parquet, COMPRESSION zstd)
    """)
    con.execute(f"""
        COPY (
          SELECT FLIGHT_NUMBER AS flight_number,
                 strptime(SCHEDULE_START, '%Y-%m-%d')::DATE AS schedule_start,
                 strptime(SCHEDULE_END, '%Y-%m-%d')::DATE AS schedule_end,
                 FREQUENCY AS frequency, ORIGIN AS origin, DESTINATION AS destination,
                 DEP_TIME_LOCAL AS dep_time_utc, ARR_TIME_LOCAL AS arr_time_utc,
                 starts_with(FLIGHT_NUMBER, '02') AS is_bus
          FROM read_csv('{input_dir / SCHEDULE_CSV}', header = true, all_varchar = true, ignore_errors = true)
        ) TO '{out_dir / "schedule.parquet"}' (FORMAT parquet, COMPRESSION zstd)
    """)
    counts: dict[str, int] = {}
    for name, src in (("inventory", INVENTORY_CSV), ("schedule", SCHEDULE_CSV)):
        written = con.execute(f"SELECT count(*) FROM '{out_dir / f'{name}.parquet'}'").fetchone()[0]  # type: ignore[index]
        with open(input_dir / src, "rb") as fh:
            data_lines = sum(1 for line in fh if line.strip()) - 1
        counts[name] = written
        counts[f"{name}_rejected"] = data_lines - written  # malformed rows (e.g. a truncated last line) are skipped
    return counts


def run(input_dir: Path, data_dir: Path, skip_bookings: bool = False) -> dict[str, Any]:
    out_dir = data_dir / "raw"
    out_dir.mkdir(parents=True, exist_ok=True)
    result: dict[str, Any] = {}
    result.update(convert_excel(input_dir, out_dir))
    result.update(convert_csvs(input_dir, out_dir))
    if not skip_bookings:
        supplied = supplied_bookings(input_dir)
        if supplied is not None:
            result["bookings"] = copy_supplied_bookings(supplied, out_dir)
        else:
            with tempfile.TemporaryDirectory(dir=data_dir) as work:
                if (out_dir / "bookings").exists():
                    shutil.rmtree(out_dir / "bookings")  # an older layout (dep_year) must not stay next to the new
                result["bookings"] = convert_bookings(input_dir, out_dir, Path(work))
    return result
