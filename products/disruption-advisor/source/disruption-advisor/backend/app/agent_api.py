"""Phase 3 agent API (ADR 0010): start a run, follow its trace, open the scenario it produced.

A run executes after the response (FastAPI background task, in the thread pool). Each step is committed as it
happens, so the UI can show it live by polling. The result is saved as a normal delay scenario with the agent's
reasons attached; a person approves or overrides it through the existing decision flow.
"""

from __future__ import annotations

import logging
import uuid
from datetime import UTC, datetime, timedelta
from typing import Annotated, Any

from fastapi import APIRouter, BackgroundTasks, HTTPException, Query, Request, status
from fastapi.encoders import jsonable_encoder
from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker

from app.agent.runner import Limits, Step, run_agent
from app.agent.tools import AgentTools
from app.auth import CurrentUser
from app.db import SessionDep
from app.engine import priority
from app.engine.explain import Explainer
from app.engine.scenarios import Context, analyse_delay
from app.models import AgentRun, Scenario
from app.schemas import AgentRunCreate, AgentRunRead

log = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1/agent", tags=["agent"])


def _read(run: AgentRun, timeout_s: float) -> AgentRunRead:
    out = AgentRunRead.model_validate(run, from_attributes=True)
    if run.status == "RUNNING" and datetime.now(UTC) - run.created_at > timedelta(seconds=timeout_s + 120):
        out.status, out.error = "FAILED", "The run was interrupted (for example by a restart). Start it again."
    return out


def _context(request: Request) -> tuple[Context, Context]:
    """(context for the tools: template texts only, so tools make no AI calls; context for the final scenario)."""
    store = request.app.state.get_store()
    if store is None:
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, "Operating data is not loaded yet (run the ingest)")
    settings = request.app.state.settings
    quiet = Explainer("", settings.ai_model, settings.ai_effort, 1)
    return Context(store, settings, quiet), Context(store, settings, request.app.state.explainer)


@router.post("/runs", status_code=status.HTTP_202_ACCEPTED)
def start_run(
    payload: AgentRunCreate, request: Request, session: SessionDep, user: CurrentUser, background: BackgroundTasks
) -> AgentRunRead:
    settings = request.app.state.settings
    tools_ctx, scenario_ctx = _context(request)
    if tools_ctx.store.leg(payload.flight_id) is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, f"Flight {payload.flight_id} is not in the operating window")
    recent = datetime.now(UTC) - timedelta(seconds=settings.agent_timeout_seconds + 120)
    busy = session.scalar(
        select(AgentRun.id).where(
            AgentRun.created_by == user.username, AgentRun.status == "RUNNING", AgentRun.created_at > recent
        )
    )
    if busy is not None:
        raise HTTPException(status.HTTP_409_CONFLICT, "You already have an agent run in progress; wait for it to end")
    run = AgentRun(
        id=uuid.uuid4(),
        flight_id=payload.flight_id,
        delay_minutes=payload.delay_minutes,
        strategy=payload.strategy,
        note=payload.note,
        status="RUNNING",
        trace=[],
        created_by=user.username,
    )
    session.add(run)
    session.commit()
    session.refresh(run)
    background.add_task(
        execute,
        request.app.state.sessionmaker,
        request.app.state.agent_client,
        tools_ctx,
        scenario_ctx,
        run.id,
        Limits(
            settings.agent_max_tool_calls,
            settings.agent_timeout_seconds,
            settings.agent_effort,
            settings.ai_model,
        ),
    )
    return _read(run, settings.agent_timeout_seconds)


def execute(
    factory: sessionmaker[Session],
    client: Any,
    tools_ctx: Context,
    scenario_ctx: Context,
    run_id: uuid.UUID,
    limits: Limits,
) -> None:
    with factory() as session:
        found = session.get(AgentRun, run_id)
        if found is None:
            return
        run: AgentRun = found

        def on_step(step: Step) -> None:
            run.trace = [*run.trace, dict(jsonable_encoder(vars(step)))]
            session.commit()

        try:
            outcome = run_agent(
                client,
                AgentTools(tools_ctx),
                run.flight_id,
                run.delay_minutes,
                run.strategy,
                run.note,
                limits,
                on_step,
            )
            final = outcome.final
            result = analyse_delay(
                scenario_ctx,
                final["flight_id"],
                final["delay_minutes"],
                priority.DEFAULT_WEIGHTS,
                final["option_key"],
                final["strategy"],
            )
            result["agent"] = {
                "run_id": str(run.id),
                "source": outcome.source,
                "option_key": final["option_key"],
                "strategy": final["strategy"],
                "reasons": final["reasons"],
                "risks": final["risks"],
                "checks": final["checks"],
            }
            scenario = Scenario(
                id=uuid.uuid4(),
                kind="DELAY",
                flight_id=final["flight_id"],
                delay_minutes=final["delay_minutes"],
                weights=dict(priority.DEFAULT_WEIGHTS),
                result=dict(jsonable_encoder(result)),
                created_by=run.created_by,
            )
            session.add(scenario)
            session.flush()
            run.status, run.source, run.fallback_reason = "DONE", outcome.source, outcome.fallback_reason
            run.recommendation = dict(jsonable_encoder(final))
            run.usage = outcome.usage or None
            run.scenario_id = scenario.id
        except Exception as exc:
            log.exception("agent run failed")
            session.rollback()
            again = session.get(AgentRun, run_id)
            if again is None:
                return
            run = again
            run.status, run.error = "FAILED", f"The run could not finish: {type(exc).__name__}"
        run.finished_at = datetime.now(UTC)
        session.commit()


@router.get("/runs/{run_id}")
def get_run(run_id: uuid.UUID, request: Request, session: SessionDep, _: CurrentUser) -> AgentRunRead:
    run = session.get(AgentRun, run_id)
    if run is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Agent run not found")
    return _read(run, request.app.state.settings.agent_timeout_seconds)


@router.get("/runs")
def list_runs(
    request: Request, session: SessionDep, _: CurrentUser, limit: Annotated[int, Query(ge=1, le=50)] = 20
) -> list[dict[str, Any]]:
    runs = session.scalars(select(AgentRun).order_by(AgentRun.created_at.desc()).limit(limit)).all()
    timeout = request.app.state.settings.agent_timeout_seconds
    return [
        {k: v for k, v in jsonable_encoder(_read(r, timeout)).items() if k not in ("trace", "note", "fallback_reason")}
        for r in runs
    ]
