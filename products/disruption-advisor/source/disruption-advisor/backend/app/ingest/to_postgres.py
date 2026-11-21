"""Load the airline extracts into PostgreSQL (schema ``extracts``), user request 2026-11-21.

The app keeps reading the typed Parquet (ADR 0005); this copy makes the same data queryable in PostgreSQL for
analysts and reports. Source: the stage-1 output in ``DATA_DIR/raw`` (already typed, bookings without names).

  extracts.rotation, schedule, inventory, mct, punctuality   always (small)
  extracts.bookings                                          27.9M rows, about 6-9 GB with indexes; skipped with
                                                             EXTRACTS_TO_DB=no-bookings
  extracts.load_log                                          one row per table: rows, source fingerprint, load time

EXTRACTS_TO_DB = all (default) | no-bookings | off. A table is reloaded only when its source changed (the ingest
fingerprint of the input files). Each table is built under a temporary name and swapped in one transaction, so
readers never see a half-loaded table. Run: python -m app.ingest.to_postgres (Compose service ``extracts-db``).
"""

from __future__ import annotations

import logging
import os
import sys
import tempfile
from collections.abc import Iterator
from pathlib import Path
from typing import Any

import duckdb
import psycopg
from psycopg import sql

log = logging.getLogger("ingest.to_postgres")

SCHEMA = "extracts"
SMALL_TABLES = ("rotation", "schedule", "inventory", "mct", "punctuality")
MODES = ("all", "no-bookings", "off")
NULL = "\\N"
PG_TYPES = {
    "VARCHAR": "text",
    "BOOLEAN": "boolean",
    "TINYINT": "smallint",
    "SMALLINT": "smallint",
    "INTEGER": "integer",
    "BIGINT": "bigint",
    "UBIGINT": "numeric",
    "FLOAT": "real",
    "DOUBLE": "double precision",
    "DATE": "date",
    "TIMESTAMP": "timestamp",
    "TIMESTAMP WITH TIME ZONE": "timestamptz",
}
INDEXES = {
    "bookings": (("pnr",), ("flight_number", "dep_utc"), ("customer_key",), ("passenger_id",)),
    "inventory": (("flight_number", "dep_utc"),),
    "rotation": (("reg", "std"),),
    "punctuality": (("reg",), ("sai",)),
}


def conninfo(database_url: str) -> str:
    """SQLAlchemy URL (postgresql+psycopg://...) -> libpq URL."""
    return database_url.replace("postgresql+psycopg://", "postgresql://", 1)


def tables_for(mode: str) -> tuple[str, ...]:
    if mode not in MODES:
        raise ValueError(f"EXTRACTS_TO_DB must be one of {MODES}, not {mode!r}")
    return () if mode == "off" else SMALL_TABLES + (() if mode == "no-bookings" else ("bookings",))


def _source(raw: Path, table: str) -> str:
    if table == "bookings":
        return f"read_parquet('{raw}/bookings/*/*.parquet', hive_partitioning = true)"
    return f"read_parquet('{raw}/{table}.parquet')"


def _columns(duck: duckdb.DuckDBPyConnection, source: str) -> list[tuple[str, str]]:
    return [
        (r[0], PG_TYPES.get(str(r[1]), "text")) for r in duck.execute(f"DESCRIBE SELECT * FROM {source}").fetchall()
    ]


def _chunks(duck: duckdb.DuckDBPyConnection, raw: Path, table: str, work: Path) -> Iterator[Path]:
    """CSV files to COPY: one per departure month for bookings (bounded temp space), one for the small tables."""
    source = _source(raw, table)
    parts = (
        [r[0] for r in duck.execute(f"SELECT DISTINCT dep_month FROM {source} ORDER BY 1").fetchall()]
        if table == "bookings"
        else [None]
    )
    for part in parts:
        where = "" if part is None else f" WHERE dep_month = '{part}'" if part else " WHERE dep_month IS NULL"
        path = work / f"{table}-{part or 'all'}.csv"
        duck.execute(f"COPY (SELECT * FROM {source}{where}) TO '{path}' (FORMAT csv, HEADER false, NULLSTR '{NULL}')")
        yield path
        path.unlink()


def _loaded(pg: psycopg.Connection[Any], table: str) -> str | None:
    row = pg.execute(
        sql.SQL("SELECT source_fingerprint FROM {}.load_log WHERE table_name = %s").format(sql.Identifier(SCHEMA)),
        [table],
    ).fetchone()
    return str(row[0]) if row else None


def load_table(
    pg: psycopg.Connection[Any], duck: duckdb.DuckDBPyConnection, raw: Path, table: str, fingerprint: str
) -> int:
    """(Re)load one table under a temporary name, then swap it in and log it, in one transaction."""
    columns = _columns(duck, _source(raw, table))
    staging = sql.Identifier(f"{table}__loading")
    target = sql.Identifier(table)
    schema = sql.Identifier(SCHEMA)
    column_list = sql.SQL(", ").join(sql.Identifier(name) for name, _ in columns)
    with pg.transaction():
        pg.execute(sql.SQL("DROP TABLE IF EXISTS {}.{}").format(schema, staging))
        pg.execute(
            sql.SQL("CREATE TABLE {}.{} ({})").format(
                schema,
                staging,
                sql.SQL(", ").join(sql.SQL("{} {}").format(sql.Identifier(n), sql.SQL(t)) for n, t in columns),
            )
        )
        with tempfile.TemporaryDirectory(dir=raw.parent) as tmp:
            for path in _chunks(duck, raw, table, Path(tmp)):
                with (
                    pg.cursor().copy(
                        sql.SQL("COPY {}.{} ({}) FROM STDIN (FORMAT csv, NULL {})").format(
                            schema, staging, column_list, sql.Literal(NULL)
                        )
                    ) as copy,
                    open(path, "rb") as f,
                ):
                    while block := f.read(1 << 20):
                        copy.write(block)
        rows = int(pg.execute(sql.SQL("SELECT count(*) FROM {}.{}").format(schema, staging)).fetchone()[0])  # type: ignore[index]
        for i, cols in enumerate(INDEXES.get(table, ())):
            pg.execute(
                sql.SQL("CREATE INDEX {} ON {}.{} ({})").format(
                    sql.Identifier(f"{table}_ix{i}_loading"),
                    schema,
                    staging,
                    sql.SQL(", ").join(sql.Identifier(c) for c in cols),
                )
            )
        pg.execute(sql.SQL("DROP TABLE IF EXISTS {}.{}").format(schema, target))
        pg.execute(sql.SQL("ALTER TABLE {}.{} RENAME TO {}").format(schema, staging, target))
        for i, _ in enumerate(INDEXES.get(table, ())):
            pg.execute(
                sql.SQL("ALTER INDEX {}.{} RENAME TO {}").format(
                    schema, sql.Identifier(f"{table}_ix{i}_loading"), sql.Identifier(f"{table}_ix{i}")
                )
            )
        pg.execute(
            sql.SQL(
                """INSERT INTO {}.load_log (table_name, row_count, source_fingerprint, loaded_at)
                   VALUES (%s, %s, %s, now())
                   ON CONFLICT (table_name) DO UPDATE SET row_count = EXCLUDED.row_count,
                       source_fingerprint = EXCLUDED.source_fingerprint, loaded_at = EXCLUDED.loaded_at"""
            ).format(schema),
            [table, rows, fingerprint],
        )
    pg.execute(sql.SQL("ANALYZE {}.{}").format(schema, target))
    return rows


def load(database_url: str, data_dir: Path, mode: str, fingerprint: str) -> dict[str, Any]:
    """Load the extracts selected by `mode`; tables whose source is unchanged are skipped."""
    tables = tables_for(mode)
    result: dict[str, Any] = {"mode": mode, "loaded": {}, "unchanged": []}
    if not tables:
        return result
    raw = data_dir / "raw"
    duck = duckdb.connect()
    duck.execute(f"SET memory_limit='{os.environ.get('INGEST_MEMORY_LIMIT', '4GB')}'")
    with psycopg.connect(conninfo(database_url), autocommit=True) as pg:
        pg.execute(sql.SQL("CREATE SCHEMA IF NOT EXISTS {}").format(sql.Identifier(SCHEMA)))
        pg.execute(
            sql.SQL(
                """CREATE TABLE IF NOT EXISTS {}.load_log (table_name text PRIMARY KEY, row_count bigint NOT NULL,
                   source_fingerprint text NOT NULL, loaded_at timestamptz NOT NULL)"""
            ).format(sql.Identifier(SCHEMA))
        )
        for table in tables:
            if _loaded(pg, table) == fingerprint:
                result["unchanged"].append(table)
                continue
            log.info("loading extracts.%s", table)
            result["loaded"][table] = load_table(pg, duck, raw, table, fingerprint)
            log.info("extracts.%s: %s rows", table, result["loaded"][table])
    return result


def main() -> int:
    logging.basicConfig(level=os.environ.get("LOG_LEVEL", "INFO"), format="%(asctime)s %(levelname)s %(message)s")
    data_dir = Path(os.environ.get("DATA_DIR", "/data"))
    mode = os.environ.get("EXTRACTS_TO_DB", "all").strip().lower()
    marker = data_dir / "ingest_fingerprint.txt"
    if not marker.exists():
        log.error("no ingest fingerprint in %s: run the ingest first (python -m app.ingest)", data_dir)
        return 1
    try:
        result = load(os.environ["DATABASE_URL"], data_dir, mode, marker.read_text().strip())
    except (ValueError, KeyError) as exc:
        log.error("%s", exc)
        return 1
    log.info("extracts in PostgreSQL: %s", result)
    return 0


if __name__ == "__main__":
    sys.exit(main())
