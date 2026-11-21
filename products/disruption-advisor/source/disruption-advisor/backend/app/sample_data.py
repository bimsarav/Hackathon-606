"""Test data upload: a few flights and their passengers, added to the operating picture without touching the ingest.

Two CSV sheets (flights, passengers) are checked and, when clean, stored as small Parquet files in their own folder
(``test_data_dir``). The operating store reads that folder on top of the real data (``OpsStore``), so the flights
appear in search and every scenario, rebooking and reward view works for them. The real data and the trained
models are never changed; uploading again replaces the earlier test data, and "remove" deletes it.

Everything the sheets do not hold is filled with labelled assumptions: capacity_source 'judge-test-data', synthetic
passport and national ids, fare by fare family. Times are UTC. A passenger who also appears on a later flight (same
booking reference and name) has an onward flight, so connections and missed connections work.
"""

from __future__ import annotations

import csv
import hashlib
import io
import json
import logging
import re
import shutil
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Annotated, Any

import pyarrow as pa
import pyarrow.parquet as pq
from fastapi import APIRouter, Request
from pydantic import BaseModel, Field

from app.auth import EvaluatorUser
from app.ingest.build import LOYALTY_POINTS_BASE, LOYALTY_POINTS_PER_FLIGHT, LOYALTY_PRIORITY
from app.ml import delay_risk

log = logging.getLogger(__name__)
SOURCE = "judge-test-data"
TABLES = ("flights", "pax_segments", "customers")
RISK_TABLES = ("flight_risk", "connection_risk")  # delay risk of the test flights, scored with the saved model
MANIFEST = "manifest.json"
MAX_FLIGHTS = 50
MAX_PASSENGER_ROWS = 3000
MAX_ERRORS = 40
MAX_CHARS = 1_000_000

TIERS = {"none": None, "basic": "Basic", "silver": "Silver", "gold": "Gold", "platinum": "Platinum"}
FAMILIES = {"basic": "Basic", "value": "Value", "ultimate": "Ultimate"}
FARE_BY_FAMILY = {"Basic": 330.0, "Value": 520.0, "Ultimate": 1250.0}
CODE_BY_FAMILY = {"Basic": "E20", "Value": "E30", "Ultimate": "E40"}
FREQUENCY = {"occasional": 1, "regular": 6, "frequent": 18}
PAX_TYPES = ("AD", "CH", "IN")

FLIGHT_FIELDS: list[dict[str, Any]] = [
    {
        "name": "flight_number",
        "required": True,
        "example": "G9981",
        "help": "Carrier code and number, 3 to 8 letters or digits.",
    },
    {"name": "date", "required": True, "example": "2026-11-22", "help": "Departure date, YYYY-MM-DD (UTC)."},
    {"name": "origin", "required": True, "example": "KHI", "help": "Departure airport, 3-letter IATA code."},
    {"name": "destination", "required": True, "example": "SHJ", "help": "Arrival airport, 3-letter IATA code."},
    {"name": "std", "required": True, "example": "05:00", "help": "Scheduled departure, HH:MM UTC."},
    {
        "name": "sta",
        "required": True,
        "example": "07:30",
        "help": "Scheduled arrival, HH:MM UTC (earlier than std means the next day).",
    },
    {
        "name": "aircraft_registration",
        "required": True,
        "example": "A6-TS1",
        "help": "Aircraft (tail). Flights of one aircraft form its rotation.",
    },
    {"name": "seat_capacity", "required": True, "example": "174", "help": "Seats on the aircraft, 1 to 600."},
    {
        "name": "booked_seats",
        "required": False,
        "example": "160",
        "help": (
            "Seats already sold. Empty: the number of passenger rows you list for the flight. "
            "A full flight (equal to capacity) leaves no seats for rebooking."
        ),
    },
]
PASSENGER_FIELDS: list[dict[str, Any]] = [
    {
        "name": "pnr",
        "required": True,
        "example": "AB12CD",
        "help": "Booking reference. Passengers sharing it travel together.",
    },
    {
        "name": "first_name",
        "required": True,
        "example": "Ahmed",
        "help": "First name (used only to tell people apart).",
    },
    {"name": "last_name", "required": True, "example": "Raza", "help": "Last name."},
    {"name": "pax_type", "required": True, "example": "AD", "help": "AD adult, CH child or IN infant."},
    {"name": "flight_number", "required": True, "example": "G9981", "help": "A flight from the flights sheet."},
    {"name": "date", "required": True, "example": "2026-11-22", "help": "That flight's date."},
    {"name": "fare_family", "required": False, "example": "Value", "help": "Basic, Value or Ultimate. Empty: Basic."},
    {
        "name": "fare_aed",
        "required": False,
        "example": "520",
        "help": "Fare of this flight in AED. Empty: typical fare of the fare family.",
    },
    {
        "name": "loyalty_tier",
        "required": False,
        "example": "Gold",
        "help": "none, Basic, Silver, Gold or Platinum. Empty: none.",
    },
    {
        "name": "travel_frequency",
        "required": False,
        "example": "regular",
        "help": "occasional, regular or frequent. Empty: occasional.",
    },
    {
        "name": "special_service",
        "required": False,
        "example": "WCHR",
        "help": "Special service code such as WCHR (wheelchair), PREG (pregnant) or INFT (infant). Empty: none.",
    },
]
FLIGHT_EXAMPLE = [
    "G9981,2026-11-22,KHI,SHJ,05:00,07:30,A6-TS1,174,160",
    "G9983,2026-11-22,SHJ,HBE,09:00,13:30,A6-TS2,174,170",
]
PASSENGER_EXAMPLE = [
    "AB12CD,Ahmed,Raza,AD,G9981,2026-11-22,Basic,,none,occasional,WCHR",
    "AB12CD,Ahmed,Raza,AD,G9983,2026-11-22,Basic,,none,occasional,WCHR",
    "EF34GH,Omar,Siddiqui,AD,G9981,2026-11-22,Ultimate,1450,Platinum,frequent,",
    "EF34GH,Omar,Siddiqui,AD,G9983,2026-11-22,Ultimate,1450,Platinum,frequent,",
]


def spec() -> dict[str, Any]:
    """What the upload page shows: files, columns, limits and ready-to-fill templates."""

    def template(fields: list[dict[str, Any]], rows: list[str]) -> str:
        return "\n".join([",".join(f["name"] for f in fields), *rows]) + "\n"

    return {
        "files": [
            {
                "key": "flights",
                "title": "Flights sheet",
                "file_name": "flights.csv",
                "purpose": "One row per flight you want to test.",
                "fields": FLIGHT_FIELDS,
                "template": template(FLIGHT_FIELDS, FLIGHT_EXAMPLE),
            },
            {
                "key": "passengers",
                "title": "Passengers sheet",
                "file_name": "passengers.csv",
                "purpose": (
                    "One row per passenger per flight. A passenger on two flights has two rows "
                    "(the second flight is the onward flight)."
                ),
                "fields": PASSENGER_FIELDS,
                "template": template(PASSENGER_FIELDS, PASSENGER_EXAMPLE),
            },
        ],
        "format": "CSV, comma separated, first row = column names (UTF-8). Times are UTC.",
        "limits": {"flights": MAX_FLIGHTS, "passenger_rows": MAX_PASSENGER_ROWS},
        "notes": [
            (
                "The flights are added to the live data and labelled 'judge test data'; "
                "the real data and the trained models are unchanged."
            ),
            ("Uploading again replaces the earlier test data. 'Remove test data' deletes it."),
            (
                "Delay history (past delays of the route and aircraft) comes from the live data. "
                "A new route has less history behind its risk figure."
            ),
            (
                "Loyalty tier, fare and special service come from your sheet; "
                "everything else about a passenger is filled in with labelled placeholders."
            ),
        ],
    }


@dataclass
class Issue:
    file: str
    row: int | None
    column: str | None
    message: str

    def as_dict(self) -> dict[str, Any]:
        return {"file": self.file, "row": self.row, "column": self.column, "message": self.message}


@dataclass
class Checked:
    issues: list[Issue] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    flights: list[dict[str, Any]] = field(default_factory=list)
    segments: list[dict[str, Any]] = field(default_factory=list)
    customers: list[dict[str, Any]] = field(default_factory=list)

    def add(self, file: str, row: int | None, column: str | None, message: str) -> None:
        if len(self.issues) < MAX_ERRORS:
            self.issues.append(Issue(file, row, column, message))
        elif len(self.issues) == MAX_ERRORS:
            self.issues.append(Issue(file, None, None, "More problems found; fix these first."))

    @property
    def ok(self) -> bool:
        return not self.issues


def _read(text: str, file: str, fields: list[dict[str, Any]], out: Checked) -> list[tuple[int, dict[str, str]]]:
    text = text.lstrip("﻿")
    if not text.strip():
        out.add(file, None, None, "The file is empty.")
        return []
    first = text.splitlines()[0]
    delimiter = ";" if ";" in first and "," not in first else ","
    reader = csv.reader(io.StringIO(text), delimiter=delimiter)
    header = [h.strip().lower() for h in next(reader, [])]
    names = [f["name"] for f in fields]
    missing = [f["name"] for f in fields if f["required"] and f["name"] not in header]
    if missing:
        out.add(file, 1, None, f"Missing column(s): {', '.join(missing)}. Expected: {', '.join(names)}.")
        return []
    extra = [h for h in header if h and h not in names]
    if extra:
        out.warnings.append(f"{file}: ignored unknown column(s): {', '.join(extra)}.")
    rows: list[tuple[int, dict[str, str]]] = []
    for number, cells in enumerate(reader, start=2):
        if not any(c.strip() for c in cells):
            continue
        rows.append((number, {h: (cells[i].strip() if i < len(cells) else "") for i, h in enumerate(header) if h}))
    if not rows:
        out.add(file, None, None, "The file has a header but no rows.")
    return rows


def _iata(value: str) -> bool:
    return bool(re.fullmatch(r"[A-Z]{3}", value))


def _day(value: str) -> datetime | None:
    try:
        return datetime.strptime(value, "%Y-%m-%d")
    except ValueError:
        return None


def _clock(value: str) -> timedelta | None:
    match = re.fullmatch(r"([01]?\d|2[0-3]):([0-5]\d)(?::[0-5]\d)?", value)
    return timedelta(hours=int(match[1]), minutes=int(match[2])) if match else None


def flight_id(number: str, std: datetime) -> str:
    return f"{number}_{std:%Y%m%d%H%M}"


def _key(first: str, last: str) -> str:
    return hashlib.sha256(f"test|{first.lower()}|{last.lower()}".encode()).hexdigest()[:16]


def check(flights_csv: str, passengers_csv: str, existing_ids: set[str], known_routes: set[tuple[str, str]]) -> Checked:
    """Validate both sheets and build the table rows. ``existing_ids``: flight ids of the real data (no clashes)."""
    out = Checked()
    flight_rows = _read(flights_csv, "flights.csv", FLIGHT_FIELDS, out)
    pax_rows = _read(passengers_csv, "passengers.csv", PASSENGER_FIELDS, out)
    if len(flight_rows) > MAX_FLIGHTS:
        out.add("flights.csv", None, None, f"At most {MAX_FLIGHTS} flights per upload.")
    if len(pax_rows) > MAX_PASSENGER_ROWS:
        out.add("passengers.csv", None, None, f"At most {MAX_PASSENGER_ROWS} passenger rows per upload.")
    if not out.ok:
        return out

    by_flight: dict[tuple[str, str], dict[str, Any]] = {}
    for n, r in flight_rows:
        number = r["flight_number"].upper().replace(" ", "")
        origin, dest, tail = r["origin"].upper(), r["destination"].upper(), r["aircraft_registration"].upper()
        day, dep, arr = _day(r["date"]), _clock(r["std"]), _clock(r["sta"])
        if not re.fullmatch(r"[A-Z0-9]{3,8}", number):
            out.add("flights.csv", n, "flight_number", f"'{r['flight_number']}' is not a flight number such as G9981.")
        if not _iata(origin):
            out.add("flights.csv", n, "origin", f"'{r['origin']}' is not a 3-letter airport code.")
        if not _iata(dest):
            out.add("flights.csv", n, "destination", f"'{r['destination']}' is not a 3-letter airport code.")
        if _iata(origin) and origin == dest:
            out.add("flights.csv", n, "destination", "Origin and destination are the same.")
        if day is None:
            out.add("flights.csv", n, "date", f"'{r['date']}' is not a date (use YYYY-MM-DD).")
        if dep is None:
            out.add("flights.csv", n, "std", f"'{r['std']}' is not a time (use HH:MM).")
        if arr is None:
            out.add("flights.csv", n, "sta", f"'{r['sta']}' is not a time (use HH:MM).")
        if not re.fullmatch(r"[A-Z0-9-]{3,10}", tail):
            out.add(
                "flights.csv",
                n,
                "aircraft_registration",
                f"'{r['aircraft_registration']}' is not an aircraft registration such as A6-TS1.",
            )
        try:
            capacity = int(r["seat_capacity"])
            if not 1 <= capacity <= 600:
                raise ValueError
        except ValueError:
            out.add("flights.csv", n, "seat_capacity", f"'{r['seat_capacity']}' is not a seat count between 1 and 600.")
            capacity = 0
        booked: int | None = None
        if r.get("booked_seats"):
            try:
                booked = int(r["booked_seats"])
                if booked < 0 or (capacity and booked > capacity):
                    raise ValueError
            except ValueError:
                out.add(
                    "flights.csv",
                    n,
                    "booked_seats",
                    f"'{r['booked_seats']}' is not a number from 0 to the seat capacity.",
                )
                booked = None
        if day is None or dep is None or arr is None or not capacity:
            continue
        std = day + dep
        sta = day + arr + (timedelta(days=1) if arr <= dep else timedelta())
        slot = (number, r["date"])
        if slot in by_flight:
            out.add("flights.csv", n, "flight_number", f"{number} on {r['date']} is listed twice.")
            continue
        fid = flight_id(number, std)
        if fid in existing_ids:
            out.add(
                "flights.csv",
                n,
                "flight_number",
                f"{number} on {r['date']} at {r['std']} already exists in the live data.",
            )
            continue
        by_flight[slot] = {
            "flight_id": fid,
            "number": number,
            "origin": origin,
            "destination": dest,
            "std": std,
            "sta": sta,
            "tail": tail,
            "capacity": capacity,
            "booked": booked,
            "row": n,
            "pax": 0,
        }

    people: dict[tuple[str, str, str], int] = {}
    customers: dict[str, dict[str, Any]] = {}
    pnr_party: dict[str, set[tuple[str, str]]] = {}
    staged: list[dict[str, Any]] = []
    for n, r in pax_rows:
        number, pnr = r["flight_number"].upper().replace(" ", ""), r["pnr"].upper()
        first, last, ptype = r["first_name"], r["last_name"], r["pax_type"].upper()
        flight = by_flight.get((number, r["date"]))
        if not pnr or not re.fullmatch(r"[A-Z0-9]{1,12}", pnr):
            out.add("passengers.csv", n, "pnr", f"'{r['pnr']}' is not a booking reference (letters and digits).")
        if not first or not last:
            out.add("passengers.csv", n, "first_name", "First and last name are required.")
        if ptype not in PAX_TYPES:
            out.add("passengers.csv", n, "pax_type", f"'{r['pax_type']}' must be AD, CH or IN.")
        if flight is None:
            out.add("passengers.csv", n, "flight_number", f"No flight {number} on {r['date']} in the flights sheet.")
        family = FAMILIES.get(r.get("fare_family", "").lower() or "basic")
        if family is None:
            out.add("passengers.csv", n, "fare_family", f"'{r['fare_family']}' must be Basic, Value or Ultimate.")
        tier_text = r.get("loyalty_tier", "").lower() or "none"
        if tier_text not in TIERS:
            out.add(
                "passengers.csv",
                n,
                "loyalty_tier",
                f"'{r['loyalty_tier']}' must be none, Basic, Silver, Gold or Platinum.",
            )
        freq = r.get("travel_frequency", "").lower() or "occasional"
        if freq not in FREQUENCY:
            out.add(
                "passengers.csv",
                n,
                "travel_frequency",
                f"'{r['travel_frequency']}' must be occasional, regular or frequent.",
            )
        ssr = r.get("special_service", "").upper() or None
        if ssr and not re.fullmatch(r"[A-Z]{4}", ssr):
            out.add("passengers.csv", n, "special_service", f"'{r['special_service']}' is not a 4-letter service code.")
        fare: float | None = None
        if r.get("fare_aed"):
            try:
                fare = float(r["fare_aed"])
                if fare < 0:
                    raise ValueError
            except ValueError:
                out.add("passengers.csv", n, "fare_aed", f"'{r['fare_aed']}' is not an amount.")
        if (
            flight is None
            or family is None
            or tier_text not in TIERS
            or freq not in FREQUENCY
            or ptype not in PAX_TYPES
        ):
            continue
        if not first or not last or not pnr:
            continue
        person = (flight["flight_id"], first.lower(), last.lower())
        if person in people:
            out.add("passengers.csv", n, "first_name", f"{first} {last} is already on {number} (row {people[person]}).")
            continue
        people[person] = n
        flight["pax"] += 1
        pnr_party.setdefault(pnr, set()).add((first.lower(), last.lower()))
        staged.append(
            {
                "r": r,
                "flight": flight,
                "pnr": pnr,
                "first": first,
                "last": last,
                "ptype": ptype,
                "family": family,
                "tier": TIERS[tier_text],
                "freq": freq,
                "ssr": ssr,
                "fare": fare,
            }
        )
    if not out.ok:
        return out

    for item in staged:
        flight, tier, freq = item["flight"], item["tier"], item["freq"]
        key = _key(item["first"], item["last"])
        party = pnr_party[item["pnr"]]
        types = [s["ptype"] for s in staged if s["pnr"] == item["pnr"] and s["flight"] is flight]
        fare = item["fare"] if item["fare"] is not None else FARE_BY_FAMILY[item["family"]]
        adult = next(
            (_key(s["first"], s["last"]) for s in staged if s["pnr"] == item["pnr"] and s["ptype"] == "AD"), None
        )
        out.segments.append(
            {
                "flight_id": flight["flight_id"],
                "pnr": item["pnr"],
                "customer_key": key,
                "passenger_id": f"PAX{key[:12].upper()}",
                "passport_number_synthetic": f"T{int(key[:8], 16) % 10**8:08d}",
                "national_id_synthetic": f"784-1985-{int(key[:6], 16) % 10**7:07d}-3",
                "identity_rule": "one-person-per-name",
                "pax_type": item["ptype"],
                "flight_number": flight["number"],
                "dep_utc": flight["std"],
                "origin": flight["origin"],
                "destination": flight["destination"],
                "booking_code": CODE_BY_FAMILY[item["family"]],
                "revenue_type": "REVENUE",
                "fare_family_synthetic": item["family"],
                "fare": fare,
                "ancillaries": 0.0,
                "baggage_kg": 20,
                "has_meal": False,
                "has_seat": False,
                "sales_channel": "Web",
                "pnr_size": len(party),
                "adults": types.count("AD"),
                "children": types.count("CH"),
                "infants": types.count("IN"),
                "ssr_code": item["ssr"],
                "ssr_source": "judge-test-data",
                "infant_with_customer_key": adult if item["ptype"] == "IN" else None,
            }
        )
        flown = FREQUENCY[freq]
        customers.setdefault(
            key,
            {
                "customer_key": key,
                "is_loyalty_member": tier is not None,
                "flown_segments_12m": flown,
                "bookings_12m": max(flown // 2, 1),
                "ambiguous_common_name": False,
                "loyalty_tier_synthetic": tier,
                "loyalty_priority": LOYALTY_PRIORITY.get(tier or ""),
                "loyalty_id_synthetic": f"G9{int(key[:8], 16) % 10**9:09d}" if tier else None,
                "available_points_synthetic": LOYALTY_POINTS_BASE[tier] + LOYALTY_POINTS_PER_FLIGHT * flown
                if tier
                else None,
                "travel_frequency_band": freq,
            },
        )
    out.customers = list(customers.values())

    for flight in by_flight.values():
        booked = flight["booked"] if flight["booked"] is not None else flight["pax"]
        if booked < flight["pax"]:
            out.add(
                "flights.csv",
                flight["row"],
                "booked_seats",
                f"{flight['number']}: booked_seats {booked} is below the {flight['pax']} passenger rows listed.",
            )
            continue
        out.flights.append(
            {
                "flight_id": flight["flight_id"],
                "airline": flight["number"][:2],
                "tail": flight["tail"],
                "flight_number": flight["number"],
                "origin": flight["origin"],
                "destination": flight["destination"],
                "std": flight["std"],
                "sta": flight["sta"],
                "op_type": "J-Normal Service (judge test data)",
                "status": "SCH",
                "pax_reported": booked,
                "aircraft_model": f"Test aircraft {flight['capacity']} seats",
                "capacity": flight["capacity"],
                "capacity_source": SOURCE,
                "booked_seats": booked,
                "booked_pax": booked,
                "available_seats": flight["capacity"] - booked,
                "_pax": flight["pax"],
            }
        )
        if not flight["pax"]:
            out.warnings.append(f"{flight['number']} has no passengers, so passenger views will be empty.")
        if (flight["origin"], flight["destination"]) not in known_routes:
            out.warnings.append(
                f"{flight['number']} {flight['origin']}-{flight['destination']}: the live data has no "
                "flights on this route, so its delay risk has little history behind it."
            )
    return out


# --- storage ---------------------------------------------------------------------------------------------------
def version(directory: Path) -> int | None:
    """Changes whenever test data or a flight edit is added, replaced or removed (the store reloads on a change)."""
    try:
        uploaded = (directory / MANIFEST).stat().st_mtime_ns
    except OSError:
        uploaded = 0
    try:
        edited = (directory / "flight_edits.json").stat().st_mtime_ns
    except OSError:
        edited = 0
    return (uploaded + edited) or None


def status(directory: Path) -> dict[str, Any]:
    try:
        text = (directory / MANIFEST).read_text()
    except OSError:
        return {"loaded": False}
    manifest = json.loads(text) if text.strip() else {}
    return dict(manifest) if manifest else {"loaded": False}


def clear(directory: Path) -> None:
    (directory / MANIFEST).unlink(missing_ok=True)
    for name in (*TABLES, *RISK_TABLES):
        (directory / f"{name}.parquet").unlink(missing_ok=True)


def save(directory: Path, checked: Checked, user: str, ops_dir: Path | None = None) -> dict[str, Any]:
    """Replace the stored test data. Tables are written first and the manifest last, so readers see all or nothing."""
    directory.mkdir(parents=True, exist_ok=True)
    clear(directory)
    flights = [{k: v for k, v in f.items() if not k.startswith("_")} for f in checked.flights]
    for name, rows in (("flights", flights), ("pax_segments", checked.segments), ("customers", checked.customers)):
        tmp = directory / f"{name}.tmp"
        pq.write_table(pa.Table.from_pylist(rows), tmp, compression="zstd")
        shutil.move(tmp, directory / f"{name}.parquet")
    risk: dict[str, Any] = {"scored": 0, "connections": 0, "reason": "not scored"}
    if ops_dir is not None:
        try:
            risk = delay_risk.score_test_flights(ops_dir, directory)
        except Exception as exc:
            log.warning("test flights not scored: %s", exc)
            risk = {"scored": 0, "connections": 0, "reason": f"scoring failed: {exc}"}
    manifest = {
        "loaded": True,
        "risk": risk,
        "uploaded_by": user,
        "uploaded_at": datetime.now(UTC).isoformat(timespec="seconds"),
        "counts": {
            "flights": len(flights),
            "passenger_segments": len(checked.segments),
            "passengers": len(checked.customers),
        },
        "flights": [
            {
                "flight_id": f["flight_id"],
                "flight_number": f["flight_number"],
                "route": f"{f['origin']}-{f['destination']}",
                "std": f["std"].strftime("%Y-%m-%d %H:%M"),
                "sta": f["sta"].strftime("%Y-%m-%d %H:%M"),
                "tail": f["tail"],
                "capacity": f["capacity"],
                "booked_seats": f["booked_seats"],
                "passengers": f["_pax"],
            }
            for f in checked.flights
        ],
    }
    (directory / MANIFEST).write_text(json.dumps(manifest))
    return manifest


# --- API -------------------------------------------------------------------------------------------------------
class UploadRequest(BaseModel):
    flights_csv: Annotated[str, Field(max_length=MAX_CHARS)]
    passengers_csv: Annotated[str, Field(max_length=MAX_CHARS)]
    commit: bool = False  # False: check only


router = APIRouter(prefix="/api/v1/test-data", tags=["test-data"])


@router.get("/spec")
def get_spec(_: EvaluatorUser) -> dict[str, Any]:
    return spec()


@router.get("")
def get_status(request: Request, _: EvaluatorUser) -> dict[str, Any]:
    return status(request.app.state.settings.test_data_dir)


@router.post("")
def upload(payload: UploadRequest, request: Request, user: EvaluatorUser) -> dict[str, Any]:
    settings = request.app.state.settings
    store = request.app.state.get_store()
    existing: set[str] = set()
    routes: set[tuple[str, str]] = set()
    if store is not None:
        for row in store.query("SELECT flight_id, origin, destination, capacity_source FROM flights"):
            if row["capacity_source"] != SOURCE:  # the earlier test data is being replaced
                existing.add(row["flight_id"])
                routes.add((row["origin"], row["destination"]))
    checked = check(payload.flights_csv, payload.passengers_csv, existing, routes)
    report: dict[str, Any] = {
        "ok": checked.ok,
        "errors": [i.as_dict() for i in checked.issues],
        "warnings": checked.warnings,
        "committed": False,
        "summary": {
            "flights": len(checked.flights),
            "passenger_segments": len(checked.segments),
            "passengers": len(checked.customers),
        },
    }
    if checked.ok and payload.commit:
        report["status"] = save(
            settings.test_data_dir, checked, f"{user.username} ({user.role})", settings.data_dir / "ops"
        )
        report["committed"] = True
    return report


@router.delete("")
def remove(request: Request, _: EvaluatorUser) -> dict[str, Any]:
    clear(request.app.state.settings.test_data_dir)
    return {"loaded": False}
