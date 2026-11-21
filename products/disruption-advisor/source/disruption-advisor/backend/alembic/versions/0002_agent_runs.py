"""agent runs (phase 3)

Revision ID: 0002
Revises: 0001
Create Date: 2026-11-21
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "agent_runs",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("flight_id", sa.String(length=40), nullable=False),
        sa.Column("delay_minutes", sa.Integer(), nullable=True),
        sa.Column("strategy", sa.String(length=30), nullable=True),
        sa.Column("note", sa.Text(), server_default="", nullable=False),
        sa.Column("status", sa.String(length=10), nullable=False),
        sa.Column("source", sa.String(length=60), nullable=True),
        sa.Column("fallback_reason", sa.Text(), nullable=True),
        sa.Column("trace", postgresql.JSONB(), server_default="[]", nullable=False),
        sa.Column("recommendation", postgresql.JSONB(), nullable=True),
        sa.Column("usage", postgresql.JSONB(), nullable=True),
        sa.Column("error", sa.Text(), nullable=True),
        sa.Column("scenario_id", sa.Uuid(), sa.ForeignKey("scenarios.id", ondelete="SET NULL"), nullable=True),
        sa.Column("created_by", sa.String(length=60), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_agent_runs_created_at", "agent_runs", ["created_at"])
    op.create_index("ix_agent_runs_created_by", "agent_runs", ["created_by"])


def downgrade() -> None:
    op.drop_index("ix_agent_runs_created_by", table_name="agent_runs")
    op.drop_index("ix_agent_runs_created_at", table_name="agent_runs")
    op.drop_table("agent_runs")
