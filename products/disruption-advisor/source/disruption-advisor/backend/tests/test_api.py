from alembic import command
from alembic.config import Config
from fastapi.testclient import TestClient

from tests.ops_fixture import F1, X1


def test_live_returns_up_and_request_id(client: TestClient) -> None:
    response = client.get("/health/live", headers={"X-Request-ID": "abc-123"})
    assert response.status_code == 200
    assert response.json() == {"status": "UP"}
    assert response.headers["X-Request-ID"] == "abc-123"


def test_unsafe_request_id_is_replaced(client: TestClient) -> None:
    response = client.get("/health/live", headers={"X-Request-ID": "bad id"})
    assert response.headers["X-Request-ID"] != "bad id"
    assert len(response.headers["X-Request-ID"]) == 32


def test_ready_checks_database_and_operating_data(client: TestClient) -> None:
    response = client.get("/health/ready")
    assert response.status_code == 200
    assert response.json() == {"status": "UP"}


def test_login_rejects_wrong_password_and_routes_need_a_token(client: TestClient) -> None:
    bad = client.post("/api/v1/auth/login", json={"username": "pcu", "password": "nope"})
    assert bad.status_code == 401
    assert bad.headers["content-type"] == "application/problem+json"
    assert client.get("/api/v1/meta").status_code == 401
    assert client.get("/api/v1/meta", headers={"Authorization": "Bearer forged.token"}).status_code == 401


def test_login_returns_role(client: TestClient) -> None:
    body = client.post("/api/v1/auth/login", json={"username": "occ", "password": "occ-pass"}).json()
    assert body["role"] == "OCC"
    assert body["token"]


def test_meta_and_flight_search(client: TestClient, auth: dict[str, str]) -> None:
    meta = client.get("/api/v1/meta", headers=auth).json()
    assert meta["user"]["role"] == "PCU"
    assert meta["ai_enabled"] is False
    flights = client.get("/api/v1/flights?q=G9001", headers=auth).json()
    assert [f["flight_id"] for f in flights] == [F1]


def test_delay_scenario_end_to_end_with_decision(client: TestClient, auth: dict[str, str]) -> None:
    created = client.post(
        "/api/v1/scenarios", headers=auth, json={"kind": "DELAY", "flight_id": F1, "delay_minutes": 150}
    )
    assert created.status_code == 201
    scenario = created.json()
    assert scenario["result"]["recommended_key"].startswith("swap:")
    assert len(scenario["result"]["misconnections"]) == 2

    decision = client.post(
        f"/api/v1/scenarios/{scenario['id']}/decisions",
        headers=auth,
        json={"target": f"option:{scenario['result']['recommended_key']}", "action": "APPROVE"},
    )
    assert decision.status_code == 201
    assert decision.json()["decided_by"] == "pcu (PCU)"
    listed = client.get(f"/api/v1/scenarios/{scenario['id']}/decisions", headers=auth).json()
    assert [d["action"] for d in listed] == ["APPROVE"]
    assert [s["id"] for s in client.get("/api/v1/scenarios", headers=auth).json()] == [scenario["id"]]


def test_cancellation_what_if_and_message_draft(client: TestClient, auth: dict[str, str]) -> None:
    scenario = client.post("/api/v1/scenarios", headers=auth, json={"kind": "CANCEL", "flight_id": X1}).json()
    rows = scenario["result"]["passengers"]
    assert rows[0]["tier"] == 1
    weights = {"loyalty": 100, "frequency": 0, "fare_value": 0, "ancillaries": 0, "journey": 0, "booking": 0}
    updated = client.post(
        f"/api/v1/scenarios/{scenario['id']}/reprioritise", headers=auth, json={"weights": weights}
    ).json()
    assert updated["weights"]["loyalty"] == 100
    draft = client.post(
        f"/api/v1/scenarios/{scenario['id']}/messages", headers=auth, json={"customer_key": rows[0]["customer_key"]}
    ).json()
    assert draft["source"] == "template"
    assert draft["text"].startswith("Dear customer")


def test_delay_requires_minutes_and_validates_input(client: TestClient, auth: dict[str, str]) -> None:
    missing = client.post("/api/v1/scenarios", headers=auth, json={"kind": "DELAY", "flight_id": F1})
    assert missing.status_code == 422
    bad = client.post(
        "/api/v1/scenarios", headers=auth, json={"kind": "DELAY", "flight_id": "x'; drop", "delay_minutes": 60}
    )
    assert bad.status_code == 422
    assert bad.headers["content-type"] == "application/problem+json"


def test_unknown_flight_and_scenario_are_404(client: TestClient, auth: dict[str, str]) -> None:
    unknown = client.post("/api/v1/scenarios", headers=auth, json={"kind": "CANCEL", "flight_id": "G9999_202611210000"})
    assert unknown.status_code == 404
    missing = client.get("/api/v1/scenarios/00000000-0000-0000-0000-000000000000", headers=auth)
    assert missing.status_code == 404


def test_openapi_is_published(client: TestClient) -> None:
    assert client.get("/api/openapi.json").json()["info"]["version"] == "1.0.0"


def test_migrations_match_models(alembic_config: Config) -> None:
    command.check(alembic_config)  # raises if the models have changes without a migration
