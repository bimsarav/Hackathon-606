"""Generate the UC5 synthetic enrichment files (user decision 2026-11-20: open data questions 4-11 are
filled with synthetic data built from the given data plus domain knowledge). NOT airline data.

Input : a DuckDB database with table `bookings` (all 18 monthly booking CSVs, cleaned to UTF-8, one row
        per passenger-segment, plus SRC_FILE). Build it with load_bookings.py.
Output: CSV files next to this script (see README.md). Deterministic: the same input gives the same output.

Usage: python generate_synthetic.py <bookings.duckdb>
"""
import hashlib
import sys
from pathlib import Path

import duckdb

OUT = Path(__file__).resolve().parent
SNAPSHOT = "2026-11-20 00:00:00"  # demo "now" (Q2): history = 12 months before, window = rotation range
WINDOW_FROM, WINDOW_TO = "2026-11-19 00:00:00", "2026-12-01 00:00:00"
ACTIVE = "RES_STATUS='CNF' AND SEG_STATUS='CNF' AND FLIGHT_STATUS='ACT'"
NONREV_CODES = ("VI", "DU", "DT", "Z", "DUMKT", "GD", "DUFAM")  # zero-fare active codes in the data (Q7, assumed staff/ID travel)
AMBIGUOUS_NAME_PNRS = 60  # a name in more PNRs than this in 12 months is treated as a common name (frequency unreliable)


def u(key: str, salt: str) -> float:
    """Deterministic uniform [0,1) from a key, so every run assigns the same synthetic values."""
    return int(hashlib.sha256(f"{salt}|{key}".encode()).hexdigest()[:12], 16) / 16**12


def main(db: str) -> None:
    c = duckdb.connect(db, read_only=True)
    c.create_function("u", u, ["VARCHAR", "VARCHAR"], "DOUBLE")
    c.execute(f"""
    CREATE TEMP TABLE act AS
    SELECT *, lower(trim(FIRST_NAME))||'|'||lower(trim(LAST_NAME)) AS name_key,
           try_cast(EST_TIME_DEPARTURE_ZULU AS TIMESTAMP) AS dep_utc,
           try_cast(TOTAL_FARE AS DOUBLE) AS fare
    FROM bookings WHERE {ACTIVE}""")

    # 1. Customer profile (Q4): customer key = hash of the normalised name (no other identity field exists).
    c.execute(f"""
    CREATE TEMP TABLE hist AS
    SELECT name_key, count(*) AS segments_12m, count(DISTINCT PNR) AS pnrs_12m,
           max(CASE WHEN IS_LMS_MEMBER='Y' THEN 1 ELSE 0 END) AS member_any
    FROM act WHERE dep_utc >= TIMESTAMP '{SNAPSHOT}' - INTERVAL 365 DAY AND dep_utc < TIMESTAMP '{SNAPSHOT}'
    GROUP BY 1""")
    c.execute(f"""
    CREATE TEMP TABLE win AS
    SELECT * FROM act WHERE dep_utc >= TIMESTAMP '{WINDOW_FROM}' AND dep_utc < TIMESTAMP '{WINDOW_TO}'""")
    c.execute(f"""
    COPY (
      WITH people AS (SELECT DISTINCT name_key, max(CASE WHEN IS_LMS_MEMBER='Y' THEN 1 ELSE 0 END) OVER (PARTITION BY name_key) AS member_now FROM win)
      SELECT DISTINCT substr(sha256(p.name_key),1,16) AS customer_key,
             CASE WHEN p.member_now=1 OR coalesce(h.member_any,0)=1 THEN 'Y' ELSE 'N' END AS is_loyalty_member,
             coalesce(h.segments_12m,0) AS flown_segments_12m,
             coalesce(h.pnrs_12m,0) AS bookings_12m,
             coalesce(h.pnrs_12m,0) > {AMBIGUOUS_NAME_PNRS} AS ambiguous_common_name,
             CASE WHEN NOT (p.member_now=1 OR coalesce(h.member_any,0)=1) THEN NULL
                  WHEN coalesce(h.pnrs_12m,0) > {AMBIGUOUS_NAME_PNRS} THEN 'Blue'
                  WHEN coalesce(h.segments_12m,0) >= 24 THEN 'Platinum'
                  WHEN coalesce(h.segments_12m,0) >= 12 THEN 'Gold'
                  WHEN coalesce(h.segments_12m,0) >= 6 THEN 'Silver' ELSE 'Blue' END AS loyalty_tier_synthetic,
             CASE WHEN coalesce(h.pnrs_12m,0) > {AMBIGUOUS_NAME_PNRS} THEN 'unknown'
                  WHEN coalesce(h.segments_12m,0) >= 12 THEN 'frequent'
                  WHEN coalesce(h.segments_12m,0) >= 4 THEN 'regular' ELSE 'occasional' END AS travel_frequency_band
      FROM people p LEFT JOIN hist h USING (name_key)
      ORDER BY 1) TO '{OUT}/customer_profile_synthetic.csv' (HEADER)""")

    # 2. Booking class -> fare family / revenue type (Q7, Q8): E-ladder buckets ordered by average fare and split by
    #    passenger share: cheapest 50% Basic, next 35% Value, top 15% Ultimate (synthetic; real families unknown).
    c.execute(f"""
    COPY (
      WITH k AS (SELECT coalesce(BOOKING_CODE,'(blank)') AS booking_code, count(*) AS active_segments,
                        round(avg(fare),2) AS avg_fare, round(100*avg(CASE WHEN fare=0 THEN 1 ELSE 0 END),1) AS pct_zero_fare
                 FROM act GROUP BY 1),
           e AS (SELECT booking_code, sum(active_segments) OVER (ORDER BY avg_fare, booking_code) / sum(active_segments) OVER () AS cum_share
                 FROM k WHERE regexp_matches(booking_code,'^E[0-9]+$'))
      SELECT booking_code, active_segments, avg_fare, pct_zero_fare,
        CASE WHEN booking_code IN {NONREV_CODES} THEN 'NON_REV'
             WHEN booking_code='BUS' THEN 'BUS'
             ELSE 'REVENUE' END AS revenue_type,
        CASE WHEN booking_code IN {NONREV_CODES} THEN 'Staff/ID (non-revenue)'
             WHEN booking_code='BUS' THEN 'Bus connection'
             WHEN e.cum_share > 0.85 THEN 'Ultimate'
             WHEN e.cum_share > 0.50 THEN 'Value'
             WHEN e.cum_share IS NOT NULL THEN 'Basic'
             ELSE 'Other (promo/corporate/agency)' END AS fare_family_synthetic
      FROM k LEFT JOIN e USING (booking_code) ORDER BY active_segments DESC) TO '{OUT}/booking_class_map_synthetic.csv' (HEADER)""")

    # 3. Special service requests and infant links (Q5) for passengers in the demo window.
    c.execute(f"""
    COPY (
      WITH pax AS (SELECT DISTINCT PNR, FIRST_NAME, LAST_NAME, PAX_TYPE_CODE, name_key FROM win),
           pnr AS (SELECT PNR, sum(CASE WHEN PAX_TYPE_CODE='AD' THEN 1 ELSE 0 END) AS adults FROM pax GROUP BY 1),
           inf AS (SELECT PNR, name_key, row_number() OVER (PARTITION BY PNR ORDER BY name_key) AS n FROM pax WHERE PAX_TYPE_CODE='IN'),
           ad  AS (SELECT PNR, name_key, row_number() OVER (PARTITION BY PNR ORDER BY name_key) AS n FROM pax WHERE PAX_TYPE_CODE='AD'),
           ssr AS (
             SELECT p.PNR, substr(sha256(p.name_key),1,16) AS customer_key, p.PAX_TYPE_CODE,
               CASE WHEN p.PAX_TYPE_CODE='CH' AND r.adults=0 THEN 'UMNR'
                    WHEN p.PAX_TYPE_CODE='IN' THEN 'INFT'
                    WHEN p.PAX_TYPE_CODE='AD' AND u(p.PNR||p.name_key,'ssr') < 0.0060 THEN 'WCHR'
                    WHEN p.PAX_TYPE_CODE='AD' AND u(p.PNR||p.name_key,'ssr') < 0.0075 THEN 'WCHS'
                    WHEN p.PAX_TYPE_CODE='AD' AND u(p.PNR||p.name_key,'ssr') < 0.0080 THEN 'WCHC'
                    WHEN p.PAX_TYPE_CODE='AD' AND u(p.PNR||p.name_key,'ssr') < 0.0083 THEN 'BLND'
                    WHEN p.PAX_TYPE_CODE='AD' AND u(p.PNR||p.name_key,'ssr') < 0.0086 THEN 'DEAF'
                    WHEN p.PAX_TYPE_CODE='AD' AND u(p.PNR||p.name_key,'ssr') < 0.0091 THEN 'MEDA'
                    WHEN p.PAX_TYPE_CODE='AD' AND u(p.PNR||p.name_key,'ssr') < 0.0101 THEN 'PREG'
               END AS ssr_code,
               CASE WHEN p.PAX_TYPE_CODE='IN' THEN substr(sha256(a.name_key),1,16) END AS travelling_with_customer_key
             FROM pax p JOIN pnr r USING (PNR)
             LEFT JOIN inf i ON i.PNR=p.PNR AND i.name_key=p.name_key
             LEFT JOIN ad a ON a.PNR=p.PNR AND a.n=((i.n-1) % greatest(r.adults,1))+1)
      SELECT * FROM ssr WHERE ssr_code IS NOT NULL ORDER BY PNR) TO '{OUT}/ssr_synthetic.csv' (HEADER)""")

    for f in ("customer_profile_synthetic.csv", "booking_class_map_synthetic.csv", "ssr_synthetic.csv"):
        n = c.execute(f"SELECT count(*) FROM read_csv('{OUT}/{f}')").fetchone()[0]
        print(f, n)


if __name__ == "__main__":
    main(sys.argv[1])
