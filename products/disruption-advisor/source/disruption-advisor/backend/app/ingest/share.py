"""Shareable bookings: every booking row (Oct 2025 - Mar 2027) without passenger names.

Since 2026-11-21 the ingest stores bookings in this name-free format already (``raw/bookings``: names replaced by
customer_key and the synthetic passenger ID, passport and national ID the app uses), so the export is a copy with a
README. Output, partitioned by departure month:

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
    source, out = data_dir / "raw" / "bookings", data_dir / "share"
    if not any(source.glob("dep_month=*")):
        raise FileNotFoundError(f"{source} has no name-free bookings: run the ingest first (python -m app.ingest)")
    if (out / "bookings").exists():
        shutil.rmtree(out / "bookings")
    out.mkdir(parents=True, exist_ok=True)
    shutil.copytree(source, out / "bookings")
    rows, pnrs, persons, missing = duckdb.connect().execute(
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
