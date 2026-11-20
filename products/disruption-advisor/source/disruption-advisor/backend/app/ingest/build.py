"""Stage 2 of the ingest: build the operating picture (``<DATA_DIR>/ops/*.parquet``) from the typed raw Parquet.

Everything is read from Parquet with column selection and filter pushdown (standards §9.25). Synthetic values
fill the data the airline did not supply (decisions Q4-Q11, Q25, Q30). They are deterministic, and every one is
labelled: a ``*_synthetic`` column or a ``*_source`` column says where a value came from.

Outputs:
  airports.parquet        IATA → IANA time zone (public dataset subset, app/data/airports.csv)
  aircraft.parquet        registration → model and seats (inventory-exact or assumed A320/174)
  flights.parquet         every rotation leg in the window, with tail, times (UTC), capacity, booked, available
  booking_classes.parquet booking code → revenue type and fare family (synthetic)
  customers.parquet       one row per passenger key: 12-month travel history (real) and loyalty tier (synthetic)
  pax_segments.parquet    active passenger-segments in the window with enrichment and SSRs
  mct.parquet             hub connection times
  ingest_report.json      counts, mismatches and data-quality notes (shown in the UI)
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

import duckdb

AIRPORTS_CSV = Path(__file__).resolve().parent.parent / "data" / "airports.csv"
NONREV_CODES = ("VI", "DU", "DT", "Z", "DUMKT", "GD", "DUFAM")
AMBIGUOUS_NAME_PNRS = 60
DEFAULT_MODEL, DEFAULT_SEATS = "A320 (assumed)", 174
# Deterministic special-service rates for adults (synthetic, Q5): cumulative thresholds on a hash in [0, 1).
SSR_RATES = (
    ("WCHR", 0.0060),
    ("WCHS", 0.0075),
    ("WCHC", 0.0080),
    ("BLND", 0.0083),
    ("DEAF", 0.0086),
    ("MEDA", 0.0091),
    ("PREG", 0.0101),
)


@dataclass(frozen=True)
class Window:
    snapshot: datetime  # demo "now" (Q2)
    start: datetime
    end: datetime


DEFAULT_WINDOW = Window(datetime(2026, 11, 20), datetime(2026, 11, 19), datetime(2026, 12, 1))


def _u(expr: str, salt: str) -> str:
    """SQL for a deterministic uniform [0,1) value from ``expr`` (md5-based, stable across runs and versions)."""
    return f"(('0x' || substr(md5('{salt}|' || {expr}), 1, 12))::UBIGINT / 281474976710656.0)"


def build(data_dir: Path, window: Window = DEFAULT_WINDOW) -> dict[str, Any]:
    raw, ops = data_dir / "raw", data_dir / "ops"
    ops.mkdir(parents=True, exist_ok=True)
    c = duckdb.connect()
    w_start, w_end, snap = (f"TIMESTAMP '{t:%Y-%m-%d %H:%M:%S}'" for t in (window.start, window.end, window.snapshot))
    bookings = f"read_parquet('{raw}/bookings/*/*.parquet', hive_partitioning = true)"
    active = "res_status = 'CNF' AND seg_status = 'CNF' AND flight_status = 'ACT'"

    def out(name: str, sql: str) -> int:
        c.execute(f"COPY ({sql}) TO '{ops / name}.parquet' (FORMAT parquet, COMPRESSION zstd)")
        c.execute(f"CREATE OR REPLACE VIEW {name} AS SELECT * FROM '{ops / name}.parquet'")
        return int(c.execute(f"SELECT count(*) FROM {name}").fetchone()[0])  # type: ignore[index]

    counts: dict[str, Any] = {}
    counts["airports"] = out("airports", f"SELECT * FROM read_csv('{AIRPORTS_CSV}', header = true, all_varchar = true)")

    # Aircraft registry (Q25/Q30). Model from exact inventory matches; seats = the smallest known cabin layout
    # (174 A320 / 215 A321, seen in the inventory) that fits the most passengers the tail ever carried, so a tail
    # that carried 200 passengers is never treated as a 174-seat aircraft.
    counts["aircraft"] = out(
        "aircraft",
        f"""
        WITH legs AS (
            SELECT airline, reg, sai, std, try_cast(pax AS INTEGER) AS pax FROM '{raw}/rotation.parquet'
            UNION ALL SELECT airline, reg, sai, std, try_cast(pax AS INTEGER) FROM '{raw}/punctuality.parquet'),
        inv AS (SELECT DISTINCT flight_number, dep_utc, aircraft_model, adult_capacity FROM '{raw}/inventory.parquet'),
        hits AS (
            SELECT l.reg, i.aircraft_model, max(i.adult_capacity) AS seats, count(*) AS n
            FROM legs l JOIN inv i ON i.flight_number = l.sai AND i.dep_utc = l.std GROUP BY 1, 2),
        best AS (SELECT reg, arg_max(aircraft_model, n) AS model, arg_max(seats, n) AS seats, sum(n) AS evidence
                 FROM hits GROUP BY 1),
        tails AS (SELECT reg, arg_max(airline, std) AS airline, max(pax) AS max_pax FROM legs
                  WHERE reg IS NOT NULL GROUP BY 1),
        -- rotation PAX counts infants too (lap infants take no seat), so allow up to 12 infants per layout
        fit AS (SELECT t.*, CASE WHEN coalesce(t.max_pax, 0) <= 186 THEN 174 WHEN t.max_pax <= 230 THEN 215
                                 ELSE t.max_pax END AS seats_fit FROM tails t)
        SELECT f.reg AS registration, f.airline,
               CASE WHEN b.model IS NOT NULL AND b.seats >= f.seats_fit THEN b.model
                    WHEN f.seats_fit >= 215 THEN 'A321 (inferred)'
                    ELSE coalesce(b.model, '{DEFAULT_MODEL}') END AS aircraft_model,
               greatest(coalesce(b.seats, 0), f.seats_fit)::INTEGER AS seats,
               CASE WHEN b.model IS NOT NULL AND b.seats >= f.seats_fit THEN 'inventory-exact'
                    WHEN f.seats_fit > {DEFAULT_SEATS} THEN 'inferred-from-max-pax'
                    ELSE 'assumed-a320-174' END AS model_source,
               coalesce(b.evidence, 0) AS evidence_legs, f.max_pax AS max_pax_seen
        FROM fit f LEFT JOIN best b USING (reg)""",
    )

    # Booking classes (Q7/Q8): non-revenue codes from the data; E-ladder split by passenger share 50/35/15.
    counts["booking_classes"] = out(
        "booking_classes",
        f"""
        WITH k AS (SELECT coalesce(booking_code, '(blank)') AS booking_code, count(*) AS active_segments,
                          avg(total_fare) AS avg_fare
                   FROM {bookings} WHERE {active} GROUP BY 1),
             e AS (SELECT booking_code, sum(active_segments) OVER (ORDER BY avg_fare, booking_code)
                          / sum(active_segments) OVER () AS cum_share
                   FROM k WHERE regexp_matches(booking_code, '^E[0-9]+$'))
        SELECT booking_code, active_segments, round(avg_fare, 2) AS avg_fare,
               CASE WHEN booking_code IN {NONREV_CODES} THEN 'NON_REV' WHEN booking_code = 'BUS' THEN 'BUS'
                    ELSE 'REVENUE' END AS revenue_type,
               CASE WHEN booking_code IN {NONREV_CODES} THEN 'Staff/ID'
                    WHEN booking_code = 'BUS' THEN 'Bus'
                    WHEN e.cum_share > 0.85 THEN 'Ultimate' WHEN e.cum_share > 0.50 THEN 'Value'
                    WHEN e.cum_share IS NOT NULL THEN 'Basic' ELSE 'Other' END AS fare_family_synthetic
        FROM k LEFT JOIN e USING (booking_code)""",
    )

    # Window segments (latest active row per passenger-segment wins).
    c.execute(f"""
        CREATE TEMP TABLE seg AS
        SELECT * FROM (
            SELECT pnr, first_name, last_name, pax_type, flight_number, dep_utc, origin, destination, booking_code,
                   total_fare, anci_charges, baggage_kg, meals, seat_code, is_lms_member, sales_channel, booking_ts,
                   lower(trim(first_name)) || '|' || lower(trim(last_name)) AS name_key,
                   row_number() OVER (PARTITION BY pnr, first_name, last_name, flight_number, dep_utc
                                      ORDER BY booking_ts DESC) AS rn
            FROM {bookings}
            WHERE dep_year IN ({window.start.year}, {window.end.year}) AND dep_utc >= {w_start} AND dep_utc < {w_end}
              AND {active})
        WHERE rn = 1""")

    # Customer profiles (Q4): real 12-month history by name key; synthetic tier for loyalty members.
    counts["customers"] = out(
        "customers",
        f"""
        WITH hist AS (
            SELECT lower(trim(first_name)) || '|' || lower(trim(last_name)) AS name_key, count(*) AS flown_12m,
                   count(DISTINCT pnr) AS pnrs_12m, bool_or(is_lms_member) AS member_hist
            FROM {bookings}
            WHERE dep_year IN ({window.snapshot.year - 1}, {window.snapshot.year})
              AND dep_utc >= {snap} - INTERVAL 365 DAY AND dep_utc < {snap} AND {active}
            GROUP BY 1),
        people AS (SELECT name_key, bool_or(is_lms_member) AS member_now FROM seg GROUP BY 1)
        SELECT substr(sha256(p.name_key), 1, 16) AS customer_key,
               coalesce(p.member_now, FALSE) OR coalesce(h.member_hist, FALSE) AS is_loyalty_member,
               coalesce(h.flown_12m, 0) AS flown_segments_12m, coalesce(h.pnrs_12m, 0) AS bookings_12m,
               coalesce(h.pnrs_12m, 0) > {AMBIGUOUS_NAME_PNRS} AS ambiguous_common_name,
               CASE WHEN NOT (coalesce(p.member_now, FALSE) OR coalesce(h.member_hist, FALSE)) THEN NULL
                    WHEN coalesce(h.pnrs_12m, 0) > {AMBIGUOUS_NAME_PNRS} THEN 'Blue'
                    WHEN coalesce(h.flown_12m, 0) >= 24 THEN 'Platinum' WHEN coalesce(h.flown_12m, 0) >= 12 THEN 'Gold'
                    WHEN coalesce(h.flown_12m, 0) >= 6 THEN 'Silver' ELSE 'Blue' END AS loyalty_tier_synthetic,
               CASE WHEN coalesce(h.pnrs_12m, 0) > {AMBIGUOUS_NAME_PNRS} THEN 'unknown'
                    WHEN coalesce(h.flown_12m, 0) >= 12 THEN 'frequent'
                    WHEN coalesce(h.flown_12m, 0) >= 4 THEN 'regular' ELSE 'occasional' END AS travel_frequency_band
        FROM people p LEFT JOIN hist h USING (name_key)""",
    )

    ssr_case = "\n".join(
        f"WHEN s.pax_type = 'AD' AND {_u('s.pnr || s.name_key', 'ssr')} < {rate} THEN '{code}'"
        for code, rate in SSR_RATES
    )
    counts["pax_segments"] = out(
        "pax_segments",
        f"""
        WITH pnr AS (SELECT pnr, count(DISTINCT name_key) AS pnr_size,
                            count(DISTINCT name_key) FILTER (WHERE pax_type = 'AD') AS adults,
                            count(DISTINCT name_key) FILTER (WHERE pax_type = 'IN') AS infants,
                            count(DISTINCT name_key) FILTER (WHERE pax_type = 'CH') AS children
                     FROM seg GROUP BY 1),
             inf AS (SELECT pnr, name_key, dense_rank() OVER (PARTITION BY pnr ORDER BY name_key) AS n
                     FROM (SELECT DISTINCT pnr, name_key FROM seg WHERE pax_type = 'IN')),
             ad AS (SELECT pnr, name_key, dense_rank() OVER (PARTITION BY pnr ORDER BY name_key) AS n
                    FROM (SELECT DISTINCT pnr, name_key FROM seg WHERE pax_type = 'AD'))
        SELECT s.flight_number || '_' || strftime(s.dep_utc, '%Y%m%d%H%M') AS flight_id,
               s.pnr, substr(sha256(s.name_key), 1, 16) AS customer_key, s.first_name, s.last_name, s.pax_type,
               s.flight_number, s.dep_utc, s.origin, s.destination, s.booking_code,
               coalesce(bc.revenue_type, 'REVENUE') AS revenue_type,
               coalesce(bc.fare_family_synthetic, 'Other') AS fare_family_synthetic,
               coalesce(s.total_fare, 0) AS fare, coalesce(s.anci_charges, 0) AS ancillaries,
               coalesce(s.baggage_kg, 0) AS baggage_kg, s.meals IS NOT NULL AS has_meal,
               s.seat_code IS NOT NULL AS has_seat, s.sales_channel,
               p.pnr_size, p.adults, p.children, p.infants,
               CASE WHEN s.pax_type = 'CH' AND p.adults = 0 THEN 'UMNR'
                    WHEN s.pax_type = 'IN' THEN 'INFT'
                    {ssr_case}
               END AS ssr_code,
               CASE WHEN s.pax_type IN ('IN') OR (s.pax_type = 'CH' AND p.adults = 0) THEN 'data'
                    ELSE 'synthetic' END AS ssr_source,
               CASE WHEN s.pax_type = 'IN' THEN substr(sha256(a.name_key), 1, 16) END AS infant_with_customer_key
        FROM seg s
        JOIN pnr p USING (pnr)
        LEFT JOIN booking_classes bc ON bc.booking_code = coalesce(s.booking_code, '(blank)')
        LEFT JOIN inf i ON i.pnr = s.pnr AND i.name_key = s.name_key
        LEFT JOIN ad a ON a.pnr = s.pnr AND a.n = ((i.n - 1) % greatest(p.adults, 1)) + 1
        ORDER BY s.dep_utc, s.flight_number, s.pnr""",
    )

    # Flights: rotation legs + capacity (inventory with curtail/oversell when present, else aircraft seats).
    counts["flights"] = out(
        "flights",
        f"""
        WITH r AS (
            SELECT airline, reg AS tail, sai AS flight_number, dep AS origin, arr AS destination, std,
                   coalesce(try_strptime(sta, '%Y-%m-%d %H:%M:%S'), pta) AS sta, atd, ata, dep_dly, arr_dly,
                   op_type, status, try_cast(pax AS INTEGER) AS pax_reported
            FROM '{raw}/rotation.parquet' WHERE std >= {w_start} AND std < {w_end}),
        inv AS (
            SELECT flight_number, dep_utc, any_value(aircraft_model) AS model, max(adult_capacity) AS cap,
                   max(CASE curtail_oversell WHEN 'OVERSELL' THEN curtail_oversell_count
                                             WHEN 'CURTAIL' THEN -curtail_oversell_count ELSE 0 END) AS adj
            FROM '{raw}/inventory.parquet' WHERE dep_utc >= {w_start} AND dep_utc < {w_end} GROUP BY 1, 2),
        booked AS (SELECT flight_id, count(*) FILTER (WHERE pax_type <> 'IN') AS booked_seats,
                          count(*) AS booked_pax FROM pax_segments GROUP BY 1)
        SELECT r.flight_number || '_' || strftime(r.std, '%Y%m%d%H%M') AS flight_id, r.*,
               coalesce(inv.model, ac.aircraft_model, '{DEFAULT_MODEL}') AS aircraft_model,
               coalesce(inv.cap + inv.adj, ac.seats, {DEFAULT_SEATS})::INTEGER AS capacity,
               CASE WHEN inv.cap IS NOT NULL THEN 'inventory' ELSE coalesce(ac.model_source, 'assumed-a320-174') END
                   AS capacity_source,
               coalesce(b.booked_seats, 0) AS booked_seats, coalesce(b.booked_pax, 0) AS booked_pax,
               coalesce(inv.cap + inv.adj, ac.seats, {DEFAULT_SEATS}) - coalesce(b.booked_seats, 0) AS available_seats
        FROM r LEFT JOIN inv ON inv.flight_number = r.flight_number AND inv.dep_utc = r.std
        LEFT JOIN aircraft ac ON ac.registration = r.tail
        LEFT JOIN booked b ON b.flight_id = r.flight_number || '_' || strftime(r.std, '%Y%m%d%H%M')
        ORDER BY r.tail, r.std""",
    )

    counts["mct"] = out(
        "mct",
        f"""
        SELECT ond_code, split_part(ond_code, '/', 1) AS origin, split_part(ond_code, '/', 2) AS hub,
               split_part(ond_code, '/', 3) AS destination, min_conn_time_mins::INTEGER AS min_minutes,
               max_conn_time_mins::INTEGER AS max_minutes
        FROM '{raw}/mct.parquet' WHERE hub_ond_status = 'ACT'""",
    )

    quality = {
        "segments_without_flight": c.execute(
            "SELECT count(*) FROM pax_segments p ANTI JOIN flights f USING (flight_id)"
        ).fetchone()[0],  # type: ignore[index]
        "overbooked_flights": c.execute("SELECT count(*) FROM flights WHERE available_seats < 0").fetchone()[0],  # type: ignore[index]
        "capacity_sources": dict(c.execute("SELECT capacity_source, count(*) FROM flights GROUP BY 1").fetchall()),
        "flights_without_sta": c.execute("SELECT count(*) FROM flights WHERE sta IS NULL").fetchone()[0],  # type: ignore[index]
    }
    report = {
        "window": {k: str(v) for k, v in vars(window).items()},
        "counts": counts,
        "quality": quality,
        "built_at": datetime.now().isoformat(timespec="seconds"),
    }
    (ops / "ingest_report.json").write_text(json.dumps(report, indent=2, default=str))
    return report
