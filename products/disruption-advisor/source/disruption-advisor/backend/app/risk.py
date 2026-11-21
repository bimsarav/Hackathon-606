"""Phase 2 API: delay risk, the 7-day watchlist and missed-connection risk per passenger (ADR 0008).

Read-only. The numbers come from ingest stage 3 (app/ml/delay_risk.py); predictions only rank and pre-fill, a
person still runs a scenario and approves any action.
"""

import json
from datetime import timedelta
from typing import Annotated, Any, Literal

from fastapi import APIRouter, HTTPException, Path, Query, Request, status
from fastapi.encoders import jsonable_encoder

from app.auth import CurrentUser, EvaluatorUser
from app.engine.store import OpsStore

router = APIRouter(prefix="/api/v1/risk", tags=["risk"])

FLIGHT_COLUMNS = """f.flight_id, f.flight_number, f.origin, f.destination, f.std, f.sta, f.tail, f.aircraft_model,
    r.p_15, r.p_30, r.p_60, r.p_120, r.planning_delay_minutes, r.risk_band, r.reasons, r.connecting_pax,
    r.expected_misconnects"""
ORDER = {
    "misconnects": "r.expected_misconnects DESC, r.p_60 DESC",
    "delay": "r.p_60 DESC, r.expected_misconnects DESC",
}


def _store(request: Request) -> OpsStore:
    store: OpsStore | None = request.app.state.get_store()
    if store is None:
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, "Operating data is not loaded yet (run the ingest)")
    if not store.has_risk:
        raise HTTPException(
            status.HTTP_503_SERVICE_UNAVAILABLE, "Delay-risk data is not available yet (run the ingest, stage 3)"
        )
    return store


def _row(r: dict[str, Any]) -> dict[str, Any]:
    return {**r, "reasons": json.loads(r["reasons"]) if r.get("reasons") else []}


@router.get("/model")
def model_card(request: Request, _: EvaluatorUser) -> dict[str, Any]:
    """How the delay-risk model was trained and how well it did on the most recent weeks it did not see."""
    return _store(request).model_card


@router.get("/last-week")
def last_week(request: Request, _: CurrentUser) -> dict[str, Any]:
    """The last 7 days of flights predicted by a model that had not seen them, next to what really happened."""
    check = _store(request).last_week
    if not check:
        raise HTTPException(
            status.HTTP_503_SERVICE_UNAVAILABLE, "The last-week check is not available yet (run the ingest)"
        )
    return check


@router.get("/cascade")
def cascade(request: Request, _: CurrentUser) -> dict[str, Any]:
    """The cascade formula against what really happened over the last month of punctuality data."""
    check = _store(request).cascade_check
    if not check:
        raise HTTPException(
            status.HTTP_503_SERVICE_UNAVAILABLE, "The cascade check is not available yet (run the ingest)"
        )
    return check


@router.get("/watchlist")
def watchlist(
    request: Request,
    _: CurrentUser,
    days: Annotated[int, Query(ge=1, le=7)] = 7,
    band: Annotated[Literal["all", "medium", "high"], Query()] = "medium",
    sort: Annotated[Literal["misconnects", "delay"], Query()] = "misconnects",
    limit: Annotated[int, Query(ge=1, le=200)] = 50,
) -> dict[str, Any]:
    """Flights in the next `days` days ranked by expected missed connections (or by delay risk)."""
    store = _store(request)
    now = request.app.state.settings.now_utc
    bands = {"all": ["low", "medium", "high"], "medium": ["medium", "high"], "high": ["high"]}[band]
    where = "f.std >= ? AND f.std < ? AND list_contains(?, r.risk_band)"
    params: list[Any] = [now, now + timedelta(days=days), bands]
    rows = store.query(
        f"""SELECT {FLIGHT_COLUMNS} FROM flights f JOIN flight_risk r USING (flight_id)
            WHERE {where} ORDER BY {ORDER[sort]}, f.std LIMIT ?""",
        [*params, limit],
    )
    totals = store.query(
        f"""SELECT count(*) AS flights, count(*) FILTER (WHERE r.risk_band = 'high') AS high,
                   count(*) FILTER (WHERE r.risk_band = 'medium') AS medium,
                   round(sum(r.expected_misconnects), 1) AS expected_misconnects
            FROM flights f JOIN flight_risk r USING (flight_id) WHERE {where}""",
        params,
    )[0]
    return dict(
        jsonable_encoder(
            {"from_utc": now, "days": days, "band": band, "totals": totals, "flights": [_row(r) for r in rows]}
        )
    )


@router.get("/flights/{flight_id}")
def flight_risk(
    flight_id: Annotated[str, Path(max_length=40, pattern=r"^[A-Za-z0-9]+_\d{12}$")],
    request: Request,
    _: CurrentUser,
    limit: Annotated[int, Query(ge=1, le=500)] = 100,
) -> dict[str, Any]:
    """One flight's delay curve and reasons, with its connecting passengers ranked by missed-connection risk."""
    store = _store(request)
    rows = store.query(
        f"""SELECT {FLIGHT_COLUMNS}, r.p_5, r.p_180
            FROM flights f JOIN flight_risk r USING (flight_id) WHERE f.flight_id = ?""",
        [flight_id],
    )
    if not rows:
        raise HTTPException(status.HTTP_404_NOT_FOUND, f"No delay risk for flight {flight_id}")
    connections = store.query(
        """SELECT pnr, passenger_id, outbound_flight_id, outbound_flight_number, hub, final_destination,
                  connection_minutes, mct_minutes, default_mct, slack_minutes, misconnect_risk
           FROM connection_risk WHERE inbound_flight_id = ? ORDER BY misconnect_risk DESC, pnr LIMIT ?""",
        [flight_id, limit],
    )
    return dict(jsonable_encoder({"flight": _row(rows[0]), "connections": connections}))
