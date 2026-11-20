"""Test database: a throw-away PostgreSQL container (Testcontainers), same major version as production."""

from collections.abc import Iterator

import pytest
from django.conf import settings
from pytest_django.fixtures import Settings
from testcontainers.community.postgres import PostgresContainer

POSTGRES_IMAGE = "postgres:18.7-alpine"


@pytest.fixture(scope="session")
def django_db_modify_db_settings(django_db_modify_db_settings_parallel_suffix: None) -> Iterator[None]:
    with PostgresContainer(POSTGRES_IMAGE, driver=None) as pg:
        settings.DATABASES["default"].update(
            {
                "HOST": pg.get_container_host_ip(),
                "PORT": str(pg.get_exposed_port(5432)),
                "NAME": pg.dbname,
                "USER": pg.username,
                "PASSWORD": pg.password,
            }
        )
        yield


@pytest.fixture(autouse=True)
def _plain_static_storage(settings: Settings) -> None:
    """The manifest storage needs collectstatic output, which only the Docker image build produces."""
    plain = {"BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage"}
    settings.STORAGES = {**settings.STORAGES, "staticfiles": plain}
