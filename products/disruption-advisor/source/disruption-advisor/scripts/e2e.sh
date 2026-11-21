#!/usr/bin/env bash
# Playwright end-to-end tests in Docker against a running stack.
#   scripts/e2e.sh                       → http://localhost:${UI_PORT} (from settings.env)
#   E2E_BASE_URL=http://host:8080 scripts/e2e.sh
# Signs in with the first DEMO_USERS entry from settings.env (or E2E_USER / E2E_PASSWORD).
set -euo pipefail
cd "$(dirname "$0")/.."
set -a; if [ -f settings.env ]; then . ./settings.env; elif [ -f .env ]; then . ./.env; fi; set +a
FIRST="${DEMO_USERS%%,*}"
E2E_USER="${E2E_USER:-${FIRST%%:*}}"
REST="${FIRST#*:}"; E2E_PASSWORD="${E2E_PASSWORD:-${REST%%:*}}"
EVAL="$(printf '%s' "${DEMO_USERS:-}" | tr ',' '\n' | grep -i ':EVALUATOR$' | head -1 || true)"  # none: the evaluator tests skip
E2E_EVAL_USER="${E2E_EVAL_USER:-${EVAL%%:*}}"
EVREST="${EVAL#*:}"; E2E_EVAL_PASSWORD="${E2E_EVAL_PASSWORD:-${EVREST%%:*}}"
BASE="${E2E_BASE_URL:-http://localhost:${UI_PORT:-8080}}"
mkdir -p logs
docker run --rm --network host --ipc host -u "$(id -u):$(id -g)" -e HOME=/tmp -e CI=1 \
  -e E2E_BASE_URL="$BASE" -e E2E_USER="$E2E_USER" -e E2E_PASSWORD="$E2E_PASSWORD" \
  -e E2E_EVAL_USER="$E2E_EVAL_USER" -e E2E_EVAL_PASSWORD="$E2E_EVAL_PASSWORD" \
  -v "$PWD/e2e":/e2e -w /e2e mcr.microsoft.com/playwright:v1.65.1 \
  sh -c "npm ci --no-audit --no-fund >/dev/null && npx playwright test" 2>&1 | tee logs/e2e.log
