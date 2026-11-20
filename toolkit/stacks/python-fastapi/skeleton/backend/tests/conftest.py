"""Test database: a throw-away PostgreSQL container (Testcontainers), migrated with Alembic exactly as in production."""

from collections.abc import Iterator

import pytest
from alembic import command
from alembic.config import Config
from fastapi.testclient import TestClient
from sqlalchemy import text
from testcontainers.community.postgres import PostgresContainer

from app.config import Settings
from app.main import create_app

POSTGRES_IMAGE = "postgres:18.7-alpine"


@pytest.fixture(scope="session")
def alembic_config() -> Iterator[Config]:
    with PostgresContainer(POSTGRES_IMAGE, driver="psycopg") as pg:
        config = Config("alembic.ini")
        config.set_main_option("sqlalchemy.url", pg.get_connection_url())
        command.upgrade(config, "head")
        yield config


@pytest.fixture
def client(alembic_config: Config) -> Iterator[TestClient]:
    url = alembic_config.get_main_option("sqlalchemy.url")
    assert url
    app = create_app(Settings(database_url=url, log_json=False))
    with TestClient(app) as test_client:
        yield test_client
    with app.state.engine.begin() as connection:
        connection.execute(text("TRUNCATE notes RESTART IDENTITY"))
