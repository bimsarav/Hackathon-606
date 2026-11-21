"""ORM models. Every schema change also needs an Alembic migration (alembic/versions/); tests fail otherwise.

PostgreSQL holds what users create: scenarios (with the analysis result as JSON), their decisions (audit) and,
from phase 3, agent runs (the agent's trace and recommendation, linked to the scenario it produced).
The airline extracts themselves live in Parquet (app.ingest) and are never written here.
"""

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import BigInteger, DateTime, ForeignKey, Identity, Index, Integer, String, Text, Uuid, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


class Scenario(Base):
    __tablename__ = "scenarios"
    __table_args__ = (Index("ix_scenarios_created_at", "created_at"),)

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    kind: Mapped[str] = mapped_column(String(10))  # DELAY | CANCEL
    flight_id: Mapped[str] = mapped_column(String(40))
    delay_minutes: Mapped[int | None] = mapped_column(Integer)
    weights: Mapped[dict[str, Any]] = mapped_column(JSONB)
    result: Mapped[dict[str, Any]] = mapped_column(JSONB)
    created_by: Mapped[str] = mapped_column(String(60))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class Decision(Base):
    __tablename__ = "decisions"
    __table_args__ = (Index("ix_decisions_scenario", "scenario_id"),)

    id: Mapped[int] = mapped_column(BigInteger, Identity(), primary_key=True)
    scenario_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("scenarios.id", ondelete="CASCADE"))
    target: Mapped[str] = mapped_column(String(120))  # e.g. option:swap:A6-ARI | rebooking | message:<key>
    action: Mapped[str] = mapped_column(String(10))  # APPROVE | REJECT
    comment: Mapped[str] = mapped_column(Text, server_default="")
    decided_by: Mapped[str] = mapped_column(String(60))
    decided_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class AgentRun(Base):
    __tablename__ = "agent_runs"
    __table_args__ = (Index("ix_agent_runs_created_at", "created_at"), Index("ix_agent_runs_created_by", "created_by"))

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    flight_id: Mapped[str] = mapped_column(String(40))
    delay_minutes: Mapped[int | None] = mapped_column(Integer)
    strategy: Mapped[str | None] = mapped_column(String(30))
    note: Mapped[str] = mapped_column(Text, server_default="")
    status: Mapped[str] = mapped_column(String(10))  # RUNNING | DONE | FAILED
    source: Mapped[str | None] = mapped_column(String(60))  # ai:<model> | planner
    fallback_reason: Mapped[str | None] = mapped_column(Text)
    trace: Mapped[list[dict[str, Any]]] = mapped_column(JSONB, server_default="[]")
    recommendation: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    usage: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    error: Mapped[str | None] = mapped_column(Text)
    scenario_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, ForeignKey("scenarios.id", ondelete="SET NULL"))
    created_by: Mapped[str] = mapped_column(String(60))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
