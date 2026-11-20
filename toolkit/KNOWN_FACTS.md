# Known facts (verified; read before researching or debugging)

One line per fact, with the date verified. Add a fact whenever something cost more than one attempt. Remove it when it stops being true.

## Host and tooling
- 2026-11-19 · Host: Docker Engine 20.10.24, Compose v2.21.0; 22 CPUs; about 10 GB free RAM; disk about 93% full (35 GB free). Prune verify images (`verify-*`) after profile work. Host java/node are too old: build everything in Docker.
- 2026-11-19 · Docker 20.10 (API 1.41) works with Testcontainers Python 4.15 and Java 2.0.x (esm-hub), via the socket mount plus `TESTCONTAINERS_HOST_OVERRIDE=localhost` and `--network host`.
- 2026-11-19 · The UTC date can differ from the user's local date (UTC+4). Stamp logs with `date -u +%Y-%m-%dT%H:%MZ`, never a hand-typed date.
- 2026-11-19 · Claude Code's safety check blocks `rm -rf "$VAR"` and some complex heredoc commands. Extract into fixed scratchpad paths, and write files with the Write tool instead of large heredocs.
- 2026-11-19 · Version sources that work without auth: PyPI JSON (`pypi.org/pypi/<pkg>/json`), npm (`registry.npmjs.org/<pkg>/latest`), Packagist, NuGet, Maven Central metadata, Docker Hub tags API, GitHub releases API, endoflife.date (`/api/<product>.json`; `/api/v1/...` returns 404).

## Current versions and lifecycles (2026-11-19)
- Python 3.14.10 (3.15 released 2026-10; not adopted yet). Django 5.2.19 LTS (to 2028-04; 6.1.3 is the current non-LTS). PostgreSQL 18.7 (to 2030-11). Node 26.13.1 LTS (to 2029-04). nginx stable 1.30.7. uv 0.13.9. Trivy 0.76.2.
- Spring Boot 4.1.2 (OSS support to 2027-07), PHP 8.5.12 / 8.4.27, Laravel 13.43 (to 2028-03), .NET 10 LTS (10.0.15, to 2028-11), NestJS 11.2 / 12.5.
- GitHub Actions: `actions/checkout@v7.0.1`, `actions/upload-artifact@v7.0.2`, `aquasecurity/trivy-action@v0.36.0` (tags carry a `v` prefix). esm-hub's CI still pins checkout@v4 and trivy-action 0.33.1; update it in T-006.1.

## Pitfalls already solved (python profiles)
- Django: subscripting `ModelForm[...]`, `ModelSerializer[...]` or `ModelViewSet[...]` needs `django_stubs_ext.monkeypatch(extra_classes=[...])` in `AppConfig.ready()`. Calling it from `settings.py` imports DRF too early and breaks drf-spectacular (E001).
- django-stubs 5.2 (`compatible-mypy`) pins mypy 1.19.x; mypy 2.x comes with django-stubs 6.x.
- django-environ has no type information: use an inline `# type: ignore[import-untyped]` (a pyproject override was ignored).
- pytest-django: point tests at Testcontainers by overriding the `django_db_modify_db_settings` fixture; its settings fixture type is `pytest_django.fixtures.Settings`.
- whitenoise `CompressedManifestStaticFilesStorage` needs `collectstatic`: tests switch to `StaticFilesStorage`; filter the "No directory at" UserWarning (it is raised from Django's module, so the filter must not name whitenoise).
- Testcontainers Python: import from `testcontainers.community.postgres` (the old path is deprecated).
- Starlette 1.x: `TestClient` wants `httpx2` (pydantic org) instead of `httpx`.
- Alembic CLI does not put the working directory on the import path: set `prepend_sys_path = .` in `alembic.ini` (pytest hides this).
- Ruff treats `alembic` as first-party when an `alembic/` folder exists: set `known-third-party = ["alembic"]`.
- Vitest output contains ANSI colours: run Node steps with `CI=true NO_COLOR=1`.
- Base images ship known CVEs: run `apt-get upgrade` / `apk upgrade` in the runtime stage, and remove pip from Python runtime images (its vendored msgpack, urllib3 and setuptools get flagged).
- `nginxinc/nginx-unprivileged` can lag behind nginx security releases (1.30.6 vs 1.30.7 on 2026-11-19). Run `nginx:<patched>-alpine` as user `nginx` instead: delete the `user` line, put the PID in `/tmp`, chown `/var/cache/nginx`, listen on 8080.
- PostgreSQL 18 images: mount the volume at `/var/lib/postgresql` (not `.../data`).
- Product names replace `sample_app`: keep lines with sample identifiers short, or long product names break the 120-character lint rule.
