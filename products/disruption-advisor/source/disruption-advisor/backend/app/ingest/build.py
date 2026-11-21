"""Stage 2 of the ingest: build the operating picture (``<DATA_DIR>/ops/*.parquet``) from the typed raw Parquet.

Everything is read from Parquet with column selection and filter pushdown (standards §9.25). Synthetic values
fill the data the airline did not supply (decisions Q4-Q11, Q25, Q30). They are deterministic, and every one is
labelled: a ``*_synthetic`` column or a ``*_source`` column says where a value came from.

Outputs:
  airports.parquet        IATA → IANA time zone (public dataset subset, app/data/airports.csv)
  aircraft.parquet        registration → model and seats (inventory-exact or assumed A320/174)
  flights.parquet         every rotation leg in the window, with tail, times (UTC), capacity, booked, available
  booking_classes.parquet booking code → revenue type and fare family (synthetic)
  customers.parquet       one row per passenger key: 12-month travel history (real), loyalty membership (real) and
                          a synthetic loyalty account modelled on the airline's loyalty sample (tier, priority,
                          loyalty ID, points; LOYALTY_* below)
  pax_segments.parquet    active passenger-segments in the window with enrichment and SSRs
  mct.parquet             hub connection times
  history_flights.parquet G9 flights 1 Jan 2026 to the window start with actual times, aircraft chain, bookings
  ingest_report.json      counts, mismatches and data-quality notes (shown in the UI)
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timedelta
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
# Scope (user decision 2026-11-21): only the airline's own flights. Partner and other carriers in the extracts
# (3L, 3O, E5, 9P, 4P) are excluded from the operating picture; including them is a future enhancement.
DEFAULT_CARRIERS: tuple[str, ...] = ("G9",)


# Loyalty (user 2026-11-21: use the given "Loyalty_Sample Data.xlsx"). The sample defines the tier ladder and its
# recovery priority (Basic Lowest, Silver Low, Gold Medium, Platinum High), points balances (Basic adult 10,000,
# Basic child 3,000, Silver 60,000) and family accounts with a head of family. It cannot be joined to the bookings
# (it holds e-mail IDs and names, the bookings are name-free), so every member gets a synthetic account built the
# same way: tier from real 12-month flights flown, points from tier + flights, family accounts from bookings that
# travel with children or infants. No names or e-mail addresses are generated.
LOYALTY_PRIORITY = {"Basic": "Lowest", "Silver": "Low", "Gold": "Medium", "Platinum": "High"}
LOYALTY_POINTS_BASE = {"Basic": 2000, "Silver": 40000, "Gold": 100000, "Platinum": 250000}
LOYALTY_POINTS_PER_FLIGHT = 1500
LOYALTY_FAMILY_MAX = 9  # people on a booking for it to count as a family account (larger = a group)


def _months(start: datetime, end: datetime) -> str:
    """Partition filter on dep_month (YYYY-MM) so DuckDB reads only the months in [start, end]."""
    return f"dep_month BETWEEN '{start:%Y-%m}' AND '{end:%Y-%m}'"


def _u(expr: str, salt: str) -> str:
    """SQL for a deterministic uniform [0,1) value from ``expr`` (md5-based, stable across runs and versions)."""
    return f"(('0x' || substr(md5('{salt}|' || {expr}), 1, 12))::UBIGINT / 281474976710656.0)"


def build(
    data_dir: Path, window: Window = DEFAULT_WINDOW, carriers: tuple[str, ...] = DEFAULT_CARRIERS
) -> dict[str, Any]:
    raw, ops = data_dir / "raw", data_dir / "ops"
    ops.mkdir(parents=True, exist_ok=True)
    c = duckdb.connect()
    w_start, w_end, snap = (f"TIMESTAMP '{t:%Y-%m-%d %H:%M:%S}'" for t in (window.start, window.end, window.snapshot))
    bookings = f"read_parquet('{raw}/bookings/*/*.parquet', hive_partitioning = true)"
    in_scope = "(" + ", ".join(f"'{c}'" for c in carriers if c.isalnum()) + ")"  # codes are alphanumeric only
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
            WHERE airline IN {in_scope}
            UNION ALL SELECT airline, reg, sai, std, try_cast(pax AS INTEGER) FROM '{raw}/punctuality.parquet'
            WHERE airline IN {in_scope}),
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

    # Fares list (user 2026-11-21): fares whose outbound travel validity overlaps the window. Validities are text
    # ranges "from~to" (several separated by commas); "4000-01-01" means open-ended.
    fares_file = raw / "fares.parquet"
    if fares_file.exists():
        c.execute(f"""
            CREATE OR REPLACE TEMP TABLE fares_window AS
            SELECT DISTINCT f.fare_id, f.booking_code, f.ond, f.journey_type, f.adult_value
            FROM read_parquet('{fares_file}') f, unnest(string_split(f.outbound_flight_validities, ',')) AS v(r)
            WHERE f.status = 'A' AND f.currency = 'AED' AND f.adult_value > 0
              AND try_strptime(split_part(r, '~', 1), '%Y-%m-%dT%H:%M') < {w_end}
              AND coalesce(try_strptime(split_part(split_part(r, '~', 2), ':', 1) || ':'
                                        || split_part(split_part(r, '~', 2), ':', 2), '%Y-%m-%dT%H:%M'),
                           TIMESTAMP '4000-01-01') >= {w_start}""")
        # Booking-class ladder: within each one-way O&D the classes are ranked by fare (percent rank); a class's
        # ladder position is its average rank over the O&Ds that sell it, so route price levels cancel out.
        c.execute("""
            CREATE OR REPLACE TEMP TABLE class_ladder AS
            WITH r AS (SELECT booking_code, ond, percent_rank() OVER (PARTITION BY ond ORDER BY adult_value) AS pr
                       FROM (SELECT booking_code, ond, min(adult_value) AS adult_value FROM fares_window
                             WHERE journey_type = 'ONE_WAY' GROUP BY 1, 2))
            SELECT r.booking_code, avg(r.pr) AS ladder, count(*) AS onds,
                   (SELECT median(adult_value) FROM fares_window w
                    WHERE w.booking_code = r.booking_code AND w.journey_type = 'ONE_WAY') AS median_one_way_aed
            FROM r GROUP BY 1""")
        # Connections the airline sells (one-way O&D X/SHJ/Y with X <> Y): only these are offered as rebooking
        # itineraries through the hub (gap 3).
        counts["sold_connections"] = out(
            "sold_connections",
            """
            SELECT DISTINCT string_split(ond, '/')[1] AS origin, string_split(ond, '/')[2] AS hub,
                   string_split(ond, '/')[3] AS destination
            FROM fares_window
            WHERE journey_type = 'ONE_WAY' AND len(string_split(ond, '/')) = 3
              AND string_split(ond, '/')[1] <> string_split(ond, '/')[3]""",
        )
    else:
        c.execute(
            "CREATE OR REPLACE TEMP TABLE class_ladder"
            " (booking_code VARCHAR, ladder DOUBLE, onds BIGINT, median_one_way_aed DOUBLE)"
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
            SELECT pnr, customer_key, pax_type, flight_number, dep_utc, origin, destination, booking_code,
                   total_fare, anci_charges, baggage_kg, meals, seat_code, is_lms_member, sales_channel, booking_ts,
                   passenger_id, passport_number_synthetic, national_id_synthetic, identity_rule,
                   row_number() OVER (PARTITION BY pnr, customer_key, flight_number, dep_utc
                                      ORDER BY booking_ts DESC) AS rn
            FROM {bookings}
            WHERE {_months(window.start, window.end)} AND dep_utc >= {w_start} AND dep_utc < {w_end}
              AND customer_key IS NOT NULL
              AND {active}
              AND (substr(flight_number, 1, 2) IN {in_scope} OR starts_with(flight_number, '02')))
        WHERE rn = 1""")

    # Booking-class level 0-1 (gap: booking class in fare value): classes in ladder order, level = share of the
    # window's passengers booked in cheaper classes (+ half the class's own share). Most passengers book a narrow
    # band of the ladder, so this spreads the level over the classes actually sold. NULL for codes the fares list
    # does not sell (promo, staff, ...): the priority then falls back to the fare family.
    counts["booking_class_levels"] = out(
        "booking_class_levels",
        """
        WITH pax AS (SELECT booking_code, count(*) AS n FROM seg WHERE booking_code IS NOT NULL GROUP BY 1),
             j AS (SELECT l.booking_code, l.ladder, l.onds, l.median_one_way_aed, coalesce(p.n, 0) AS n
                   FROM class_ladder l LEFT JOIN pax p USING (booking_code))
        SELECT booking_code, round(ladder, 4) AS ladder, onds, round(median_one_way_aed) AS median_one_way_aed,
               n AS window_passengers,
               round((sum(n) OVER (ORDER BY ladder, booking_code) - n / 2.0) / greatest(sum(n) OVER (), 1), 4)
                   AS level
        FROM j""",
    )

    # Customer profiles (Q4): real 12-month history and membership by customer key; synthetic loyalty account.
    priority_case = " ".join(f"WHEN '{t}' THEN '{p}'" for t, p in LOYALTY_PRIORITY.items())
    points_case = " ".join(f"WHEN '{t}' THEN {b}" for t, b in LOYALTY_POINTS_BASE.items())
    counts["customers"] = out(
        "customers",
        f"""
        WITH prof AS (
        WITH hist AS (
            SELECT customer_key, count(*) AS flown_12m,
                   count(DISTINCT pnr) AS pnrs_12m, bool_or(is_lms_member) AS member_hist
            FROM {bookings}
            WHERE {_months(window.snapshot - timedelta(days=366), window.snapshot)} AND customer_key IS NOT NULL
              AND dep_utc >= {snap} - INTERVAL 365 DAY AND dep_utc < {snap} AND {active}
            GROUP BY 1),
        people AS (SELECT customer_key, bool_or(is_lms_member) AS member_now FROM seg GROUP BY 1)
        SELECT p.customer_key,
               coalesce(p.member_now, FALSE) OR coalesce(h.member_hist, FALSE) AS is_loyalty_member,
               coalesce(h.flown_12m, 0) AS flown_segments_12m, coalesce(h.pnrs_12m, 0) AS bookings_12m,
               coalesce(h.pnrs_12m, 0) > {AMBIGUOUS_NAME_PNRS} AS ambiguous_common_name,
               CASE WHEN NOT (coalesce(p.member_now, FALSE) OR coalesce(h.member_hist, FALSE)) THEN NULL
                    WHEN coalesce(h.pnrs_12m, 0) > {AMBIGUOUS_NAME_PNRS} THEN 'Basic'
                    WHEN coalesce(h.flown_12m, 0) >= 24 THEN 'Platinum' WHEN coalesce(h.flown_12m, 0) >= 12 THEN 'Gold'
                    WHEN coalesce(h.flown_12m, 0) >= 6 THEN 'Silver' ELSE 'Basic' END AS loyalty_tier_synthetic,
               CASE WHEN coalesce(h.pnrs_12m, 0) > {AMBIGUOUS_NAME_PNRS} THEN 'unknown'
                    WHEN coalesce(h.flown_12m, 0) >= 12 THEN 'frequent'
                    WHEN coalesce(h.flown_12m, 0) >= 4 THEN 'regular' ELSE 'occasional' END AS travel_frequency_band
        FROM people p LEFT JOIN hist h USING (customer_key))
        SELECT *,
               CASE loyalty_tier_synthetic {priority_case} END AS loyalty_priority,
               -- unique and deterministic: members numbered in the order of a salted hash of their key
               CASE WHEN is_loyalty_member
                    THEN 'G9' || lpad(CAST(row_number() OVER (
                             PARTITION BY is_loyalty_member ORDER BY md5('loyalty-id|' || customer_key), customer_key)
                         AS VARCHAR), 9, '0')
               END AS loyalty_id_synthetic,
               -- flights of ambiguous common names are unreliable (tier capped at Basic): no accrual from them
               CASE WHEN is_loyalty_member
                    THEN CAST(round((CASE loyalty_tier_synthetic {points_case} END
                                     + {LOYALTY_POINTS_PER_FLIGHT}
                                       * least(CASE WHEN ambiguous_common_name THEN 0 ELSE flown_segments_12m END, 100)
                                     + {_u("customer_key", "loyalty-points")} * 5000) / 10) * 10 AS INTEGER)
               END AS available_points_synthetic
        FROM prof""",
    )

    # Family accounts (loyalty sample: "Family / Ind", "Head of family"): a booking in the window of at most
    # LOYALTY_FAMILY_MAX people that travels with children or infants and holds a member adult. Its head is the
    # member adult who flew most (ties: customer key); everyone on that booking travels on the head's tier.
    c.execute(f"""
        CREATE OR REPLACE TEMP TABLE family AS
        SELECT pnr, customer_key AS head_key, loyalty_tier_synthetic AS family_tier, loyalty_priority AS family_priority
        FROM (
            SELECT s.pnr, s.customer_key, cu.loyalty_tier_synthetic, cu.loyalty_priority,
                   row_number() OVER (PARTITION BY s.pnr ORDER BY cu.flown_segments_12m DESC, s.customer_key) AS n
            FROM (SELECT DISTINCT pnr, customer_key, pax_type FROM seg) s
            JOIN customers cu USING (customer_key)
            WHERE s.pax_type = 'AD' AND cu.is_loyalty_member
              AND s.pnr IN (SELECT pnr FROM seg WHERE pax_type IN ('CH', 'IN'))
              -- a family, not a tour group: at most LOYALTY_FAMILY_MAX people on the booking
              AND s.pnr IN (SELECT pnr FROM seg GROUP BY 1 HAVING count(DISTINCT customer_key) <= {LOYALTY_FAMILY_MAX}))
        WHERE n = 1""")

    ssr_case = "\n".join(
        f"WHEN s.pax_type = 'AD' AND {_u('s.pnr || s.customer_key', 'ssr')} < {rate} THEN '{code}'"
        for code, rate in SSR_RATES
    )
    counts["pax_segments"] = out(
        "pax_segments",
        f"""
        WITH pnr AS (SELECT pnr, count(DISTINCT customer_key) AS pnr_size,
                            count(DISTINCT customer_key) FILTER (WHERE pax_type = 'AD') AS adults,
                            count(DISTINCT customer_key) FILTER (WHERE pax_type = 'IN') AS infants,
                            count(DISTINCT customer_key) FILTER (WHERE pax_type = 'CH') AS children
                     FROM seg GROUP BY 1),
             inf AS (SELECT pnr, customer_key, dense_rank() OVER (PARTITION BY pnr ORDER BY customer_key) AS n
                     FROM (SELECT DISTINCT pnr, customer_key FROM seg WHERE pax_type = 'IN')),
             ad AS (SELECT pnr, customer_key, dense_rank() OVER (PARTITION BY pnr ORDER BY customer_key) AS n
                    FROM (SELECT DISTINCT pnr, customer_key FROM seg WHERE pax_type = 'AD'))
        SELECT s.flight_number || '_' || strftime(s.dep_utc, '%Y%m%d%H%M') AS flight_id,
               s.pnr, s.customer_key, s.pax_type,
               s.flight_number, s.dep_utc, s.origin, s.destination, s.booking_code,
               coalesce(bc.revenue_type, 'REVENUE') AS revenue_type,
               coalesce(bc.fare_family_synthetic, 'Other') AS fare_family_synthetic,
               coalesce(s.total_fare, 0) AS fare, coalesce(s.anci_charges, 0) AS ancillaries,
               coalesce(s.baggage_kg, 0) AS baggage_kg, s.meals IS NOT NULL AS has_meal,
               s.seat_code IS NOT NULL AS has_seat, s.sales_channel,
               p.pnr_size, p.adults, p.children, p.infants,
               -- Unaccompanied minors (UMNR) are out of scope (user 2026-11-21): no UMNR code is derived.
               CASE WHEN s.pax_type = 'IN' THEN 'INFT'
                    {ssr_case}
               END AS ssr_code,
               CASE WHEN s.pax_type = 'IN' THEN 'data' ELSE 'synthetic' END AS ssr_source,
               CASE WHEN s.pax_type = 'IN' THEN substr(sha256(a.customer_key), 1, 16) END AS infant_with_customer_key,
               -- synthetic identity, supplied with the bookings (stage 1, app.ingest.convert)
               s.passenger_id, s.passport_number_synthetic, s.national_id_synthetic, s.identity_rule,
               -- synthetic family loyalty account (see "family" above)
               fa.pnr IS NOT NULL AS family_account_synthetic,
               coalesce(fa.head_key = s.customer_key, FALSE) AS family_head_synthetic,
               fa.family_tier AS family_tier_synthetic, fa.family_priority AS family_priority_synthetic,
               -- booking-class level from the fares list (NULL for codes it does not sell: promo, staff, ...)
               bl.level AS booking_class_level
        FROM seg s
        JOIN pnr p ON p.pnr = s.pnr
        LEFT JOIN family fa ON fa.pnr = s.pnr
        LEFT JOIN booking_class_levels bl ON bl.booking_code = s.booking_code
        LEFT JOIN booking_classes bc ON bc.booking_code = coalesce(s.booking_code, '(blank)')
        LEFT JOIN inf i ON i.pnr = s.pnr AND i.customer_key = s.customer_key
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
            FROM '{raw}/rotation.parquet'
            WHERE std >= {w_start} AND std < {w_end} AND airline IN {in_scope}),
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

    # History (G9, 1 Jan 2026 up to the window start): real flights with actual times, from the punctuality
    # extract. Used to measure rules (turn times), replay real disruptions (backtest) and for prediction.
    # Each aircraft's legs are ordered by actual departure: delays and tail swaps make scheduled times overlap.
    counts["history_flights"] = out(
        "history_flights",
        f"""
        WITH p AS (
            SELECT airline, reg AS tail, sai AS flight_number, dep AS origin, arr AS destination,
                   try_cast(std AS TIMESTAMP) AS std, try_cast(sta AS TIMESTAMP) AS sta,
                   try_cast(atd AS TIMESTAMP) AS atd, try_cast(ata AS TIMESTAMP) AS ata,
                   dep_dly, arr_dly, op_type,
                   trim(regexp_replace(coalesce(dlycode, ''), '\\s+', ' ', 'g')) AS dep_delay_codes,
                   trim(regexp_replace(coalesce(dcode, ''), '\\s+', ' ', 'g')) AS arr_delay_codes,
                   try_cast(pax AS INTEGER) AS pax_reported, trim(diversion) = 'Yes' AS diverted
            FROM '{raw}/punctuality.parquet'
            WHERE airline = 'G9' AND try_cast(std AS TIMESTAMP) < {w_start}),
        f AS (
            SELECT flight_number || '_' || strftime(std, '%Y%m%d%H%M') AS flight_id, *, atd IS NOT NULL AS operated
            FROM p
            -- one row per flight: if a planned flight was replaced (e.g. new destination), keep the one that flew
            QUALIFY row_number() OVER (PARTITION BY flight_number, std ORDER BY atd IS NOT NULL DESC, tail) = 1),
        booked AS (
            SELECT flight_number, dep_utc, count(*) FILTER (WHERE pax_type <> 'IN') AS booked_seats,
                   count(*) AS booked_pax
            FROM {bookings}
            WHERE {_months(datetime(2026, 1, 1), window.start)} AND dep_utc < {w_start} AND {active}
            GROUP BY 1, 2),
        chain AS (
            SELECT flight_id,
                   row_number() OVER w AS leg_no,
                   lead(flight_id) OVER w AS next_flight_id,
                   lead(origin) OVER w = destination AS next_from_same_station,
                   date_diff('minute', ata, lead(atd) OVER w) AS actual_turn_minutes,
                   date_diff('minute', sta, lead(std) OVER w) AS scheduled_turn_minutes
            FROM f WHERE operated AND tail IS NOT NULL
            WINDOW w AS (PARTITION BY tail ORDER BY atd))
        SELECT f.*, ac.aircraft_model, coalesce(ac.seats, {DEFAULT_SEATS})::INTEGER AS capacity,
               coalesce(b.booked_seats, 0) AS booked_seats, coalesce(b.booked_pax, 0) AS booked_pax,
               c.leg_no, c.next_flight_id, c.next_from_same_station, c.actual_turn_minutes, c.scheduled_turn_minutes
        FROM f
        LEFT JOIN aircraft ac ON ac.registration = f.tail
        LEFT JOIN booked b ON b.flight_number = f.flight_number AND b.dep_utc = f.std
        LEFT JOIN chain c USING (flight_id)
        ORDER BY f.tail, coalesce(f.atd, f.std)""",
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
        "history": dict(
            zip(
                ["flights", "not_operated", "diverted", "with_bookings", "chain_same_station_share"],
                c.execute(
                    """SELECT count(*), count(*) FILTER (WHERE NOT operated), count(*) FILTER (WHERE diverted),
                              count(*) FILTER (WHERE booked_pax > 0),
                              round(avg(next_from_same_station::INTEGER) FILTER (WHERE next_flight_id IS NOT NULL), 4)
                       FROM history_flights"""
                ).fetchone()
                or (),
                strict=False,
            )
        ),
    }
    report = {
        "window": {k: str(v) for k, v in vars(window).items()},
        "carriers_in_scope": list(carriers),
        "counts": counts,
        "quality": quality,
        "built_at": datetime.now().isoformat(timespec="seconds"),
    }
    (ops / "ingest_report.json").write_text(json.dumps(report, indent=2, default=str))
    return report
