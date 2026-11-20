"""scenarios and decisions

Revision ID: 0001
Revises:
Create Date: 2026-11-20
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "scenarios",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("kind", sa.String(length=10), nullable=False),
        sa.Column("flight_id", sa.String(length=40), nullable=False),
        sa.Column("delay_minutes", sa.Integer(), nullable=True),
        sa.Column("weights", postgresql.JSONB(), nullable=False),
        sa.Column("result", postgresql.JSONB(), nullable=False),
        sa.Column("created_by", sa.String(length=60), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_scenarios_created_at", "scenarios", ["created_at"])
    op.create_table(
        "decisions",
        sa.Column("id", sa.BigInteger(), sa.Identity(), primary_key=True),
        sa.Column("scenario_id", sa.Uuid(), sa.ForeignKey("scenarios.id", ondelete="CASCADE"), nullable=False),
        sa.Column("target", sa.String(length=120), nullable=False),
        sa.Column("action", sa.String(length=10), nullable=False),
        sa.Column("comment", sa.Text(), server_default="", nullable=False),
        sa.Column("decided_by", sa.String(length=60), nullable=False),
        sa.Column("decided_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_decisions_scenario", "decisions", ["scenario_id"])


def downgrade() -> None:
    op.drop_index("ix_decisions_scenario", table_name="decisions")
    op.drop_table("decisions")
    op.drop_index("ix_scenarios_created_at", table_name="scenarios")
    op.drop_table("scenarios")
