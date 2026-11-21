"""Crew FDP analysis: what the crew roster says about flight duty period headroom.

Built by the ingest (app/ingest/build.py ``_crew``) from the roster's planned/actual FDP and maximum FDP. Contains
counts and percentages only: no crew names or IDs.
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException, Request, status

from app.auth import CurrentUser
from app.engine.store import OpsStore

router = APIRouter(prefix="/api/v1/crew", tags=["crew"])


@router.get("/fdp")
def crew_fdp(request: Request, _: CurrentUser) -> dict[str, Any]:
    store: OpsStore | None = request.app.state.get_store()
    if store is None:
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, "Operating data is not loaded yet (run the ingest)")
    if not store.crew_fdp:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "No crew roster was supplied (crew.parquet)")
    return {
        **store.crew_fdp,
        "rules": {
            "tight_below_minutes": request.app.state.settings.crew_tight_minutes,
        },
    }
