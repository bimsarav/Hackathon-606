import structlog
from fastapi import APIRouter, Request, Response, status
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

router = APIRouter(prefix="/health", tags=["health"])
log = structlog.get_logger(__name__)


@router.get("/live")
def live() -> dict[str, str]:
    """Liveness: the process is running. Never checks dependencies."""
    return {"status": "UP"}


@router.get("/ready")
def ready(request: Request, response: Response) -> dict[str, str]:
    """Readiness: the database answers and the operating data (Parquet) is loaded."""
    try:
        with request.app.state.engine.connect() as connection:
            connection.execute(text("SELECT 1"))
    except SQLAlchemyError:
        log.warning("readiness_check_failed", dependency="database")
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
        return {"status": "DOWN"}
    if request.app.state.get_store() is None:
        log.warning("readiness_check_failed", dependency="ops_data")
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
        return {"status": "DOWN"}
    return {"status": "UP"}
