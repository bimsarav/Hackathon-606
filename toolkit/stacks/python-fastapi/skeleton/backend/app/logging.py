"""Structured logging: JSON lines in production, readable console output in development.

Every log line carries the request id bound by ``app.middleware.RequestIdMiddleware``.
Never log passwords, tokens or personal data.
"""

import logging.config
from typing import Any

import structlog

_SHARED: list[Any] = [
    structlog.contextvars.merge_contextvars,
    structlog.stdlib.add_log_level,
    structlog.stdlib.add_logger_name,
    structlog.processors.TimeStamper(fmt="iso", utc=True),
]


def configure_logging(level: str, as_json: bool) -> None:
    renderer: Any = structlog.processors.JSONRenderer() if as_json else structlog.dev.ConsoleRenderer()
    structlog.configure(
        processors=[*_SHARED, structlog.stdlib.ProcessorFormatter.wrap_for_formatter],
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )
    logging.config.dictConfig(
        {
            "version": 1,
            "disable_existing_loggers": False,
            "formatters": {
                "structured": {
                    "()": structlog.stdlib.ProcessorFormatter,
                    "processors": [structlog.stdlib.ProcessorFormatter.remove_processors_meta, renderer],
                    "foreign_pre_chain": _SHARED,
                }
            },
            "handlers": {"console": {"class": "logging.StreamHandler", "formatter": "structured"}},
            "root": {"handlers": ["console"], "level": level},
            # Uvicorn's own loggers propagate to the root handler (uvicorn runs with log_config=None).
            "loggers": {
                name: {"handlers": [], "propagate": True} for name in ("uvicorn", "uvicorn.error", "uvicorn.access")
            },
        }
    )
