"""Phase 2 API: delay risk, the 7-day watchlist and missed-connection risk per passenger (ADR 0008).

Read-only. The numbers come from ingest stage 3 (app/ml/delay_risk.py); predictions only rank and pre-fill, a
person still runs a scenario and approves any action.
"""

import json
from datetime import timedelta
from typing import Annotated, Any, Literal

import numpy as np
from fastapi import APIRouter, HTTPException, Path, Query, Request, status
from fastapi.encoders import jsonable_encoder
from pydantic import BaseModel, Field

from app.auth import CurrentUser, EvaluatorUser
from app.engine.store import OpsStore
from app.ml import delay_risk, live_delay

router = APIRouter(prefix="/api/v1/risk", tags=["risk"])

FLIGHT_COLUMNS = """f.flight_id, f.flight_number, f.origin, f.destination, f.std, f.sta, f.tail, f.aircraft_model,
    r.p_15, r.p_30, r.p_60, r.p_120, r.a_15, r.a_60, r.planning_delay_minutes, r.risk_band, r.reasons, r.connecting_pax,
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


class PredictRequest(BaseModel):
    """What is known on the day. Every field is optional; give none to get the planning (7-day) prediction."""

    inbound_arrival_delay: Annotated[int | None, Field(ge=-120, le=1440, description="minutes late, previous leg")] = (
        None
    )
    inbound_departure_delay: Annotated[int | None, Field(ge=-120, le=1440)] = None
    departure_delay: Annotated[int | None, Field(ge=-120, le=1440, description="this flight, actual or what-if")] = None


@router.post("/flights/{flight_id}/predict")
def predict(
    flight_id: Annotated[str, Path(max_length=40, pattern=r"^[A-Za-z0-9]+_\d{12}$")],
    body: PredictRequest,
    request: Request,
    _: CurrentUser,
) -> dict[str, Any]:
    """Departure AND arrival delay curves of one flight, from the planning model or from live inputs."""
    store = _store(request)
    rows = store.query(
        """SELECT r.p_5, r.p_15, r.p_30, r.p_60, r.p_120, r.p_180, r.a_5, r.a_15, r.a_30, r.a_60, r.a_120, r.a_180,
                  f.flight_number, f.origin, f.destination
           FROM flights f JOIN flight_risk r USING (flight_id) WHERE f.flight_id = ?""",
        [flight_id],
    )
    if not rows:
        raise HTTPException(status.HTTP_404_NOT_FOUND, f"No delay risk for flight {flight_id}")
    r = rows[0]
    planning_dep = np.array([r[f"p_{t}"] for t in delay_risk.THRESHOLDS], dtype=float)
    planning_arr = np.array([r[f"a_{t}"] for t in delay_risk.THRESHOLDS], dtype=float)
    ia, idd, dd = body.inbound_arrival_delay, body.inbound_departure_delay, body.departure_delay
    inbound_given = ia is not None or idd is not None
    if (inbound_given or dd is not None) and store.live_models is None:
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, "Live models are not available yet (run the ingest)")

    def nan(v: int | None) -> float:
        return float("nan") if v is None else float(v)

    departure = {"mode": "planning", **live_delay.summarise(planning_dep)}
    arrival = {"mode": "planning", **live_delay.summarise(planning_arr)}
    if store.live_models is not None and (inbound_given or dd is not None):
        if flight_id not in store.window_ids:  # e.g. an uploaded test flight: scored by the planning model only
            raise HTTPException(
                status.HTTP_409_CONFLICT,
                "Live inputs are not available for this flight; it has the planning forecast only",
            )
        base = store.window_x[store.window_ids.index(flight_id)][None, :]
        live = {
            "inbound_arr_delay": np.array([nan(ia)]),
            "inbound_dep_delay": np.array([nan(idd)]),
            "dep_delay": np.array([nan(dd)]),
        }
        if inbound_given:
            x = live_delay.matrix("dep", base, live)
            departure = {
                "mode": "live: inbound aircraft delay",
                **live_delay.summarise(store.live_models.predict("dep", x)[0]),
            }
        kind = "arr_dep" if dd is not None else "arr_in"
        mode = "live: departure delay" if dd is not None else "live: inbound aircraft delay"
        x = live_delay.matrix(kind, base, live)
        arrival = {"mode": mode, **live_delay.summarise(store.live_models.predict(kind, x)[0])}
    return dict(
        jsonable_encoder(
            {
                "flight_id": flight_id,
                "flight_number": r["flight_number"],
                "origin": r["origin"],
                "destination": r["destination"],
                "inputs": body.model_dump(),
                "departure": departure,
                "arrival": arrival,
                "accuracy": (store.model_card.get("live_models") or {}),
            }
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
