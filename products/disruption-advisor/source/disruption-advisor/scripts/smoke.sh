#!/usr/bin/env bash
# Post-deployment smoke test against a RUNNING stack (local or server). Read-mostly: it signs in, reads reference
# data and runs one cancellation analysis (stored as a normal scenario). It never builds, stops or deletes anything.
#   scripts/smoke.sh                         → UI http://localhost:${UI_PORT}, API http://localhost:${API_PORT}
#   scripts/smoke.sh http://92.5.154.198:8080 http://92.5.154.198:8888
# Credentials: the first DEMO_USERS entry in settings.env, or SMOKE_USER / SMOKE_PASSWORD.
set -euo pipefail
cd "$(dirname "$0")/.."
set -a; if [ -f settings.env ]; then . ./settings.env; elif [ -f .env ]; then . ./.env; fi; set +a
BASE="${1:-http://localhost:${UI_PORT:-8080}}"
API_BASE="${2:-http://localhost:${API_PORT:-8888}}"
FIRST="${DEMO_USERS:-}"; FIRST="${FIRST%%,*}"
USER_NAME="${SMOKE_USER:-${FIRST%%:*}}"; REST="${FIRST#*:}"; PASSWORD="${SMOKE_PASSWORD:-${REST%%:*}}"

FAILED=0
pass() { echo "PASS $1"; }
fail() { echo "FAIL $1"; FAILED=1; }
expect() { # expect <status> <method> <path> [text] [json-body] [token]
  local out code args=(-s -X "$2" -w '\n%{http_code}')
  [ -n "${6:-}" ] && args+=(-H "Authorization: Bearer $6")
  [ -n "${5:-}" ] && args+=(-H 'Content-Type: application/json' -d "$5")
  out="$(curl "${args[@]}" "$BASE$3")"
  code="${out##*$'\n'}"
  if [ "$code" = "$1" ] && { [ -z "${4:-}" ] || grep -q -- "$4" <<< "$out"; }; then pass "$1 $2 $3"
  else fail "$2 $3: expected $1${4:+ containing '$4'}, got $code"; fi
}

expect 200 GET /healthz "ok"
expect 200 GET / 'id="root"'
expect 200 GET /some/client/route 'id="root"'
expect 200 GET /api/openapi.json '"openapi"'
expect 401 GET /api/v1/meta
expect 401 POST /api/v1/auth/login 'Wrong user name or password' '{"username":"nobody","password":"wrong"}'
curl -sI "$BASE/" | grep -qi '^content-security-policy:' && pass "security headers on /" || fail "security headers on /"

TOKEN="$(curl -s -X POST -H 'Content-Type: application/json' \
  -d "{\"username\":\"$USER_NAME\",\"password\":\"$PASSWORD\"}" "$BASE/api/v1/auth/login" \
  | sed -n 's/.*"token":"\([^"]*\)".*/\1/p')"
[ -n "$TOKEN" ] && pass "sign in as $USER_NAME" || { fail "sign in as $USER_NAME"; exit 1; }
expect 200 GET /api/v1/meta '"flights"' "" "$TOKEN"
PRESETS="$(curl -s -H "Authorization: Bearer $TOKEN" "$BASE/api/v1/presets")"
CANCEL_ID="$(sed -n 's/.*"cancel":\[{"flight_id":"\([^"]*\)".*/\1/p' <<< "$PRESETS")"
[ -n "$CANCEL_ID" ] && pass "presets include a cancellation candidate ($CANCEL_ID)" || fail "presets"
[ -n "$CANCEL_ID" ] && expect 201 POST /api/v1/scenarios '"solver_status":"OPTIMAL"' \
  "{\"kind\":\"CANCEL\",\"flight_id\":\"$CANCEL_ID\"}" "$TOKEN"

# API port: the API answers directly; the UI is not served there and nothing redirects.
api_expect() { # api_expect <status> <path> [text]
  local out code; out="$(curl -s -w '\n%{http_code}' "$API_BASE$2")"; code="${out##*$'\n'}"
  if [ "$code" = "$1" ] && { [ -z "${3:-}" ] || grep -q -- "$3" <<< "$out"; }; then pass "API $1 GET $2"
  else fail "API GET $2: expected $1${3:+ containing '$3'}, got $code"; fi
}
api_expect 200 /health/live
api_expect 200 /api/openapi.json '"openapi"'
api_expect 401 /api/v1/meta
api_expect 404 /
exit $FAILED
