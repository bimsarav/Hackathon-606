"""Passenger impact: which journeys break when flights are delayed or cancelled.

A connection is the same passenger (customer key) in the same PNR arriving at a station and departing it again
15 min to 20 h later (decision Q8). It is missed when the new connection time is shorter than the MCT for that
origin/hub/destination (hub table, else the configured default), or when either flight is cancelled.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any

from app.engine.network import RotationPlan
from app.engine.store import OpsStore

MIN_PLANNED_CONNECTION = timedelta(minutes=15)


@dataclass(frozen=True)
class Connection:
    pnr: str
    customer_key: str
    inbound_flight_id: str
    outbound_flight_id: str
    outbound_flight_number: str
    hub: str
    final_destination: str
    planned_minutes: int
    new_minutes: int | None  # None when a flight of the connection is cancelled
    mct_minutes: int
    missed: bool


def times_of(plan: RotationPlan, flight_id: str, std: datetime, sta: datetime) -> tuple[datetime, datetime]:
    t = plan.timings.get(flight_id)
    return (t.new_std, t.new_sta) if t else (std, sta)


def connections_at_risk(
    store: OpsStore,
    plan: RotationPlan,
    cancelled: set[str],
    affected_flight_ids: list[str],
    default_mct: int,
    max_connection: timedelta,
) -> list[Connection]:
    """Connections that leave an affected (delayed or cancelled) flight, re-checked with the new times."""
    if not affected_flight_ids:
        return []
    inbound = store.query(
        """SELECT p.pnr, p.customer_key, p.flight_id, p.origin, p.destination, f.std, f.sta
           FROM pax_segments p JOIN flights f USING (flight_id)
           WHERE list_contains(?, p.flight_id) AND p.pax_type <> 'IN'""",
        [affected_flight_ids],
    )
    if not inbound:
        return []
    pnrs = sorted({r["pnr"] for r in inbound})
    earliest = min(r["sta"] for r in inbound)
    onward = store.onward_segments(pnrs, earliest, earliest + max_connection + timedelta(days=1))
    by_pax: dict[tuple[str, str], list[dict[str, Any]]] = {}
    for seg in onward:
        by_pax.setdefault((seg["pnr"], seg["customer_key"]), []).append(seg)

    result: list[Connection] = []
    mct_cache: dict[tuple[str, str, str], int] = {}
    for seg in inbound:
        nxt = next(
            (
                o
                for o in by_pax.get((seg["pnr"], seg["customer_key"]), [])
                if o["origin"] == seg["destination"]
                and MIN_PLANNED_CONNECTION <= o["std"] - seg["sta"] <= max_connection
            ),
            None,
        )
        if nxt is None:
            continue
        key = (seg["origin"], seg["destination"], nxt["destination"])
        if key not in mct_cache:
            mct_cache[key] = store.mct_minutes(*key, default=default_mct)
        mct = mct_cache[key]
        planned = int((nxt["std"] - seg["sta"]).total_seconds() // 60)
        if seg["flight_id"] in cancelled or nxt["flight_id"] in cancelled:
            new_minutes, missed = None, True
        else:
            _, in_sta = times_of(plan, seg["flight_id"], seg["std"], seg["sta"])
            out_std, _ = times_of(plan, nxt["flight_id"], nxt["std"], nxt["sta"])
            new_minutes = int((out_std - in_sta).total_seconds() // 60)
            missed = new_minutes < mct
        result.append(
            Connection(
                seg["pnr"],
                seg["customer_key"],
                seg["flight_id"],
                nxt["flight_id"],
                nxt["flight_number"],
                seg["destination"],
                nxt["destination"],
                planned,
                new_minutes,
                mct,
                missed,
            )
        )
    return result
