"""Consistent error responses: RFC 9457 problem details (application/problem+json) for every error."""

from http import HTTPStatus
from typing import Any

import structlog
from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException

log = structlog.get_logger(__name__)


def problem(status: int, detail: str | None = None, errors: list[dict[str, Any]] | None = None) -> JSONResponse:
    body: dict[str, Any] = {"type": "about:blank", "title": HTTPStatus(status).phrase, "status": status}
    if detail:
        body["detail"] = detail
    if errors:
        body["errors"] = errors
    return JSONResponse(body, status_code=status, media_type="application/problem+json")


async def _http_error(request: Request, exc: Exception) -> JSONResponse:
    assert isinstance(exc, HTTPException)  # noqa: S101  (registered for HTTPException only)
    return problem(exc.status_code, str(exc.detail) if exc.detail else None)


async def _validation_error(request: Request, exc: Exception) -> JSONResponse:
    assert isinstance(exc, RequestValidationError)  # noqa: S101  (registered for RequestValidationError only)
    errors = [{"loc": list(error["loc"]), "msg": error["msg"]} for error in exc.errors()]
    return problem(HTTPStatus.UNPROCESSABLE_CONTENT, "Request validation failed", errors)


async def _unhandled_error(request: Request, exc: Exception) -> JSONResponse:
    log.exception("unhandled_error", path=request.url.path)
    return problem(HTTPStatus.INTERNAL_SERVER_ERROR)


def register_error_handlers(app: FastAPI) -> None:
    app.add_exception_handler(HTTPException, _http_error)
    app.add_exception_handler(RequestValidationError, _validation_error)
    app.add_exception_handler(Exception, _unhandled_error)
