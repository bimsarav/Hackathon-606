"""Read-only access to the operating picture (``<data_dir>/ops/*.parquet``) through an in-memory DuckDB.

The window is small (thousands of flights, ~300k passenger-segments), so the tables are loaded once at start-up
and queried with SQL. Every query reads only the columns it needs (engineering standards §9.25).
"""

from __future__ import annotations

import json
import threading
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

import duckdb

TABLES = ("flights", "pax_segments", "customers", "aircraft", "mct", "airports", "booking_classes")


@dataclass(frozen=True)
class Leg:
    flight_id: str
    flight_number: str
    airline: str
    tail: str
    origin: str
    destination: str
    std: datetime
    sta: datetime
    capacity: int
    booked_seats: int
    booked_pax: int
    aircraft_model: str
    capacity_source: str

    @property
    def block_minutes(self) -> int:
        return int((self.sta - self.std).total_seconds() // 60)

    @property
    def available_seats(self) -> int:
        return max(self.capacity - self.booked_seats, 0)


LEG_COLUMNS = (
    "flight_id, flight_number, airline, tail, origin, destination, std, sta, capacity, booked_seats, "
    "booked_pax, aircraft_model, capacity_source"
)


class OpsStore:
    """Loads the ops Parquet tables into memory; each call uses its own cursor (thread-safe)."""

    def __init__(self, ops_dir: Path) -> None:
        self.ops_dir = ops_dir
        self._con = duckdb.connect(":memory:")
        self._lock = threading.Lock()
        for table in TABLES:
            self._con.execute(f"CREATE TABLE {table} AS SELECT * FROM read_parquet('{ops_dir / table}.parquet')")
        self._con.execute("CREATE INDEX idx_pax_flight ON pax_segments (flight_id)")
        self._con.execute("CREATE INDEX idx_pax_pnr ON pax_segments (pnr)")
        report = ops_dir / "ingest_report.json"
        self.report: dict[str, Any] = json.loads(report.read_text()) if report.exists() else {}

    def query(self, sql: str, params: list[Any] | None = None) -> list[dict[str, Any]]:
        cur = self._con.cursor()
        try:
            rel = cur.execute(sql, params or [])
            cols = [d[0] for d in rel.description]
            return [dict(zip(cols, row, strict=True)) for row in rel.fetchall()]
        finally:
            cur.close()

    def ready(self) -> bool:
        return bool(self.query("SELECT count(*) AS n FROM flights")[0]["n"])

    # --- flights -------------------------------------------------------------------------------------------
    @staticmethod
    def _leg(row: dict[str, Any]) -> Leg:
        return Leg(**{k: row[k] for k in LEG_COLUMNS.split(", ")})

    def leg(self, flight_id: str) -> Leg | None:
        rows = self.query(f"SELECT {LEG_COLUMNS} FROM flights WHERE flight_id = ? AND sta IS NOT NULL", [flight_id])
        return self._leg(rows[0]) if rows else None

    def tail_legs(self, tail: str, start: datetime, end: datetime) -> list[Leg]:
        rows = self.query(
            f"SELECT {LEG_COLUMNS} FROM flights "
            "WHERE tail = ? AND std >= ? AND std < ? AND sta IS NOT NULL ORDER BY std",
            [tail, start, end],
        )
        return [self._leg(r) for r in rows]

    def search_flights(self, text: str, day: str | None, limit: int) -> list[dict[str, Any]]:
        like = f"%{text.upper()}%"
        sql = (
            f"SELECT {LEG_COLUMNS} FROM flights WHERE sta IS NOT NULL AND "
            "(flight_number LIKE ? OR origin LIKE ? OR destination LIKE ? OR tail LIKE ?)"
        )
        params: list[Any] = [like, like, like, like]
        if day:
            sql += " AND CAST(std AS DATE) = CAST(? AS DATE)"
            params.append(day)
        return self.query(sql + " ORDER BY std LIMIT ?", [*params, limit])

    def tails_at_station(
        self, station: str, earliest: datetime, latest: datetime, model_seats: int, exclude: str
    ) -> list[str]:
        """Tails with the same seat count that depart ``station`` between earliest and latest (swap candidates)."""
        rows = self.query(
            """SELECT DISTINCT tail FROM flights
               WHERE origin = ? AND std BETWEEN ? AND ? AND tail <> ? AND capacity = ? AND sta IS NOT NULL""",
            [station, earliest, latest, exclude, model_seats],
        )
        return [r["tail"] for r in rows]

    def alternatives(
        self, origin: str, destination: str, after: datetime, before: datetime, exclude: list[str]
    ) -> list[Leg]:
        rows = self.query(
            f"""SELECT {LEG_COLUMNS} FROM flights
                WHERE origin = ? AND destination = ? AND std > ? AND std <= ? AND sta IS NOT NULL
                  AND NOT list_contains(?, flight_id)
                ORDER BY std""",
            [origin, destination, after, before, exclude],
        )
        return [self._leg(r) for r in rows]

    # --- passengers ----------------------------------------------------------------------------------------
    PAX_COLUMNS = (
        "p.flight_id, p.pnr, p.customer_key, p.pax_type, p.origin, p.destination, "
        "p.dep_utc, p.booking_code, p.revenue_type, p.fare_family_synthetic, p.fare, p.ancillaries, "
        "p.baggage_kg, p.has_meal, p.has_seat, p.pnr_size, p.adults, p.children, p.infants, p.ssr_code, "
        "p.ssr_source, p.passenger_id, p.passport_number_synthetic, p.national_id_synthetic, p.identity_rule, "
        "c.is_loyalty_member, c.loyalty_tier_synthetic, c.travel_frequency_band, "
        "c.flown_segments_12m, c.ambiguous_common_name"
    )

    def passengers_on(self, flight_ids: list[str]) -> list[dict[str, Any]]:
        if not flight_ids:
            return []
        return self.query(
            f"""SELECT {self.PAX_COLUMNS} FROM pax_segments p LEFT JOIN customers c USING (customer_key)
                WHERE list_contains(?, p.flight_id) ORDER BY p.pnr, p.customer_key""",
            [flight_ids],
        )

    def onward_segments(self, pnrs: list[str], after: datetime, until: datetime) -> list[dict[str, Any]]:
        """Later segments of the same PNRs (journey continuation), joined to their flight times."""
        if not pnrs:
            return []
        return self.query(
            """SELECT p.pnr, p.customer_key, p.flight_id, p.origin, p.destination, f.std, f.sta, f.flight_number
               FROM pax_segments p JOIN flights f USING (flight_id)
               WHERE list_contains(?, p.pnr) AND f.std > ? AND f.std <= ? ORDER BY f.std""",
            [pnrs, after, until],
        )

    def mct_minutes(self, origin: str, hub: str, destination: str, default: int) -> int:
        rows = self.query(
            "SELECT min_minutes FROM mct WHERE origin = ? AND hub = ? AND destination = ?", [origin, hub, destination]
        )
        return int(rows[0]["min_minutes"]) if rows else default

    def airport_tz(self) -> dict[str, str]:
        return {r["iata"]: r["tz"] for r in self.query("SELECT iata, tz FROM airports")}

    def country_of(self, iata: str) -> str | None:
        rows = self.query("SELECT country FROM airports WHERE iata = ?", [iata])
        return rows[0]["country"] if rows else None


_store: OpsStore | None = None
_store_lock = threading.Lock()


def get_store(ops_dir: Path) -> OpsStore:
    """Process-wide store, loaded on first use."""
    global _store
    with _store_lock:
        if _store is None or _store.ops_dir != ops_dir:
            _store = OpsStore(ops_dir)
        return _store
