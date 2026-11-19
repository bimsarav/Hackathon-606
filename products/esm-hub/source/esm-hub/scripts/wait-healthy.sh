#!/usr/bin/env bash
# Waits until every compose service with a healthcheck reports healthy.  scripts/wait-healthy.sh [timeout_seconds]
set -euo pipefail
cd "$(dirname "$0")/.."
deadline=$(( $(date +%s) + ${1:-600} ))
while :; do
  states="$(docker compose ps --format '{{.Service}} {{.Health}}' | awk '$2 != ""')"
  pending="$(echo "$states" | awk '$2 != "healthy"')"
  if [ -n "$states" ] && [ -z "$pending" ]; then echo "all healthy"; exit 0; fi
  if [ "$(date +%s)" -ge "$deadline" ]; then echo "not healthy in time:"; echo "$pending"; exit 1; fi
  sleep 5
done
