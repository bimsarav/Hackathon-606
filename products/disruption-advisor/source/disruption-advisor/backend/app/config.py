"""Settings from environment variables (see ../.env.example). Never hard-code environment-specific values."""

from functools import lru_cache

from pydantic import Field
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


@lru_cache
def get_settings() -> Settings:
    return Settings()
