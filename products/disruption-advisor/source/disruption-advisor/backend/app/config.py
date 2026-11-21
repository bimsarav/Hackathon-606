"""Settings from environment variables (see ../.env.example). Never hard-code environment-specific values."""

from datetime import datetime
from functools import lru_cache
from pathlib import Path

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(extra="ignore")

    app_name: str = "Disruption Advisor"
    # postgresql+psycopg://user:password@host:5432/database
    database_url: str = Field(min_length=1)
    db_pool_size: int = 5
    log_level: str = "INFO"
    log_json: bool = True
    workers: int = 2

    # Operating data (Parquet built by `python -m app.ingest`); the API only reads <data_dir>/ops.
    data_dir: Path = Path("/data")
    # Demo "now" (decision Q2): the extracts are a snapshot, so the clock is simulated.
    now_utc: datetime = datetime(2026, 11, 20, 0, 0)
    horizon_days: int = 7

    # Operational rule defaults (configurable; assumptions are labelled in the UI).
    # Minimum ground time between two legs of one aircraft: fastest 5% of G9 actual turns, Jan-Nov 2026.
    min_turn_minutes: int = 36  # outstations (default)
    min_turn_by_station: dict[str, int] = {"SHJ": 51}  # hub needs longer
    default_mct_minutes: int = 50  # where the hub MCT table has no entry (lowest real SHJ rule)
    max_connection_minutes: int = 1200  # 20 h (decision Q8)
    rebooking_window_hours: int = 24  # alternatives considered within 24 h (Q14)

    # Cost model (Q15): assumed defaults, AED.
    cost_delay_per_minute: float = 400.0
    cost_hotel_per_night: float = 350.0
    cost_meal_voucher: float = 50.0
    cost_rebooking_handling: float = 25.0
    # Goodwill cost of a missed connection (user 2026-11-21): base AED x passenger value, so stranding a frequent or
    # high-tier loyal traveller costs more. Value = 1 + 2 x loyalty tier value (Basic .25 .. Platinum 1) + frequency
    # bonus (frequent 1, regular .5). Assumed, configurable.
    cost_misconnect_goodwill: float = 150.0
    # Holding a connecting flight for late inbound passengers (user 2026-11-21): longest hold considered.
    hold_max_minutes: int = 60
    eur_to_aed: float = 4.0
    cost_transport: float = 60.0  # one way, airport <-> hotel

    # Passenger care while waiting (app/engine/care.py; airline policy outside EU261).
    care_meal_after_minutes: int = 120
    care_meal_every_minutes: int = 240
    care_hotel_after_minutes: int = 480
    care_refund_offer_after_minutes: int = 300

    # Demo logins (Q19): "user:password:role" entries, comma separated; set only in the server .env.
    demo_users: SecretStr = SecretStr("")
    token_secret: SecretStr = SecretStr("")
    token_ttl_hours: int = 12

    # Generative AI (Q26): explanations and message drafts; templates are used when no key is set.
    anthropic_api_key: SecretStr = SecretStr("")
    ai_model: str = "claude-opus-5-5"
    ai_effort: str = "low"  # short texts; thinking cannot be disabled on Opus 5.5, effort controls depth
    ai_timeout_seconds: float = 25.0
    # Phase 3 agent (ADR 0010): recommend-only tool-use loop; the planner answers when the AI cannot
    agent_effort: str = "medium"
    agent_max_tool_calls: int = 12
    agent_timeout_seconds: float = 120.0


@lru_cache
def get_settings() -> Settings:
    return Settings()
