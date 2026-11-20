"""Disruption Advisor API under /api/v1: login, reference data, scenarios, what-if, decisions, message drafts.

Every route except login requires a signed-in demo user (app.auth). The engine only recommends; decisions are
recorded with who and when (human in the loop, Q21).
"""

import uuid
from datetime import UTC, datetime
from typing import Annotated, Any

from fastapi import APIRouter, HTTPException, Query, Request, status
from fastapi.encoders import jsonable_encoder
from sqlalchemy import select

from app.auth import CurrentUser, authenticate, issue_token
from app.db import SessionDep
from app.engine.priority import DEFAULT_WEIGHTS, LABELS
from app.engine.scenarios import Context, ScenarioError, analyse_cancellation, analyse_delay, presets
from app.models import Decision, Scenario
from app.schemas import (
    DecisionCreate,
    DecisionRead,
    LoginRequest,
    LoginResponse,
    MessageDraft,
    MessageRequest,
    Reprioritise,
    ScenarioCreate,
    ScenarioRead,
    ScenarioSummary,
)

router = APIRouter(prefix="/api/v1", tags=["advisor"])


def _context(request: Request) -> Context:
    store = request.app.state.get_store()
    if store is None:
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, "Operating data is not loaded yet (run the ingest)")
    return Context(store, request.app.state.settings, request.app.state.explainer)


def _read(s: Scenario) -> ScenarioRead:
    return ScenarioRead(
        id=s.id,
        kind=s.kind,
        flight_id=s.flight_id,
        delay_minutes=s.delay_minutes,
        weights=s.weights,
        result=s.result,
        created_by=s.created_by,
        created_at=s.created_at,
    )


def _analyse(ctx: Context, kind: str, flight_id: str, delay: int | None, weights: dict[str, float]) -> dict[str, Any]:
    try:
        if kind == "DELAY":
            if delay is None:
                raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, "delay_minutes is required for a delay")
            result = analyse_delay(ctx, flight_id, delay, weights)
        else:
            result = analyse_cancellation(ctx, flight_id, weights)
    except ScenarioError as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, str(exc)) from exc
    return dict(jsonable_encoder(result))


@router.post("/auth/login")
def login(payload: LoginRequest, request: Request) -> LoginResponse:
    settings = request.app.state.settings
    user = authenticate(settings, payload.username, payload.password)
    if user is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Wrong user name or password")
    token, expires = issue_token(settings, user)
    return LoginResponse(
        token=token, username=user.username, role=user.role, expires_at=datetime.fromtimestamp(expires, UTC)
    )


@router.get("/meta")
def meta(request: Request, user: CurrentUser) -> dict[str, Any]:
    ctx = _context(request)
    s = ctx.settings
    return {
        "user": {"username": user.username, "role": user.role},
        "now_utc": s.now_utc,
        "horizon_days": s.horizon_days,
        "ai_enabled": ctx.explainer.enabled,
        "ai_model": s.ai_model,
        "default_weights": DEFAULT_WEIGHTS,
        "weight_labels": LABELS,
        "ingest": ctx.store.report,
    }


@router.get("/presets")
def get_presets(request: Request, _: CurrentUser) -> dict[str, Any]:
    return dict(jsonable_encoder(presets(_context(request))))


@router.get("/flights")
def search_flights(
    request: Request,
    _: CurrentUser,
    q: Annotated[str, Query(max_length=10, pattern=r"^[A-Za-z0-9-]*$")] = "",
    day: Annotated[str | None, Query(pattern=r"^\d{4}-\d{2}-\d{2}$")] = None,
    limit: Annotated[int, Query(ge=1, le=100)] = 30,
) -> list[dict[str, Any]]:
    return list(jsonable_encoder(_context(request).store.search_flights(q, day, limit)))


@router.post("/scenarios", status_code=status.HTTP_201_CREATED)
def create_scenario(payload: ScenarioCreate, request: Request, session: SessionDep, user: CurrentUser) -> ScenarioRead:
    weights = payload.weights.as_dict()
    result = _analyse(_context(request), payload.kind, payload.flight_id, payload.delay_minutes, weights)
    scenario = Scenario(
        id=uuid.uuid4(),
        kind=payload.kind,
        flight_id=payload.flight_id,
        delay_minutes=payload.delay_minutes,
        weights=weights,
        result=result,
        created_by=user.username,
    )
    session.add(scenario)
    session.commit()
    session.refresh(scenario)
    return _read(scenario)


@router.get("/scenarios")
def list_scenarios(
    session: SessionDep, _: CurrentUser, limit: Annotated[int, Query(ge=1, le=50)] = 20
) -> list[ScenarioSummary]:
    rows = session.scalars(select(Scenario).order_by(Scenario.created_at.desc()).limit(limit))
    return [
        ScenarioSummary(
            id=s.id,
            kind=s.kind,
            flight_id=s.flight_id,
            delay_minutes=s.delay_minutes,
            created_by=s.created_by,
            created_at=s.created_at,
        )
        for s in rows
    ]


def _get(session: SessionDep, scenario_id: uuid.UUID) -> Scenario:
    scenario = session.get(Scenario, scenario_id)
    if scenario is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Scenario not found")
    return scenario


@router.get("/scenarios/{scenario_id}")
def get_scenario(scenario_id: uuid.UUID, session: SessionDep, _: CurrentUser) -> ScenarioRead:
    return _read(_get(session, scenario_id))


@router.post("/scenarios/{scenario_id}/reprioritise")
def reprioritise(
    scenario_id: uuid.UUID, payload: Reprioritise, request: Request, session: SessionDep, _: CurrentUser
) -> ScenarioRead:
    """What-if: re-run the analysis with new weights (the flight and delay stay the same)."""
    scenario = _get(session, scenario_id)
    weights = payload.weights.as_dict()
    scenario.result = _analyse(_context(request), scenario.kind, scenario.flight_id, scenario.delay_minutes, weights)
    scenario.weights = weights
    session.commit()
    session.refresh(scenario)
    return _read(scenario)


@router.get("/scenarios/{scenario_id}/decisions")
def list_decisions(scenario_id: uuid.UUID, session: SessionDep, _: CurrentUser) -> list[DecisionRead]:
    _get(session, scenario_id)
    rows = session.scalars(select(Decision).where(Decision.scenario_id == scenario_id).order_by(Decision.id))
    return [DecisionRead.model_validate(d) for d in rows]


@router.post("/scenarios/{scenario_id}/decisions", status_code=status.HTTP_201_CREATED)
def decide(scenario_id: uuid.UUID, payload: DecisionCreate, session: SessionDep, user: CurrentUser) -> DecisionRead:
    _get(session, scenario_id)
    decision = Decision(
        scenario_id=scenario_id,
        target=payload.target,
        action=payload.action,
        comment=payload.comment,
        decided_by=f"{user.username} ({user.role})",
    )
    session.add(decision)
    session.commit()
    session.refresh(decision)
    return DecisionRead.model_validate(decision)


@router.post("/scenarios/{scenario_id}/messages")
def draft_message(
    scenario_id: uuid.UUID, payload: MessageRequest, request: Request, session: SessionDep, _: CurrentUser
) -> MessageDraft:
    """Personalised message draft. Only non-identifying facts are sent to the language model."""
    scenario = _get(session, scenario_id)
    row = next((p for p in scenario.result.get("passengers", []) if p["customer_key"] == payload.customer_key), None)
    if row is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Passenger is not part of this scenario")
    origin, destination = row["route"].split("-", 1)
    facts = {
        "flight": row["flight_id"].split("_")[0],
        "origin": origin,
        "destination": destination,
        "event": "cancelled" if scenario.kind == "CANCEL" else "delayed, so the onward connection is missed",
        "new_flight": row["assigned_flight"],
        "new_departure": row["new_departure"],
        "care": "meal vouchers" if row["assigned_flight"] else "hotel and meals until the next available flight",
        "travelling_with_infant": row["infants"] > 0,
        "special_assistance": row["ssr"],
    }
    draft = request.app.state.explainer.passenger_message(facts)
    return MessageDraft(text=draft.text, source=draft.source)
