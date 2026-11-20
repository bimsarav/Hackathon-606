#!/usr/bin/env bash
# Deployment smoke test: builds the images, starts the full stack with Docker Compose, checks the public endpoints,
# then stops the stack and removes its volumes.   scripts/smoke.sh [port]
set -euo pipefail
cd "$(dirname "$0")/.."
[ -f .env ] || cp .env.example .env
export WEB_PORT="${1:-18000}"
BASE="http://localhost:$WEB_PORT"
mkdir -p logs
cleanup() { docker compose logs --no-color > logs/smoke-compose.log 2>&1 || true; docker compose down -v --remove-orphans > /dev/null 2>&1 || true; }
trap cleanup EXIT

docker compose build -q > logs/smoke-build.log 2>&1 || { echo "FAIL build (see logs/smoke-build.log)"; tail -n 20 logs/smoke-build.log; exit 1; }
echo "PASS build"
docker compose up -d > logs/smoke-up.log 2>&1 || { echo "FAIL up (see logs/smoke-up.log)"; tail -n 20 logs/smoke-up.log; exit 1; }

health() { docker compose ps --format '{{.Service}} {{.Health}}' | awk '$1=="web"{print $2}'; }
for _ in $(seq 1 60); do
  [ "$(health)" = "healthy" ] && curl -fs "$BASE/health/ready" > /dev/null 2>&1 && break
  sleep 2
done

FAILED=0
expect() { # expect <status> <path> [text]
  local body code
  body="$(curl -s -o - -w '\n%{http_code}' "$BASE$2")"; code="${body##*$'\n'}"
  if [ "$code" = "$1" ] && { [ -z "${3:-}" ] || grep -q "$3" <<< "$body"; }; then echo "PASS $1 $2"
  else echo "FAIL $2: expected $1${3:+ containing '$3'}, got $code"; FAILED=1; fi
}
expect 200 /health/live '"UP"'
expect 200 /health/ready '"UP"'
expect 200 / "<h1>"
expect 200 /accounts/login/ "Sign in"
expect 200 /static/vendor/htmx.min.js "htmx"
expect 302 /notes/
expect 403 /api/v1/notes/
[ "$(health)" = "healthy" ] \
  && echo "PASS web container healthcheck" || { echo "FAIL web container healthcheck"; FAILED=1; }
exit $FAILED
