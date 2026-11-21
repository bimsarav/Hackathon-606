"""API request/response models (the contract). Analysis results are returned as validated JSON documents."""

import uuid
from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

from app.engine.priority import ATTRIBUTES, DEFAULT_WEIGHTS


class Strict(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class LoginRequest(Strict):
    username: str = Field(min_length=1, max_length=60)
    password: str = Field(min_length=1, max_length=200)


class LoginResponse(BaseModel):
    token: str
    username: str
    role: str
    expires_at: datetime


class Weights(Strict):
    loyalty: float = Field(default=DEFAULT_WEIGHTS["loyalty"], ge=0, le=100)
    frequency: float = Field(default=DEFAULT_WEIGHTS["frequency"], ge=0, le=100)
    fare_value: float = Field(default=DEFAULT_WEIGHTS["fare_value"], ge=0, le=100)
    ancillaries: float = Field(default=DEFAULT_WEIGHTS["ancillaries"], ge=0, le=100)
    journey: float = Field(default=DEFAULT_WEIGHTS["journey"], ge=0, le=100)
    booking: float = Field(default=DEFAULT_WEIGHTS["booking"], ge=0, le=100)

    def as_dict(self) -> dict[str, float]:
        return {a: float(getattr(self, a)) for a in ATTRIBUTES}


class ScenarioCreate(Strict):
    kind: Literal["DELAY", "CANCEL"]
    flight_id: str = Field(min_length=6, max_length=40, pattern=r"^[A-Z0-9]{2,8}_\d{12}$")
    delay_minutes: int | None = Field(default=None, ge=15, le=1440)
    weights: Weights = Field(default_factory=Weights)


class Reprioritise(Strict):
    weights: Weights


class SelectOption(Strict):
    option_key: str = Field(min_length=1, max_length=40, pattern=r"^[A-Za-z0-9:_\-]+$")


class ScenarioRead(BaseModel):
    id: uuid.UUID
    kind: str
    flight_id: str
    delay_minutes: int | None
    weights: dict[str, float]
    result: dict[str, Any]
    created_by: str
    created_at: datetime


class ScenarioSummary(BaseModel):
    id: uuid.UUID
    kind: str
    flight_id: str
    delay_minutes: int | None
    created_by: str
    created_at: datetime


class DecisionCreate(Strict):
    target: str = Field(min_length=1, max_length=120, pattern=r"^[A-Za-z0-9:_\-]+$")
    action: Literal["APPROVE", "REJECT"]
    comment: str = Field(default="", max_length=1000)


class DecisionRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    target: str
    action: str
    comment: str
    decided_by: str
    decided_at: datetime


class MessageRequest(Strict):
    customer_key: str = Field(min_length=8, max_length=32, pattern=r"^[0-9a-f]+$")


class MessageDraft(BaseModel):
    text: str
    source: str


class RewardRequest(Strict):
    budget_aed: float = Field(ge=0, le=1_000_000)
