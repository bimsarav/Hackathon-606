"""A tiny, hand-made operating picture (Parquet) for tests: no airline data is used.

Day 2026-11-21, hub SHJ, times UTC.
  T1 (174 seats): F1 KHI-SHJ 08:00-10:00 · F2 SHJ-LHE 10:45-13:45 · F3 LHE-SHJ 14:30-17:30 · F4 SHJ-CAI 18:15-22:15
  T2 (174 seats): G1 DOH-SHJ 06:00-07:00 · G2 SHJ-BKK 11:00-17:00       (on the ground at SHJ: swap candidate)
  T3 (215 seats): X1 SHJ-CAI 12:00-16:00 (cancellation scenario) · Y1 SHJ-CAI 2026-11-22 09:00-13:00
  T4 (174 seats): H1 SHJ-CAI 11:30-15:30 (onward flight for connecting passengers from F1)
Seats: H1 is full, F4 has 2 free, Y1 has 5 free → 7 seats for the 10 seated passengers of X1 (+1 lap infant).
"""

from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

import pyarrow as pa
import pyarrow.parquet as pq

D = datetime(2026, 11, 21)


def t(h: int, m: int = 0, day: int = 21) -> datetime:
    return datetime(2026, 11, day, h, m)


def _flight(fn: str, tail: str, o: str, d: str, std: datetime, sta: datetime, cap: int, booked: int) -> dict[str, Any]:
    return {
        "flight_id": f"{fn}_{std:%Y%m%d%H%M}",
        "flight_number": fn,
        "airline": "G9",
        "tail": tail,
        "origin": o,
        "destination": d,
        "std": std,
        "sta": sta,
        "capacity": cap,
        "booked_seats": booked,
        "booked_pax": booked,
        "aircraft_model": "A321" if cap == 215 else "A320-174",
        "capacity_source": "inventory-exact",
    }


FLIGHTS = [
    _flight("G9001", "T1", "KHI", "SHJ", t(8), t(10), 174, 150),
    _flight("G9002", "T1", "SHJ", "LHE", t(10, 45), t(13, 45), 174, 160),
    _flight("G9003", "T1", "LHE", "SHJ", t(14, 30), t(17, 30), 174, 140),
    _flight("G9004", "T1", "SHJ", "CAI", t(18, 15), t(22, 15), 174, 172),
    _flight("G9101", "T2", "DOH", "SHJ", t(6), t(7), 174, 100),
    _flight("G9102", "T2", "SHJ", "BKK", t(11), t(17), 174, 120),
    _flight("G9201", "T3", "SHJ", "CAI", t(12), t(16), 215, 10),
    _flight("G9201", "T3", "SHJ", "CAI", t(9, day=22), t(13, day=22), 215, 210),
    _flight("G9301", "T4", "SHJ", "CAI", t(11, 30), t(15, 30), 174, 174),
]
F1, X1 = FLIGHTS[0]["flight_id"], FLIGHTS[6]["flight_id"]


def _pax(fid: str, pnr: str, key: str, ptype: str, o: str, d: str, dep: datetime, **kw: Any) -> dict[str, Any]:
    row = {
        "flight_id": fid,
        "pnr": pnr,
        "customer_key": key,
        "passenger_id": f"PAX{key.upper()}",
        "passport_number_synthetic": f"T{sum(map(ord, key)) * 7919 % 10**8:08d}",
        "national_id_synthetic": f"784-1990-{sum(map(ord, key)) % 10**7:07d}-1",
        "identity_rule": "one-person-per-name",
        "pax_type": ptype,
        "origin": o,
        "destination": d,
        "dep_utc": dep,
        "booking_code": "E30",
        "revenue_type": "REVENUE",
        "fare_family_synthetic": "Value",
        "fare": 500.0,
        "ancillaries": 0.0,
        "baggage_kg": 20,
        "has_meal": False,
        "has_seat": False,
        "pnr_size": 1,
        "adults": 1,
        "children": 0,
        "infants": 0,
        "ssr_code": None,
        "ssr_source": "synthetic",
    }
    row.update(kw)
    return row


PAX = [
    # Connecting passengers on F1 (KHI-SHJ) continuing on H1 (SHJ-CAI 11:30): planned 90 min connection.
    _pax(F1, "CONN01", "c0000001", "AD", "KHI", "SHJ", t(8)),
    _pax(FLIGHTS[8]["flight_id"], "CONN01", "c0000001", "AD", "SHJ", "CAI", t(11, 30)),
    _pax(F1, "CONN02", "c0000002", "AD", "KHI", "SHJ", t(8)),
    _pax(FLIGHTS[8]["flight_id"], "CONN02", "c0000002", "AD", "SHJ", "CAI", t(11, 30)),
    # Passengers of the cancelled X1 (SHJ-CAI 12:00): 10 seated + 1 lap infant.
    _pax(X1, "PNRA", "a0000001", "AD", "SHJ", "CAI", t(12), ssr_code="WCHR"),
    _pax(X1, "PNRB", "b0000001", "AD", "SHJ", "CAI", t(12), pnr_size=3, adults=2, infants=1),
    _pax(X1, "PNRB", "b0000002", "AD", "SHJ", "CAI", t(12), pnr_size=3, adults=2, infants=1),
    _pax(X1, "PNRB", "b0000003", "IN", "SHJ", "CAI", t(12), pnr_size=3, adults=2, infants=1, ssr_code="INFT"),
    _pax(X1, "PNRC", "g0000001", "AD", "SHJ", "CAI", t(12), pnr_size=3, adults=3, fare=900.0, ancillaries=150.0),
    _pax(X1, "PNRC", "g0000002", "AD", "SHJ", "CAI", t(12), pnr_size=3, adults=3, fare=900.0, ancillaries=150.0),
    _pax(X1, "PNRC", "g0000003", "AD", "SHJ", "CAI", t(12), pnr_size=3, adults=3, fare=900.0, ancillaries=150.0),
    _pax(X1, "PNRD", "n0000001", "AD", "SHJ", "CAI", t(12), booking_code="DU", revenue_type="NON_REV", fare=0.0),
    _pax(X1, "PNRE", "e0000001", "AD", "SHJ", "CAI", t(12), pnr_size=2, adults=2, fare=200.0),
    _pax(X1, "PNRE", "e0000002", "AD", "SHJ", "CAI", t(12), pnr_size=2, adults=2, fare=200.0),
    _pax(X1, "PNRF", "f0000001", "AD", "SHJ", "CAI", t(12), fare=300.0),
]

CUSTOMERS = [
    {
        "customer_key": k,
        "is_loyalty_member": k.startswith("g"),
        "loyalty_tier_synthetic": "Gold" if k.startswith("g") else None,
        "travel_frequency_band": "frequent" if k.startswith("g") else "occasional",
        "flown_segments_12m": 14 if k.startswith("g") else 1,
        "ambiguous_common_name": False,
    }
    for k in sorted({p["customer_key"] for p in PAX})
]

AIRPORTS = [
    {
        "iata": "SHJ",
        "icao": "OMSJ",
        "name": "Sharjah",
        "country": "AE",
        "tz": "Asia/Dubai",
        "lat": "25.3286",
        "lon": "55.5172",
    },
    {
        "iata": "KHI",
        "icao": "OPKC",
        "name": "Karachi",
        "country": "PK",
        "tz": "Asia/Karachi",
        "lat": "24.9065",
        "lon": "67.1608",
    },
    {
        "iata": "LHE",
        "icao": "OPLA",
        "name": "Lahore",
        "country": "PK",
        "tz": "Asia/Karachi",
        "lat": "31.5216",
        "lon": "74.4036",
    },
    {
        "iata": "CAI",
        "icao": "HECA",
        "name": "Cairo",
        "country": "EG",
        "tz": "Africa/Cairo",
        "lat": "30.1219",
        "lon": "31.4056",
    },
    {
        "iata": "DOH",
        "icao": "OTHH",
        "name": "Doha",
        "country": "QA",
        "tz": "Asia/Qatar",
        "lat": "25.2731",
        "lon": "51.6081",
    },
    {
        "iata": "BKK",
        "icao": "VTBS",
        "name": "Bangkok",
        "country": "TH",
        "tz": "Asia/Bangkok",
        "lat": "13.6811",
        "lon": "100.7472",
    },
]


def write_ops(data_dir: Path) -> Path:
    ops = data_dir / "ops"
    ops.mkdir(parents=True, exist_ok=True)
    tables: dict[str, list[dict[str, Any]]] = {
        "flights": FLIGHTS,
        "pax_segments": PAX,
        "customers": CUSTOMERS,
        "airports": AIRPORTS,
        "mct": [
            {
                "ond_code": "KHI/SHJ/CAI",
                "origin": "KHI",
                "hub": "SHJ",
                "destination": "CAI",
                "min_minutes": 55,
                "max_minutes": 1200,
            }
        ],
        "aircraft": [
            {
                "registration": tail,
                "airline": "G9",
                "aircraft_model": "A320-174",
                "seats": 174,
                "model_source": "inventory-exact",
                "evidence_legs": 1,
                "max_pax_seen": 170,
            }
            for tail in ("T1", "T2", "T3", "T4")
        ],
        "booking_classes": [
            {
                "booking_code": "E30",
                "active_segments": 1,
                "avg_fare": 500.0,
                "revenue_type": "REVENUE",
                "fare_family_synthetic": "Value",
            }
        ],
    }
    for name, rows in tables.items():
        pq.write_table(pa.Table.from_pylist(rows), ops / f"{name}.parquet")
    pq.write_table(pa.Table.from_pylist(history()), ops / "history_flights.parquet")
    (ops / "ingest_report.json").write_text('{"counts": {"flights": 9}, "quality": {}}')
    return ops


# History for the delay-risk model (phase 2): 1 Jul - 18 Nov 2026, synthetic with a planted pattern.
# KHI-SHJ in the morning is late 60+ minutes on 70% of days; DOH-SHJ is almost always on time; the rest in between.
HISTORY_ROUTES = (
    ("G9001", "T1", "KHI", "SHJ", 8, 120, 0.70),
    ("G9002", "T1", "SHJ", "LHE", 11, 180, 0.30),
    ("G9101", "T2", "DOH", "SHJ", 6, 60, 0.03),
    ("G9102", "T2", "SHJ", "BKK", 11, 360, 0.15),
    ("G9301", "T4", "SHJ", "CAI", 11, 240, 0.10),
)


def history() -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    start = datetime(2026, 7, 1)
    for day in range(140):
        for n, (fn, tail, o, d, hour, block, late_share) in enumerate(HISTORY_ROUTES):
            std = start + timedelta(days=day, hours=hour)
            u = ((day * 7919 + n * 104729) % 1000) / 1000  # deterministic, evenly spread
            delay = 75 + (day % 4) * 20 if u < late_share else (day * 13 + n * 7) % 12
            sta = std + timedelta(minutes=block)
            rows.append(
                {
                    "flight_id": f"{fn}_{std:%Y%m%d%H%M}",
                    "airline": "G9",
                    "tail": tail,
                    "flight_number": fn,
                    "origin": o,
                    "destination": d,
                    "std": std,
                    "sta": sta,
                    "atd": std + timedelta(minutes=delay),
                    "ata": sta + timedelta(minutes=max(delay - 5, 0)),
                    "operated": True,
                    "diverted": False,
                    "aircraft_model": "A320-174",
                    "capacity": 174,
                    "booked_pax": 150,
                }
            )
    return rows
