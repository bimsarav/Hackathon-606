"""Evaluator edits of existing flights (table view in the Test data page).

An evaluator opens a flight (real or uploaded), changes its schedule, aircraft or seats and its passengers (type,
fare family, fare, loyalty tier, travel frequency, special service; remove or add a passenger) and saves. The edits
are stored as one small JSON file next to the test data (``flight_edits.json`` in ``test_data_dir``) and applied by
the operating store on top of the real data each time it loads; the Parquet files and the trained models are never
changed. Every scenario, rebooking, crew check and reward plan computed afterwards uses the edited data. Resetting a
flight deletes its entry. A changed loyalty tier or travel frequency belongs to the customer, so it shows on every
flight of that customer. The 7-day delay risk of an edited flight keeps its precomputed value.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Annotated, Any, Literal

import duckdb
from fastapi import APIRouter, HTTPException, Request, status
from fastapi import Path as PathParam
from pydantic import BaseModel, Field, field_validator

from app.auth import EvaluatorUser
from app.ingest.build import LOYALTY_PRIORITY

EDITS_FILE = "flight_edits.json"
EDIT_SOURCE = "evaluator-edit"
TIERS = ("none", "Basic", "Silver", "Gold", "Platinum")
FREQUENCIES = ("occasional", "regular", "frequent", "unknown")
MAX_PASSENGERS = 600
_HHMM = re.compile(r"^([01]\d|2[0-3]):[0-5]\d$")


# --- storage ---------------------------------------------------------------------------------------------------
def load(directory: Path | None) -> dict[str, Any]:
    if directory is None:
        return {}
    try:
        data = json.loads((directory / EDITS_FILE).read_text())
    except OSError:
        return {}
    except ValueError:
        return {}
    return dict(data) if isinstance(data, dict) else {}


def write(directory: Path, edits: dict[str, Any]) -> None:
    """Atomic replace, so a reading worker never sees half a file; an empty set removes the file."""
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / EDITS_FILE
    if not edits:
        path.unlink(missing_ok=True)
        return
    tmp = directory / f"{EDITS_FILE}.tmp"
    tmp.write_text(json.dumps(edits))
    os.replace(tmp, path)


def mtime(directory: Path | None) -> int:
    if directory is None:
        return 0
    try:
        return (directory / EDITS_FILE).stat().st_mtime_ns
    except OSError:
        return 0


# --- applying the edits to the in-memory tables ------------------------------------------------------------------
def _clock(day: datetime, hhmm: str) -> datetime:
    h, m = (int(x) for x in hhmm.split(":"))
    return datetime(day.year, day.month, day.day, h, m)


def _new_key(flight_id: str, pnr: str, index: int) -> str:
    return hashlib.sha256(f"edit|{flight_id}|{pnr}|{index}".encode()).hexdigest()[:16]


def _columns(con: duckdb.DuckDBPyConnection, table: str) -> set[str]:
    rows = con.execute("SELECT column_name FROM information_schema.columns WHERE table_name = ?", [table]).fetchall()
    return {r[0] for r in rows}


def apply(con: duckdb.DuckDBPyConnection, directory: Path | None) -> int:
    """Apply every saved flight edit to the store's tables. Returns the number of flights edited."""
    edits = load(directory)
    done = 0
    for flight_id, edit in edits.items():
        row = con.execute("SELECT std FROM flights WHERE flight_id = ?", [flight_id]).fetchone()
        if row is None:  # the flight is no longer in the data (e.g. removed test flight): nothing to apply
            continue
        f = edit["flight"]
        std = _clock(row[0], f["std"])
        sta = _clock(row[0], f["sta"])
        if sta <= std:
            sta += timedelta(days=1)
        values = {
            "std": std,
            "sta": sta,
            "tail": f["tail"],
            "capacity": f["capacity"],
            "booked_seats": f["booked_seats"],
            "booked_pax": f["booked_seats"],
            "available_seats": max(f["capacity"] - f["booked_seats"], 0),
            "capacity_source": EDIT_SOURCE,
        }
        have = _columns(con, "flights")
        sets = [k for k in values if k in have]
        con.execute(
            f"UPDATE flights SET {', '.join(f'{k} = ?' for k in sets)} WHERE flight_id = ?",
            [*[values[k] for k in sets], flight_id],
        )
        con.execute("UPDATE pax_segments SET dep_utc = ? WHERE flight_id = ?", [std, flight_id])
        template = con.execute("SELECT * FROM pax_segments WHERE flight_id = ? LIMIT 1", [flight_id]).fetchdf()
        for i, p in enumerate(edit.get("passengers", [])):
            tier = None if p["loyalty_tier"] == "none" else p["loyalty_tier"]
            key = p.get("customer_key")
            if key and p.get("remove"):
                con.execute("DELETE FROM pax_segments WHERE flight_id = ? AND customer_key = ?", [flight_id, key])
                continue
            if p.get("remove"):
                continue
            if not key:  # a passenger added by the evaluator: copy the flight's columns, then set the edited fields
                key = _new_key(flight_id, p["pnr"], i)
                if not template.empty:
                    con.register("seg_template", template)
                    replace = {
                        "customer_key": key,
                        "pnr": p["pnr"],
                        "passenger_id": f"PAX{key[:12].upper()}",
                        "pnr_size": 1,
                        "infant_with_customer_key": None,
                    }
                    present = [c for c in replace if c in template.columns]
                    clause = ", ".join(f"? AS {c}" for c in present)
                    con.execute(
                        f"INSERT INTO pax_segments BY NAME SELECT * REPLACE ({clause}) FROM seg_template",
                        [replace[c] for c in present],
                    )
                    con.unregister("seg_template")
                extra = {"ambiguous_common_name": False, "flown_segments_12m": 1, "bookings_12m": 1}
                cust_cols = _columns(con, "customers")
                fields = ["customer_key", *[c for c in extra if c in cust_cols]]
                con.execute(
                    f"INSERT INTO customers ({', '.join(fields)}) VALUES ({', '.join('?' for _ in fields)})",
                    [key, *[extra[c] for c in fields[1:]]],
                )
            con.execute(
                """UPDATE pax_segments SET pax_type = ?, fare_family_synthetic = ?, fare = ?, ssr_code = ?,
                       ssr_source = ? WHERE flight_id = ? AND customer_key = ?""",
                [
                    p["pax_type"],
                    p["fare_family"],
                    p["fare"],
                    p.get("ssr") or None,
                    EDIT_SOURCE if p.get("ssr") else None,
                    flight_id,
                    key,
                ],
            )
            con.execute(
                """UPDATE customers SET loyalty_tier_synthetic = ?, is_loyalty_member = ?, loyalty_priority = ?,
                       travel_frequency_band = ? WHERE customer_key = ?""",
                [tier, tier is not None, LOYALTY_PRIORITY.get(tier or ""), p["frequency"], key],
            )
        done += 1
    return done


def merge_passengers(
    flight_id: str, previous: dict[str, Any] | None, sent: list[dict[str, Any]]
) -> list[dict[str, Any]]:
    """A save replaces the flight's edit, but the editor only lists the passengers the analysis sees now. So keep
    what earlier saves did: passengers removed before stay removed, and passengers added before (shown with the key
    apply() gave them) stay added instead of pointing at a real row that does not exist."""
    if not previous:
        return sent
    old = previous.get("passengers", [])
    added = {_new_key(flight_id, p["pnr"], i): p for i, p in enumerate(old) if not p.get("customer_key")}
    out: list[dict[str, Any]] = []
    for p in sent:
        if p.get("customer_key") in added:
            if p.get("remove"):
                continue  # an added passenger taken off again: simply not added
            p = {**p, "customer_key": None}
        out.append(p)
    listed = {p.get("customer_key") for p in sent}
    out += [p for p in old if p.get("customer_key") and p.get("remove") and p["customer_key"] not in listed]
    return out


# --- API -------------------------------------------------------------------------------------------------------
class FlightFields(BaseModel):
    std: str
    sta: str
    tail: Annotated[str, Field(min_length=1, max_length=10, pattern=r"^[A-Za-z0-9-]+$")]
    capacity: Annotated[int, Field(ge=1, le=600)]
    booked_seats: Annotated[int, Field(ge=0, le=600)]

    @field_validator("std", "sta")
    @classmethod
    def _time(cls, v: str) -> str:
        if not _HHMM.match(v):
            raise ValueError("use HH:MM (UTC)")
        return v


class PassengerFields(BaseModel):
    customer_key: str | None = None  # None: a passenger added by the evaluator
    pnr: Annotated[str, Field(min_length=1, max_length=12, pattern=r"^[A-Za-z0-9]+$")]
    pax_type: Literal["AD", "CH", "IN"]
    fare_family: Annotated[str, Field(min_length=1, max_length=20)]
    fare: Annotated[float, Field(ge=0, le=100000)]
    loyalty_tier: Literal["none", "Basic", "Silver", "Gold", "Platinum"]
    frequency: Literal["occasional", "regular", "frequent", "unknown"]
    ssr: Annotated[str | None, Field(default=None, max_length=4, pattern=r"^[A-Za-z]{4}$|^$")] = None
    remove: bool = False


class FlightEditRequest(BaseModel):
    flight: FlightFields
    passengers: Annotated[list[PassengerFields], Field(max_length=MAX_PASSENGERS)]


router = APIRouter(prefix="/api/v1/test-data", tags=["test-data"])


def _store(request: Request) -> Any:
    store = request.app.state.get_store()
    if store is None:
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, "Operating data is not loaded yet (run the ingest)")
    return store


@router.get("/edits")
def list_edits(request: Request, _: EvaluatorUser) -> list[dict[str, Any]]:
    edits = load(request.app.state.settings.test_data_dir)
    return [
        {
            "flight_id": fid,
            "flight_number": fid.split("_")[0],
            "saved_by": e.get("saved_by"),
            "saved_at": e.get("saved_at"),
            "passengers_edited": len(e.get("passengers", [])),
        }
        for fid, e in sorted(edits.items())
    ]


@router.get("/flights/{flight_id}")
def get_flight(
    flight_id: Annotated[str, PathParam(pattern=r"^[A-Za-z0-9]+_\d{12}$")], request: Request, _: EvaluatorUser
) -> dict[str, Any]:
    """The flight and its passengers as the analysis sees them now (with any saved edits)."""
    store = _store(request)
    rows = store.query(
        "SELECT flight_id, flight_number, origin, destination, std, sta, tail, capacity, booked_seats "
        "FROM flights WHERE flight_id = ?",
        [flight_id],
    )
    if not rows:
        raise HTTPException(status.HTTP_404_NOT_FOUND, f"No flight {flight_id}")
    f = rows[0]
    pax = store.query(
        """SELECT p.customer_key, p.pnr, p.passenger_id, p.pax_type, p.fare_family_synthetic AS fare_family, p.fare,
                  p.ssr_code AS ssr, coalesce(c.loyalty_tier_synthetic, 'none') AS loyalty_tier,
                  coalesce(c.travel_frequency_band, 'unknown') AS frequency
           FROM pax_segments p LEFT JOIN customers c USING (customer_key)
           WHERE p.flight_id = ? ORDER BY p.pnr, p.passenger_id""",
        [flight_id],
    )
    edited = flight_id in load(request.app.state.settings.test_data_dir)
    return {
        "flight": {**f, "std_hhmm": f["std"].strftime("%H:%M"), "sta_hhmm": f["sta"].strftime("%H:%M")},
        "passengers": pax,
        "edited": edited,
    }


@router.put("/flights/{flight_id}")
def save_flight(
    flight_id: Annotated[str, PathParam(pattern=r"^[A-Za-z0-9]+_\d{12}$")],
    payload: FlightEditRequest,
    request: Request,
    user: EvaluatorUser,
) -> dict[str, Any]:
    store = _store(request)
    if not store.query("SELECT 1 AS x FROM flights WHERE flight_id = ?", [flight_id]):
        raise HTTPException(status.HTTP_404_NOT_FOUND, f"No flight {flight_id}")
    if payload.flight.booked_seats > payload.flight.capacity:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, "Seats sold cannot be more than the seat capacity")
    directory = request.app.state.settings.test_data_dir
    edits = load(directory)
    edits[flight_id] = {
        "flight": payload.flight.model_dump(),
        "passengers": merge_passengers(flight_id, edits.get(flight_id), [p.model_dump() for p in payload.passengers]),
        "saved_by": f"{user.username} ({user.role})",
        "saved_at": datetime.now(UTC).isoformat(timespec="seconds"),
    }
    write(directory, edits)
    return {"saved": True, "flight_id": flight_id}


@router.delete("/flights/{flight_id}")
def reset_flight(
    flight_id: Annotated[str, PathParam(pattern=r"^[A-Za-z0-9]+_\d{12}$")], request: Request, _: EvaluatorUser
) -> dict[str, Any]:
    directory = request.app.state.settings.test_data_dir
    edits = load(directory)
    removed = edits.pop(flight_id, None) is not None
    write(directory, edits)
    return {"reset": removed, "flight_id": flight_id}
