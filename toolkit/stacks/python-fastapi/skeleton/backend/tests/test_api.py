from alembic import command
from alembic.config import Config
from fastapi.testclient import TestClient


def test_live_returns_up_and_request_id(client: TestClient) -> None:
    response = client.get("/health/live", headers={"X-Request-ID": "abc-123"})
    assert response.status_code == 200
    assert response.json() == {"status": "UP"}
    assert response.headers["X-Request-ID"] == "abc-123"


def test_unsafe_request_id_is_replaced(client: TestClient) -> None:
    response = client.get("/health/live", headers={"X-Request-ID": "bad id"})
    assert response.headers["X-Request-ID"] != "bad id"
    assert len(response.headers["X-Request-ID"]) == 32


def test_ready_checks_database(client: TestClient) -> None:
    response = client.get("/health/ready")
    assert response.status_code == 200
    assert response.json() == {"status": "UP"}


def test_create_list_and_get_note(client: TestClient) -> None:
    created = client.post("/api/v1/notes", json={"title": "  first  ", "body": "hello"})
    assert created.status_code == 201
    note = created.json()
    assert note["title"] == "first"

    listed = client.get("/api/v1/notes")
    assert [n["id"] for n in listed.json()["items"]] == [note["id"]]
    assert client.get(f"/api/v1/notes/{note['id']}").json()["body"] == "hello"


def test_validation_errors_use_problem_details(client: TestClient) -> None:
    response = client.post("/api/v1/notes", json={"title": "", "unexpected": 1})
    assert response.status_code == 422
    assert response.headers["content-type"] == "application/problem+json"
    body = response.json()
    assert body["title"] == "Unprocessable Content"
    assert {tuple(e["loc"]) for e in body["errors"]} >= {("body", "title"), ("body", "unexpected")}


def test_not_found_uses_problem_details(client: TestClient) -> None:
    response = client.get("/api/v1/notes/999")
    assert response.status_code == 404
    assert response.json() == {"type": "about:blank", "title": "Not Found", "status": 404, "detail": "Note not found"}


def test_paging_is_bounded(client: TestClient) -> None:
    assert client.get("/api/v1/notes?limit=101").status_code == 422


def test_openapi_is_published(client: TestClient) -> None:
    assert client.get("/api/openapi.json").json()["info"]["version"] == "1.0.0"


def test_migrations_match_models(alembic_config: Config) -> None:
    command.check(alembic_config)  # raises if the models have changes without a migration
