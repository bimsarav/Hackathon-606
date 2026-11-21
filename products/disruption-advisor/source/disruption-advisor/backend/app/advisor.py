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
from app.engine import rewards
from app.engine import strategy as strategies
from app.engine.priority import DEFAULT_WEIGHTS, LABELS
from app.engine.scenarios import Context, ScenarioError, analyse_cancellation, analyse_delay, presets
from app.models import Decision, Scenario
from app.schemas import (
    ChooseStrategy,
    DecisionCreate,
    DecisionRead,
    LoginRequest,
    LoginResponse,
    MessageDraft,
    MessageRequest,
    Reprioritise,
    RewardRequest,
    ScenarioCreate,
    ScenarioRead,
    ScenarioSummary,
    SelectOption,
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


def _analyse(
    ctx: Context,
    kind: str,
    flight_id: str,
    delay: int | None,
    weights: dict[str, float],
    selected_key: str | None = None,
    strategy: str = strategies.DEFAULT,
) -> dict[str, Any]:
    try:
        if kind == "DELAY":
            if delay is None:
                raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, "delay_minutes is required for a delay")
            result = analyse_delay(ctx, flight_id, delay, weights, selected_key, strategy)
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
        "min_turn_minutes": {"default": s.min_turn_minutes, "by_station": s.min_turn_by_station},
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
    result = _analyse(
        _context(request), payload.kind, payload.flight_id, payload.delay_minutes, weights, strategy=payload.strategy
    )
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
    scenario.result = _analyse(
        _context(request),
        scenario.kind,
        scenario.flight_id,
        scenario.delay_minutes,
        weights,
        scenario.result.get("selected_key"),
        scenario.result.get("strategy", strategies.DEFAULT),
    )
    scenario.weights = weights
    session.commit()
    session.refresh(scenario)
    return _read(scenario)


@router.post("/scenarios/{scenario_id}/select")
def select_option(
    scenario_id: uuid.UUID, payload: SelectOption, request: Request, session: SessionDep, _: CurrentUser
) -> ScenarioRead:
    """Choose a recovery option (delay scenarios). Passengers, costs and the explanation follow the chosen option."""
    scenario = _get(session, scenario_id)
    if scenario.kind != "DELAY":
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, "Only delay scenarios have recovery options")
    if payload.option_key not in {o["key"] for o in scenario.result.get("options", [])}:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Option not found in this scenario")
    scenario.result = _analyse(
        _context(request),
        scenario.kind,
        scenario.flight_id,
        scenario.delay_minutes,
        scenario.weights,
        payload.option_key,
        scenario.result.get("strategy", strategies.DEFAULT),
    )
    session.commit()
    session.refresh(scenario)
    return _read(scenario)


@router.post("/scenarios/{scenario_id}/strategy")
def choose_strategy(
    scenario_id: uuid.UUID, payload: ChooseStrategy, request: Request, session: SessionDep, _: CurrentUser
) -> ScenarioRead:
    """Switch the strategy of a delay scenario (phase 3). The numbers stay the same; the recommendation becomes the
    new strategy's pick, and that option is selected."""
    scenario = _get(session, scenario_id)
    if scenario.kind != "DELAY":
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, "Only delay scenarios have strategies")
    scenario.result = _analyse(
        _context(request),
        scenario.kind,
        scenario.flight_id,
        scenario.delay_minutes,
        scenario.weights,
        None,
        payload.strategy,
    )
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
        "event": "cancelled" if scenario.kind == "CANCEL" else "missed connection",
        "late_inbound_flight": row.get("missed_inbound_flight"),
        "new_flight": row["assigned_flight"],
        "new_departure": row["new_departure"],
        "care_while_waiting": row["care"]["summary"],
        "waiting_hours": round(row["care"]["wait_minutes"] / 60) if row["care"]["wait_minutes"] is not None else None,
        "can_choose_refund_and_free_return_to_origin_or_date_change": row["care"]["refund_option"],
        "travelling_with_infant": row["infants"] > 0,
        "special_assistance": row["ssr"],
    }
    draft = request.app.state.explainer.passenger_message(facts)
    return MessageDraft(text=draft.text, source=draft.source)


@router.post("/scenarios/{scenario_id}/rewards")
def recommend_rewards(
    scenario_id: uuid.UUID, payload: RewardRequest, request: Request, session: SessionDep, _: CurrentUser
) -> dict[str, Any]:
    """Goodwill reward plan for the passengers of the scenario's flight within a budget (phase 5, ADR 0012).

    Computed on request and not stored; a person approves it through the decisions endpoint."""
    scenario = _get(session, scenario_id)
    ctx = _context(request)
    people = rewards.people_for(
        ctx.store.passengers_on([scenario.flight_id]),
        scenario.result,
        scenario.kind,
        scenario.delay_minutes,
        scenario.weights,
        ctx.store.reward_model,
    )
    plan = rewards.recommend(people, payload.budget_aed)
    model = ctx.store.reward_model
    plan["preference_model"] = model.summary() if model else {"kind": "proxy rules", "synthetic_training_data": False}
    plan["disruption"] = rewards.flight_severity(scenario.delay_minutes, scenario.kind == "CANCEL")
    plan["assumptions"] = [
        (
            "Preferences come from a model trained on SIMULATED redemption history (no real history exists): it "
            "reproduces assumed behaviour, not real customer choices."
            if model
            else "Preferences are proxy rules (meal and seat bought, sales channel, fare family, loyalty, frequency, "
            "family booking), not stated preferences: no redemption history exists."
        ),
        "Reward values (AED) and the severity weights are assumed defaults to confirm with the airline.",
        "Statutory care (meals and hotel under the care rules, EU261 where it applies) is not paid from this budget.",
    ]
    return plan
