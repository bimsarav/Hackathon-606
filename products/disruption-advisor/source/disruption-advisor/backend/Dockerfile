# Multi-stage image. Versions come from docs/architecture/COMPATIBILITY_MATRIX.md; change them there first.
ARG PYTHON_IMAGE=python:3.14.10-slim-trixie
FROM ghcr.io/astral-sh/uv:0.13.9 AS uv

FROM ${PYTHON_IMAGE} AS base
COPY --from=uv /uv /uvx /usr/local/bin/
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 UV_LINK_MODE=copy UV_PYTHON_DOWNLOADS=never
WORKDIR /app

# Toolchain image used by scripts/check.sh (lint, type check, tests). The project is mounted, not copied.
FROM base AS dev

FROM base AS build
ENV UV_COMPILE_BYTECODE=1
COPY pyproject.toml uv.lock .python-version ./
RUN uv sync --frozen --no-dev --no-install-project
COPY alembic.ini ./
COPY alembic ./alembic
COPY app ./app

FROM ${PYTHON_IMAGE} AS runtime
# Security: apply OS updates published after the base image, and drop pip (unused at runtime; uv built the venv),
# whose vendored libraries otherwise show up in vulnerability scans.
RUN apt-get update && apt-get upgrade -y --no-install-recommends && rm -rf /var/lib/apt/lists/* \
 && python -m pip uninstall -y pip && rm -rf /usr/local/lib/python3.14/ensurepip/_bundled \
 && groupadd --system app && useradd --system --gid app --home-dir /app --shell /usr/sbin/nologin app \
 && mkdir -p /data && chown app:app /data
WORKDIR /app
ENV PATH="/app/.venv/bin:$PATH" PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
COPY --from=build /app /app
USER app
EXPOSE 8000
HEALTHCHECK --interval=15s --timeout=3s --start-period=20s --retries=5 \
  CMD ["python", "-c", "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/health/live', timeout=2)"]
CMD ["python", "-m", "app.serve"]
