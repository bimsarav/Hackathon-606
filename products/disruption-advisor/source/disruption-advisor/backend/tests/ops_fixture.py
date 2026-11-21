"""A tiny, hand-made operating picture (Parquet) for tests: no airline data is used.

Day 2026-11-21, hub SHJ, times UTC.
  T1 (174 seats): F1 KHI-SHJ 08:00-10:00 · F2 SHJ-LHE 10:45-13:45 · F3 LHE-SHJ 14:30-17:30 · F4 SHJ-CAI 18:15-22:15
  T2 (174 seats): G1 DOH-SHJ 06:00-07:00 · G2 SHJ-BKK 11:00-17:00       (on the ground at SHJ: swap candidate)
  T3 (215 seats): X1 SHJ-CAI 12:00-16:00 (cancellation scenario) · Y1 SHJ-CAI 2026-11-22 09:00-13:00
  T4 (174 seats): H1 SHJ-CAI 11:30-15:30 (onward flight for connecting passengers from F1)
  T5 (215 seats): L1 SHJ-LHE 13:00-16:00 · L2 LHE-SHJ 17:00-20:00 (same-route flights for T1's F2/F3 round trip)
Seats: H1 is full, F4 has 2 free, Y1 has 5 free → 7 seats for the 10 seated passengers of X1 (+1 lap infant).
F2/F3 (SHJ-LHE-SHJ, phase 3 cancel/consolidate) carry 6 + 4 listed passengers; L1 has 10 free, L2 has 15 free.
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
    _flight("G9011", "T5", "SHJ", "LHE", t(13), t(16), 215, 205),
    _flight("G9012", "T5", "LHE", "SHJ", t(17), t(20), 215, 200),
    # T6: a later KHI-SHJ, so a cancelled F1's connecting passengers can be re-protected through SHJ (gap 3)
    _flight("G9007", "T6", "KHI", "SHJ", t(12), t(14), 174, 100),
]
F1, X1 = FLIGHTS[0]["flight_id"], FLIGHTS[6]["flight_id"]
F2, F3 = FLIGHTS[1]["flight_id"], FLIGHTS[2]["flight_id"]


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
        "sales_channel": "Web",
        # booking-class level from the fares list (E30 mid-ladder; DU = staff code, not sold: None)
        "booking_class_level": None if kw.get("booking_code") == "DU" else 0.5,
        # PNRB travels with an infant and its head b0000001 is a Silver member: a family account (loyalty sample)
        "family_account_synthetic": pnr == "PNRB",
        "family_head_synthetic": key == "b0000001",
        "family_tier_synthetic": "Silver" if pnr == "PNRB" else None,
        "family_priority_synthetic": "Low" if pnr == "PNRB" else None,
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
    # Passengers of T1's round trip F2 (SHJ-LHE) / F3 (LHE-SHJ), rebooked when phase 3 cancels the pair.
    _pax(F2, "RTA", "r0000001", "AD", "SHJ", "LHE", t(10, 45), pnr_size=2, adults=2),
    _pax(F2, "RTA", "r0000002", "AD", "SHJ", "LHE", t(10, 45), pnr_size=2, adults=2),
    *[_pax(F2, f"RTB{i}", f"s000000{i}", "AD", "SHJ", "LHE", t(10, 45)) for i in range(1, 5)],
    *[_pax(F3, f"RTC{i}", f"u000000{i}", "AD", "LHE", "SHJ", t(14, 30)) for i in range(1, 5)],
]

LOYALTY = {"g": ("Gold", "Medium", 132000), "b0000001": ("Silver", "Low", 61500)}  # key prefix or key


def _loyalty(k: str) -> tuple[str, str, int] | None:
    if k == "b0000001":
        return LOYALTY[k]
    return LOYALTY["g"] if k.startswith("g") else None


CUSTOMERS = [
    {
        "customer_key": k,
        "is_loyalty_member": _loyalty(k) is not None,
        "loyalty_tier_synthetic": (_loyalty(k) or (None,))[0],
        "loyalty_priority": (_loyalty(k) or (None, None))[1],
        "loyalty_id_synthetic": f"G9{sum(map(ord, k)) * 104729 % 10**9:09d}" if _loyalty(k) else None,
        "available_points_synthetic": (_loyalty(k) or (None, None, None))[2],
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
        # fares list (gap 3): KHI/SHJ/CAI is sold as a connection; LHE/SHJ/CAI too (but its only pair misses MCT)
        "sold_connections": [
            {"origin": "KHI", "hub": "SHJ", "destination": "CAI"},
            {"origin": "LHE", "hub": "SHJ", "destination": "CAI"},
        ],
        "booking_class_levels": [
            {
                "booking_code": "E30",
                "ladder": 0.105,
                "onds": 3012,
                "median_one_way_aed": 900.0,
                "window_passengers": 19004,
                "level": 0.5,
            },
        ],
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


# Crew FDP, written only by the crew tests so the other tests keep their costs. G9002 has a roster
# with 100 minutes of headroom (captain tightest), G9003 none but an estimate from its history (170 minutes, so a
# 150-minute delay leaves 20: tight); the other flights have no crew data.
def write_crew(ops: Path) -> None:
    crew_flights = [
        {
            "flight_id": F2,
            "flight_number": "G9002",
            "std": t(10, 45),
            "crew": 6,
            "pilots": 2,
            "headroom_minutes": 100,
            "tightest": "CP",
            "planned_fdp": 560,
            "max_fdp": 660,
            "sign_in": t(9, 45),
        }
    ]
    estimates = [
        {"flight_number": "G9003", "flights": 40, "headroom_p10": 170, "headroom_median": 260, "tightest": "FO"},
    ]
    pq.write_table(pa.Table.from_pylist(crew_flights), ops / "crew_flights.parquet")
    pq.write_table(pa.Table.from_pylist(estimates), ops / "crew_fdp_estimates.parquet")
    (ops / "crew_fdp.json").write_text(
        '{"summary": {"duties": 2, "headroom_median": 135},'
        ' "extra_delay": [{"extra_minutes": 60, "pct_over_max": 4.2}]}'
    )
