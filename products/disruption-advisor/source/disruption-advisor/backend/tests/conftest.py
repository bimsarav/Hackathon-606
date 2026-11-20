"""Test database: a throw-away PostgreSQL container (Testcontainers), migrated with Alembic exactly as in production.
Operating data: the hand-made Parquet network in tests/ops_fixture.py."""

from collections.abc import Iterator
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from fastapi.testclient import TestClient
from pydantic import SecretStr
from sqlalchemy import text
from testcontainers.community.postgres import PostgresContainer

from app.config import Settings
from app.main import create_app
from app.ml import delay_risk
from tests.ops_fixture import t, write_ops

POSTGRES_IMAGE = "postgres:18.7-alpine"


@pytest.fixture(scope="session")
def alembic_config() -> Iterator[Config]:
    with PostgresContainer(POSTGRES_IMAGE, driver="psycopg") as pg:
        config = Config("alembic.ini")
        config.set_main_option("sqlalchemy.url", pg.get_connection_url())
        command.upgrade(config, "head")
        yield config


@pytest.fixture(scope="session")
def data_dir(tmp_path_factory: pytest.TempPathFactory) -> Path:
    path = tmp_path_factory.mktemp("data")
    delay_risk.run(write_ops(path), default_mct=50)  # phase 2 outputs, as ingest stage 3 writes them
    return path


@pytest.fixture
def client(alembic_config: Config, data_dir: Path) -> Iterator[TestClient]:
    url = alembic_config.get_main_option("sqlalchemy.url")
    assert url
    settings = Settings(
        database_url=url,
        log_json=False,
        data_dir=data_dir,
        now_utc=t(0),
        demo_users=SecretStr("occ:occ-pass:OCC,pcu:pcu-pass:PCU"),
        token_secret=SecretStr("test-secret-0123456789"),
    )
    app = create_app(settings)
    with TestClient(app) as test_client:
        yield test_client
    with app.state.engine.begin() as connection:
        connection.execute(text("TRUNCATE scenarios, decisions RESTART IDENTITY CASCADE"))


@pytest.fixture
def auth(client: TestClient) -> dict[str, str]:
    token = client.post("/api/v1/auth/login", json={"username": "pcu", "password": "pcu-pass"}).json()["token"]
    return {"Authorization": f"Bearer {token}"}
