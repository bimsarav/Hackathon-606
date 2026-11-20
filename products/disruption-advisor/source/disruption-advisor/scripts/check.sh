#!/usr/bin/env bash
# Runs the whole quality gate inside Docker, so no local Python, uv or Node is needed.
#   scripts/check.sh            backend: lint, format, types, tests (Testcontainers PostgreSQL, Alembic)
#                               frontend: npm ci, typecheck, unit tests, production build
#   scripts/check.sh lock       refresh backend/uv.lock and frontend/package-lock.json within the declared ranges
#   scripts/check.sh outdated   list direct dependencies with newer releases (freshness check)
# Full output goes to logs/check-<step>.log; the console shows one line per step.
set -euo pipefail
cd "$(dirname "$0")/.."
ROOT="$PWD"
NAME="$(sed -n "s/^name: //p" compose.yml)"
PY_IMAGE="${NAME}-api-dev:latest"
NODE_IMAGE="node:26.13.1-alpine"
VOLUME="${NAME}-devcache"
mkdir -p logs

docker build -q --target dev -t "$PY_IMAGE" backend >/dev/null
if ! docker volume inspect "$VOLUME" >/dev/null 2>&1; then
  docker volume create "$VOLUME" >/dev/null
  docker run --rm -v "$VOLUME":/cache "$PY_IMAGE" chown -R "$(id -u):$(id -g)" /cache
fi
SOCK_GID="$(stat -c %g /var/run/docker.sock)"

run() { # run <step> <py|node> <command...>
  local step="$1" kind="$2"; shift 2
  local args=(--rm -u "$(id -u):$(id -g)" -e HOME=/tmp -v "$VOLUME":/cache)
  if [ "$kind" = py ]; then
    args+=(--group-add "$SOCK_GID" --network host -v /var/run/docker.sock:/var/run/docker.sock
           -v "$ROOT/backend":/app -w /app -e UV_CACHE_DIR=/cache/uv -e UV_PROJECT_ENVIRONMENT=/cache/venv
           -e TESTCONTAINERS_HOST_OVERRIDE=localhost "$PY_IMAGE")
  else
    args+=(-v "$ROOT/frontend":/web -w /web -e npm_config_cache=/cache/npm -e CI=true -e NO_COLOR=1 "$NODE_IMAGE")
  fi
  if docker run "${args[@]}" "$@" > "logs/check-$step.log" 2>&1; then
    echo "PASS $step"
  else
    echo "FAIL $step (see logs/check-$step.log)"; tail -n 25 "logs/check-$step.log"; exit 1
  fi
}

case "${1:-all}" in
  lock)
    run lock-backend py uv lock
    run lock-frontend node npm install --package-lock-only --no-audit --no-fund
    echo "lock files updated" ;;
  outdated)
    run outdated-backend py uv tree --outdated --depth 1
    grep -E "latest:" logs/check-outdated-backend.log || echo "backend: all direct dependencies current"
    docker run --rm -u "$(id -u):$(id -g)" -e HOME=/tmp -e npm_config_cache=/cache/npm -v "$VOLUME":/cache \
      -v "$ROOT/frontend":/web -w /web "$NODE_IMAGE" npm outdated > logs/check-outdated-frontend.log 2>&1 \
      && echo "frontend: all dependencies current" || cat logs/check-outdated-frontend.log ;;
  all)
    run backend-sync   py uv sync --frozen
    run backend-lint   py uv run --no-sync ruff check .
    run backend-format py uv run --no-sync ruff format --check .
    run backend-types  py uv run --no-sync mypy app tests alembic
    run backend-tests  py uv run --no-sync pytest
    grep -E "passed|failed" logs/check-backend-tests.log | tail -n 1 || true
    run frontend-install   node npm ci --no-audit --no-fund
    run frontend-typecheck node npm run typecheck
    run frontend-tests     node npm test
    grep -E "^ +Tests " logs/check-frontend-tests.log | tail -n 1 || true
    run frontend-build     node npm run build
    ;;
  *) echo "usage: $0 [all|lock|outdated]"; exit 2 ;;
esac
