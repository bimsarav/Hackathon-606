"""Shareable bookings: every booking row (Oct 2025 - Mar 2027) without passenger names.

Names are replaced by the synthetic identity built by the ingest (``ops/passenger_identity.parquet``): the same
passenger ID, passport and national ID the app uses. Output, partitioned by departure month:

  DATA_DIR/share/bookings/dep_month=YYYY-MM/*.parquet
  DATA_DIR/share/README.md

The folder is for a shared drive, never for Git (size, and it is still airline booking data).
Run after the ingest:  DATA_DIR=/data python -m app.ingest.share
"""

from __future__ import annotations

import os
import shutil
import sys
from pathlib import Path

import duckdb

README = """# Bookings without names (Oct 2025 - Mar 2027)

One row per passenger per segment, all statuses, as in the airline extract, except:
- `first_name` and `last_name` are removed;
- added: `customer_key` (hash of the name, as in the app), `passenger_id`, `passport_number_synthetic`,
  `national_id_synthetic`, `identity_rule`. These are SYNTHETIC: the extract has no passenger ID or documents.
  A name is one person unless it is very common; then bookings are split by home airport.

Partitioned by departure month (`dep_month=YYYY-MM`). Read with DuckDB:
  SELECT * FROM read_parquet('bookings/*/*.parquet', hive_partitioning = true)

Rows: {rows:,} · bookings (PNR): {pnrs:,} · synthetic persons: {persons:,}
Do not commit to Git. Built by `python -m app.ingest.share`.
"""


def export(data_dir: Path) -> dict[str, int]:
    raw, ops, out = data_dir / "raw", data_dir / "ops", data_dir / "share"
    identity = ops / "passenger_identity.parquet"
    if not identity.exists():
        raise FileNotFoundError(f"{identity} not found: run the ingest first (python -m app.ingest)")
    if (out / "bookings").exists():
        shutil.rmtree(out / "bookings")
    out.mkdir(parents=True, exist_ok=True)
    c = duckdb.connect()
    c.execute(f"""
        COPY (
            SELECT b.* EXCLUDE (first_name, last_name, dep_year),
                   strftime(b.dep_utc, '%Y-%m') AS dep_month,
                   i.customer_key, i.passenger_id, i.passport_number_synthetic, i.national_id_synthetic,
                   i.identity_rule
            FROM read_parquet('{raw}/bookings/*/*.parquet', hive_partitioning = true) b
            LEFT JOIN '{identity}' i
              ON i.pnr = b.pnr
             AND i.customer_key = substr(sha256(lower(trim(b.first_name)) || '|' || lower(trim(b.last_name))), 1, 16)
            ORDER BY dep_month, b.dep_utc, b.flight_number, b.pnr
        ) TO '{out / "bookings"}' (FORMAT parquet, COMPRESSION zstd, PARTITION_BY (dep_month))""")
    rows, pnrs, persons, missing = c.execute(
        f"""SELECT count(*), count(DISTINCT pnr), count(DISTINCT passenger_id), count(*) - count(passenger_id)
            FROM read_parquet('{out / "bookings"}/*/*.parquet', hive_partitioning = true)"""
    ).fetchone() or (0, 0, 0, 0)
    (out / "README.md").write_text(README.format(rows=rows, pnrs=pnrs, persons=persons))
    return {"rows": rows, "pnrs": pnrs, "persons": persons, "rows_without_identity": missing}


def main() -> int:
    data_dir = Path(os.environ.get("DATA_DIR", "/data"))
    try:
        print(export(data_dir))
    except FileNotFoundError as exc:
        print(exc, file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
