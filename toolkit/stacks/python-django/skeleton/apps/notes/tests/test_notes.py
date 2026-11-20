from typing import Any

import pytest
from django.contrib.auth.models import User
from django.test import Client
from rest_framework.test import APIClient

from apps.notes.models import Note

pytestmark = pytest.mark.django_db


@pytest.fixture
def alice(django_user_model: Any) -> User:
    user: User = django_user_model.objects.create_user(username="alice", password="a-long-test-password")
    return user


@pytest.fixture
def bob(django_user_model: Any) -> User:
    user: User = django_user_model.objects.create_user(username="bob", password="a-long-test-password")
    return user


def test_api_requires_authentication() -> None:
    response = APIClient().get("/api/v1/notes/")
    assert response.status_code == 403


def test_api_create_and_list_only_own_notes(alice: User, bob: User) -> None:
    Note.objects.create(owner=bob, title="bob's note")
    api = APIClient()
    api.force_authenticate(alice)

    created = api.post("/api/v1/notes/", {"title": "first", "body": "hello"}, format="json")
    listed = api.get("/api/v1/notes/")

    assert created.status_code == 201
    assert created.json()["title"] == "first"
    assert [n["title"] for n in listed.json()["results"]] == ["first"]


def test_api_validates_input(alice: User) -> None:
    api = APIClient()
    api.force_authenticate(alice)
    response = api.post("/api/v1/notes/", {"title": ""}, format="json")
    assert response.status_code == 400
    assert "title" in response.json()


def test_htmx_create_returns_list_item(client: Client, alice: User) -> None:
    client.force_login(alice)
    response = client.post("/notes/create", {"title": "via htmx"}, headers={"HX-Request": "true"})
    assert response.status_code == 200
    assert b"via htmx" in response.content
    assert Note.objects.filter(owner=alice, title="via htmx").exists()


def test_htmx_create_returns_errors_with_422(client: Client, alice: User) -> None:
    client.force_login(alice)
    response = client.post("/notes/create", {"title": ""})
    assert response.status_code == 422


def test_notes_page_requires_login(client: Client) -> None:
    response = client.get("/notes/")
    assert response.status_code == 302
    assert "/accounts/login/" in response["Location"]
