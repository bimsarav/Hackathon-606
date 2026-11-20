"""Application factory. Run with:  python -m app.serve   (or uvicorn app.main:create_app --factory)."""

import threading
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

import structlog
from fastapi import FastAPI
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app import advisor, health, risk
from app.config import Settings, get_settings
from app.engine.explain import Explainer
from app.engine.store import OpsStore
from app.errors import register_error_handlers
from app.logging import configure_logging
from app.middleware import RequestIdMiddleware

log = structlog.get_logger(__name__)


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or get_settings()
    configure_logging(settings.log_level, settings.log_json)
    engine = create_engine(settings.database_url, pool_pre_ping=True, pool_size=settings.db_pool_size)
    lock = threading.Lock()
    loaded: dict[str, OpsStore] = {}

    def get_store() -> OpsStore | None:
        """Load the operating data on first use; None until the ingest has produced it."""
        with lock:
            if "store" not in loaded:
                ops = settings.data_dir / "ops"
                if not (ops / "flights.parquet").exists():
                    return None
                loaded["store"] = OpsStore(ops)
                log.info("ops_data_loaded", path=str(ops))
            return loaded["store"]

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        get_store()
        yield
        engine.dispose()

    app = FastAPI(
        title=f"{settings.app_name} API",
        version="1.0.0",
        lifespan=lifespan,
        docs_url="/api/docs",
        openapi_url="/api/openapi.json",
        redoc_url=None,
    )
    app.state.settings = settings
    app.state.engine = engine
    app.state.sessionmaker = sessionmaker(engine, expire_on_commit=False)
    app.state.get_store = get_store
    app.state.explainer = Explainer(
        settings.anthropic_api_key.get_secret_value(),
        settings.ai_model,
        settings.ai_effort,
        settings.ai_timeout_seconds,
    )
    app.add_middleware(RequestIdMiddleware)
    register_error_handlers(app)
    app.include_router(health.router)
    app.include_router(advisor.router)
    app.include_router(risk.router)
    return app
