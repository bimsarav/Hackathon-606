#!/usr/bin/env bash
# Deployment smoke test: builds the images, starts the full stack with Docker Compose, exercises the public endpoints
# through the web container (nginx -> api -> PostgreSQL), then stops the stack and removes its volumes.
#   scripts/smoke.sh [port]
set -euo pipefail
cd "$(dirname "$0")/.."
[ -f .env ] || cp .env.example .env
export WEB_PORT="${1:-18080}"
BASE="http://localhost:$WEB_PORT"
mkdir -p logs
cleanup() { docker compose logs --no-color > logs/smoke-compose.log 2>&1 || true; docker compose down -v --remove-orphans > /dev/null 2>&1 || true; }
trap cleanup EXIT

docker compose build -q > logs/smoke-build.log 2>&1 || { echo "FAIL build (see logs/smoke-build.log)"; tail -n 20 logs/smoke-build.log; exit 1; }
echo "PASS build"
docker compose up -d > logs/smoke-up.log 2>&1 || { echo "FAIL up (see logs/smoke-up.log)"; tail -n 20 logs/smoke-up.log; exit 1; }

health() { docker compose ps --format '{{.Service}} {{.Health}}' | awk -v s="$1" '$1==s{print $2}'; }
for _ in $(seq 1 60); do
  [ "$(health web)" = "healthy" ] && [ "$(health api)" = "healthy" ] && break
  sleep 2
done

FAILED=0
pass() { echo "PASS $1"; }
fail() { echo "FAIL $1"; FAILED=1; }
expect() { # expect <status> <method> <path> [text] [json-body]
  local out code
  if [ -n "${5:-}" ]; then out="$(curl -s -X "$2" -H 'Content-Type: application/json' -d "$5" -w '\n%{http_code}' "$BASE$3")"
  else out="$(curl -s -X "$2" -w '\n%{http_code}' "$BASE$3")"; fi
  code="${out##*$'\n'}"
  if [ "$code" = "$1" ] && { [ -z "${4:-}" ] || grep -q "$4" <<< "$out"; }; then pass "$1 $2 $3"
  else fail "$2 $3: expected $1${4:+ containing '$4'}, got $code"; fi
}
expect 200 GET /healthz "ok"
expect 200 GET / 'id="root"'
expect 200 GET /some/client/route 'id="root"'
expect 201 POST /api/v1/notes '"title":"smoke"' '{"title":"smoke","body":"from smoke.sh"}'
expect 200 GET /api/v1/notes '"title":"smoke"'
expect 422 POST /api/v1/notes 'Unprocessable Content' '{"title":""}'
expect 200 GET /api/openapi.json '"openapi"'
curl -sI "$BASE/" | grep -qi '^content-security-policy:' && pass "security headers on /" || fail "security headers on /"
curl -sI "$BASE/api/v1/notes" | grep -qi '^x-request-id:' && pass "request id on API responses" || fail "request id on API responses"
for s in api web; do [ "$(health $s)" = "healthy" ] && pass "$s container healthcheck" || fail "$s container healthcheck"; done
exit $FAILED
