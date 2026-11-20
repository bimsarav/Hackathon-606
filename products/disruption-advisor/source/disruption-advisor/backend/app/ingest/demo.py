"""Optional, clearly labelled demo scenario (DEMO_SCENARIO=true), appended to the operating picture.

Purpose (user request 2026-11-21): show the case "an inbound flight is delayed, its connecting passengers misconnect,
and the next flight on their onward route is fully booked". The route SHJ-HBE has no real flights in the extracts,
so seat availability is exactly as designed. All rows are synthetic: flights carry capacity_source
'synthetic-demo', passenger names are invented, and nothing here comes from airline data.

Day 2026-11-22, times UTC:
  A6-DMA  G9901 KHI-SHJ 05:00-07:30  (to be delayed)   G9902 SHJ-KHI 08:20-10:50   G9903 KHI-SHJ 11:40-14:10
  A6-DME  G9971 BAH-SHJ 06:00-07:00  G9972 SHJ-BAH 09:30-10:30  G9973 BAH-SHJ 11:30-12:30   (swap candidate)
  A6-DMB  G9951 SHJ-HBE 09:00-13:30  onward flight of the connecting passengers (planned connection 90 min)
  A6-DMC  G9953 SHJ-HBE 15:00-19:30  next flight on the route: FULL (174/174)
  A6-DMD  G9955 SHJ-HBE 23 Nov 03:00-07:30: 8 seats free
"""

from __future__ import annotations

import hashlib
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

import pyarrow as pa
import pyarrow.parquet as pq

DAY = datetime(2026, 11, 22)


def _t(h: int, m: int = 0, day: int = 0) -> datetime:
    return DAY + timedelta(days=day, hours=h, minutes=m)


FLIGHTS = [  # (flight number, tail, origin, destination, std, sta, booked seats)
    ("G9901", "A6-DMA", "KHI", "SHJ", _t(5), _t(7, 30), 160),
    ("G9902", "A6-DMA", "SHJ", "KHI", _t(8, 20), _t(10, 50), 150),
    ("G9903", "A6-DMA", "KHI", "SHJ", _t(11, 40), _t(14, 10), 140),
    ("G9971", "A6-DME", "BAH", "SHJ", _t(6), _t(7), 120),
    ("G9972", "A6-DME", "SHJ", "BAH", _t(9, 30), _t(10, 30), 110),
    ("G9973", "A6-DME", "BAH", "SHJ", _t(11, 30), _t(12, 30), 100),
    ("G9951", "A6-DMB", "SHJ", "HBE", _t(9), _t(13, 30), 170),
    ("G9953", "A6-DMC", "SHJ", "HBE", _t(15), _t(19, 30), 174),
    ("G9955", "A6-DMD", "SHJ", "HBE", _t(3, day=1), _t(7, 30, day=1), 166),
]

# Connecting passengers KHI-SHJ (G9901) then SHJ-HBE (G9951), one tuple per person:
# (pnr, first, last, pax type, ssr, fare, ancillaries, booking code, fare family, revenue, loyalty tier, frequency)
PAX = [
    ("DMOA01", "Ahmed", "Raza", "AD", "WCHR", 420.0, 0.0, "E24", "Basic", "REVENUE", None, "occasional"),
    ("DMOA02", "Fatima", "Khan", "AD", None, 510.0, 60.0, "E30", "Value", "REVENUE", "Blue", "regular"),
    ("DMOA02", "Imran", "Khan", "AD", None, 510.0, 60.0, "E30", "Value", "REVENUE", None, "regular"),
    ("DMOA02", "Zara", "Khan", "IN", "INFT", 60.0, 0.0, "E30", "Value", "REVENUE", None, "occasional"),
    ("DMOA03", "Ali", "Hassan", "CH", "UMNR", 380.0, 0.0, "E22", "Basic", "REVENUE", None, "occasional"),
    ("DMOA04", "Omar", "Siddiqui", "AD", None, 1450.0, 220.0, "E43", "Ultimate", "REVENUE", "Platinum", "frequent"),
    ("DMOA05", "Sara", "Malik", "AD", None, 690.0, 90.0, "E34", "Value", "REVENUE", "Gold", "frequent"),
    ("DMOA06", "Bilal", "Ahmed", "AD", None, 330.0, 0.0, "E18", "Basic", "REVENUE", None, "occasional"),
    ("DMOA06", "Hamza", "Ahmed", "AD", None, 330.0, 0.0, "E18", "Basic", "REVENUE", None, "occasional"),
    ("DMOA06", "Usman", "Tariq", "AD", None, 330.0, 0.0, "E18", "Basic", "REVENUE", None, "occasional"),
    ("DMOA06", "Kamran", "Shah", "AD", None, 330.0, 0.0, "E18", "Basic", "REVENUE", None, "occasional"),
    ("DMOA06", "Tariq", "Javed", "AD", None, 330.0, 0.0, "E18", "Basic", "REVENUE", None, "occasional"),
    ("DMOA07", "Nadia", "Iqbal", "AD", None, 0.0, 0.0, "DU", "Staff/ID", "NON_REV", None, "regular"),
    ("DMOA08", "Ayesha", "Butt", "AD", None, 560.0, 45.0, "E31", "Value", "REVENUE", "Silver", "regular"),
    ("DMOA08", "Junaid", "Butt", "AD", None, 560.0, 45.0, "E31", "Value", "REVENUE", "Silver", "regular"),
    ("DMOA09", "Rashid", "Mehmood", "AD", None, 450.0, 30.0, "E26", "Basic", "REVENUE", None, "frequent"),
    ("DMOA10", "Hina", "Aslam", "AD", None, 480.0, 25.0, "E27", "Value", "REVENUE", None, "occasional"),
    ("DMOA10", "Faisal", "Aslam", "AD", None, 480.0, 25.0, "E27", "Value", "REVENUE", None, "occasional"),
    ("DMOA11", "Kashif", "Noor", "AD", None, 300.0, 0.0, "E15", "Basic", "REVENUE", None, "occasional"),
    ("DMOA12", "Mariam", "Saeed", "AD", "PREG", 520.0, 35.0, "E30", "Value", "REVENUE", None, "occasional"),
    ("DMOA13", "Waqas", "Ali", "AD", None, 610.0, 120.0, "E33", "Value", "REVENUE", "Blue", "regular"),
    ("DMOA14", "Sana", "Farooq", "AD", None, 395.0, 0.0, "E20", "Basic", "REVENUE", None, "occasional"),
    ("DMOA14", "Adeel", "Farooq", "AD", None, 395.0, 0.0, "E20", "Basic", "REVENUE", None, "occasional"),
    ("DMOA15", "Zubair", "Hameed", "AD", None, 275.0, 0.0, "E13", "Basic", "REVENUE", None, "occasional"),
    ("DMOA16", "Laila", "Rahman", "AD", None, 820.0, 150.0, "E38", "Ultimate", "REVENUE", "Gold", "regular"),
]


def _key(first: str, last: str) -> str:
    return hashlib.sha256(f"demo|{first.lower()}|{last.lower()}".encode()).hexdigest()[:16]


def _fid(fn: str, std: datetime) -> str:
    return f"{fn}_{std:%Y%m%d%H%M}"


def _append(path: Path, rows: list[dict[str, Any]]) -> int:
    """Parquet files are immutable: rewrite the table with the demo rows appended (standards §9.25)."""
    existing = pq.read_table(path)
    # DuckDB marks columns without nulls as required; demo rows leave operational fields (e.g. actual times) empty.
    schema = pa.schema([field.with_nullable(True) for field in existing.schema])
    existing = existing.cast(schema)
    demo = pa.Table.from_pylist([{n: r.get(n) for n in schema.names} for r in rows], schema=schema)
    pq.write_table(pa.concat_tables([existing, demo]), path, compression="zstd")
    return len(rows)


def add_demo_scenario(ops: Path) -> dict[str, int]:
    flights = [
        {
            "flight_id": _fid(fn, std),
            "airline": "G9",
            "tail": tail,
            "flight_number": fn,
            "origin": o,
            "destination": d,
            "std": std,
            "sta": sta,
            "op_type": "J-Normal Service (synthetic demo)",
            "status": "SCH",
            "pax_reported": booked,
            "aircraft_model": "A320-174",
            "capacity": 174,
            "capacity_source": "synthetic-demo",
            "booked_seats": booked,
            "booked_pax": booked,
            "available_seats": 174 - booked,
        }
        for fn, tail, o, d, std, sta, booked in FLIGHTS
    ]

    g9901 = _fid("G9901", _t(5))
    g9951 = _fid("G9951", _t(9))
    by_pnr: dict[str, list[tuple[Any, ...]]] = {}
    for p in PAX:
        by_pnr.setdefault(p[0], []).append(p)
    segments, customers = [], []
    for p in PAX:
        pnr, first, last, ptype, ssr, fare, anci, code, family, revenue, tier, freq = p
        party = by_pnr[pnr]
        adults = sum(1 for x in party if x[3] == "AD")
        infants = sum(1 for x in party if x[3] == "IN")
        children = sum(1 for x in party if x[3] == "CH")
        key = _key(first, last)
        adult_key = next((_key(x[1], x[2]) for x in party if x[3] == "AD"), None)
        for fid, o, d, dep in ((g9901, "KHI", "SHJ", _t(5)), (g9951, "SHJ", "HBE", _t(9))):
            segments.append(
                {
                    "flight_id": fid,
                    "pnr": pnr,
                    "customer_key": key,
                    "first_name": first,
                    "last_name": last,
                    "passenger_id": f"PAX{key[:12].upper()}",
                    "passport_number_synthetic": f"D{int(key[:8], 16) % 10**8:08d}",
                    "national_id_synthetic": f"784-1985-{int(key[:6], 16) % 10**7:07d}-3",
                    "identity_rule": "one-person-per-name",
                    "pax_type": ptype,
                    "flight_number": fid.split("_")[0],
                    "dep_utc": dep,
                    "origin": o,
                    "destination": d,
                    "booking_code": code,
                    "revenue_type": revenue,
                    "fare_family_synthetic": family,
                    "fare": fare / 2,
                    "ancillaries": anci / 2,
                    "baggage_kg": 20,
                    "has_meal": anci > 0,
                    "has_seat": anci > 0,
                    "sales_channel": "Web",
                    "pnr_size": len(party),
                    "adults": adults,
                    "children": children,
                    "infants": infants,
                    "ssr_code": ssr,
                    "ssr_source": "synthetic",
                    "infant_with_customer_key": adult_key if ptype == "IN" else None,
                }
            )
        flown = {"frequent": 18, "regular": 6, "occasional": 1}[freq]
        customers.append(
            {
                "customer_key": key,
                "is_loyalty_member": tier is not None,
                "flown_segments_12m": flown,
                "bookings_12m": max(flown // 2, 1),
                "ambiguous_common_name": False,
                "loyalty_tier_synthetic": tier,
                "travel_frequency_band": freq,
            }
        )
    return {
        "demo_flights": _append(ops / "flights.parquet", flights),
        "demo_pax_segments": _append(ops / "pax_segments.parquet", segments),
        "demo_customers": _append(ops / "customers.parquet", customers),
    }
