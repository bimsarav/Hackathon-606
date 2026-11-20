import structlog
from django.db import DatabaseError, connection
from django.http import HttpRequest, HttpResponse, JsonResponse
from django.shortcuts import render
from django.views.decorators.http import require_GET

log = structlog.get_logger(__name__)


@require_GET
def live(request: HttpRequest) -> JsonResponse:
    """Liveness: the process is running. Never checks dependencies."""
    return JsonResponse({"status": "UP"})


@require_GET
def ready(request: HttpRequest) -> JsonResponse:
    """Readiness: the database answers."""
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
    except DatabaseError:
        log.warning("readiness_check_failed", dependency="database")
        return JsonResponse({"status": "DOWN"}, status=503)
    return JsonResponse({"status": "UP"})


@require_GET
def home(request: HttpRequest) -> HttpResponse:
    return render(request, "home.html")
