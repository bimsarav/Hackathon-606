#!/usr/bin/env bash
# Runs the whole quality gate inside Docker, so no local Python or uv is needed.
#   scripts/check.sh            lint + format check + type check + tests (Testcontainers PostgreSQL)
#   scripts/check.sh lock       refresh uv.lock within the pyproject ranges
#   scripts/check.sh outdated   list direct dependencies with newer releases (freshness check)
#   scripts/check.sh migrations create migrations after model changes (makemigrations)
# Full output goes to logs/check-<step>.log; the console shows one line per step (token- and noise-friendly).
set -euo pipefail
cd "$(dirname "$0")/.."
NAME="$(sed -n "s/^name: //p" compose.yml)"
IMAGE="${NAME}-dev:latest"
VOLUME="${NAME}-pycache"
mkdir -p logs

docker build -q --target dev -t "$IMAGE" . >/dev/null
if ! docker volume inspect "$VOLUME" >/dev/null 2>&1; then
  docker volume create "$VOLUME" >/dev/null
  docker run --rm -v "$VOLUME":/cache "$IMAGE" chown -R "$(id -u):$(id -g)" /cache
fi
SOCK_GID="$(stat -c %g /var/run/docker.sock)"

run() { # run <step> <command...>
  local step="$1"; shift
  if docker run --rm -u "$(id -u):$(id -g)" --group-add "$SOCK_GID" --network host \
      -v /var/run/docker.sock:/var/run/docker.sock -v "$VOLUME":/cache -v "$PWD":/app -w /app \
      -e HOME=/tmp -e UV_CACHE_DIR=/cache/uv -e UV_PROJECT_ENVIRONMENT=/cache/venv \
      -e TESTCONTAINERS_HOST_OVERRIDE=localhost -e DJANGO_SECRET_KEY=test-only-not-secret-Zq8vK2pL9wX4rT6yB1nM3cF5hJ7dG0sA \
      "$IMAGE" "$@" > "logs/check-$step.log" 2>&1; then
    echo "PASS $step"
  else
    echo "FAIL $step (see logs/check-$step.log)"; tail -n 25 "logs/check-$step.log"; exit 1
  fi
}

case "${1:-all}" in
  lock)       run lock uv lock; echo "uv.lock updated" ;;
  outdated)   run outdated uv tree --outdated --depth 1; grep -E "latest:" "logs/check-outdated.log" || echo "all direct dependencies current" ;;
  migrations) run migrations sh -c "uv sync --frozen && uv run --no-sync python manage.py makemigrations" ;;
  all)
    run sync   uv sync --frozen
    run lint   uv run --no-sync ruff check .
    run format uv run --no-sync ruff format --check .
    run types  uv run --no-sync mypy .
    run django uv run --no-sync python manage.py check --deploy --fail-level ERROR
    run migrations-up-to-date uv run --no-sync python manage.py makemigrations --check --dry-run
    run tests  uv run --no-sync pytest
    grep -E "passed|failed" "logs/check-tests.log" | tail -n 1
    ;;
  *) echo "usage: $0 [all|lock|outdated|migrations]"; exit 2 ;;
esac
