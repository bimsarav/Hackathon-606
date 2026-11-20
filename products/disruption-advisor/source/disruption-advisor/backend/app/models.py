"""ORM models. Every schema change also needs an Alembic migration (alembic/versions/); tests fail otherwise."""

from datetime import datetime

from sqlalchemy import BigInteger, DateTime, Identity, Index, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


class Note(Base):
    """Example aggregate. Replace with the product's own domain models."""

    __tablename__ = "notes"
    __table_args__ = (Index("ix_notes_created_at", "created_at"),)

    id: Mapped[int] = mapped_column(BigInteger, Identity(), primary_key=True)
    title: Mapped[str] = mapped_column(String(200))
    body: Mapped[str] = mapped_column(Text, server_default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
