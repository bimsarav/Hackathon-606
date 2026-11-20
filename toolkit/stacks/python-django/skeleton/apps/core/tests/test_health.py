import pytest
from django.test import Client


def test_live_returns_up_and_request_id(client: Client) -> None:
    response = client.get("/health/live", headers={"X-Request-ID": "abc-123"})
    assert response.status_code == 200
    assert response.json() == {"status": "UP"}
    assert response["X-Request-ID"] == "abc-123"


def test_unsafe_request_id_is_replaced(client: Client) -> None:
    response = client.get("/health/live", headers={"X-Request-ID": "bad id\n"})
    assert response["X-Request-ID"] != "bad id\n"
    assert len(response["X-Request-ID"]) == 32


@pytest.mark.django_db
def test_ready_checks_database(client: Client) -> None:
    response = client.get("/health/ready")
    assert response.status_code == 200
    assert response.json() == {"status": "UP"}


def test_home_renders(client: Client) -> None:
    response = client.get("/")
    assert response.status_code == 200
    assert b"Sample App" in response.content
