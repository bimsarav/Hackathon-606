"""Stage 1 of the ingest: convert every raw airline extract to typed Parquet (engineering standards §9.25).

All later work reads these Parquet files, never the raw CSV/Excel. Nothing here edits the input files.

Raw inputs (folder ``INPUT_DIR``):
  Past & Future Booking Data.zip      18 monthly CSVs in nested zips, Latin-1, ~28M rows
  Flight Rotation.xls                 rotation / movement extract (UTC)
  Flight_Punctuality_Jan-Nov_2026_Combined.xlsx
  Flight Inventory.csv                seat allocation per flight and booking class
  Flight Schedule.csv                 seasonal schedule (times UTC despite the *_LOCAL names, PO answer Q9)
  Connection Time.xlsx                hub MCT per origin/hub/destination

Outputs (folder ``<DATA_DIR>/raw``):
  bookings/dep_year=YYYY/*.parquet    partitioned by departure year, sorted by departure time, zstd
  rotation.parquet, punctuality.parquet, inventory.parquet, schedule.parquet, mct.parquet
  bookings_rejects.txt                malformed lines (wrong field count or unterminated quote)
"""

from __future__ import annotations

import csv
import io
import logging
import os
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
    target = out_dir / "bookings"
    con = duckdb.connect()
    con.execute(f"SET temp_directory='{work_dir / 'duckdb_tmp'}'")
    con.execute(f"SET memory_limit='{os.environ.get('INGEST_MEMORY_LIMIT', '4GB')}'")  # spills to disk beyond this
    con.execute(f"""
        COPY (
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
            SRC_FILE AS src_file,
            year(try_strptime(EST_TIME_DEPARTURE_ZULU, '%Y-%m-%d %H:%M:%S')) AS dep_year
          FROM read_csv('{clean_dir}/*.csv', header = true, all_varchar = true)
          ORDER BY dep_utc, flight_number
        ) TO '{target}' (FORMAT parquet, COMPRESSION zstd, PARTITION_BY (dep_year), OVERWRITE_OR_IGNORE)
    """)
    for f in clean_dir.glob("*.csv"):
        f.unlink()
    return stats


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
        with tempfile.TemporaryDirectory(dir=data_dir) as work:
            result["bookings"] = convert_bookings(input_dir, out_dir, Path(work))
    return result
