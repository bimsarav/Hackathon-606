#!/usr/bin/env bash
# Starts/stops a throwaway PostgreSQL 16 with the repaired legacy dump loaded (schema `esmp`), on localhost:55433.
#   tools/seed/legacy-db.sh up | down | psql
# Used only by the seed export (tools/seed/export.sh) and the data profiling (tools/profiling).
set -euo pipefail
cd "$(dirname "$0")"
NAME=esmhub-legacy-db
case "${1:-up}" in
  up)
    if docker ps --format '{{.Names}}' | grep -qx "$NAME"; then echo "already running"; exit 0; fi
    docker run -d --rm --name "$NAME" -e POSTGRES_PASSWORD=legacy -p 55433:5432 postgres:16-alpine >/dev/null
    until docker exec "$NAME" pg_isready -U postgres >/dev/null 2>&1; do sleep 1; done
    sleep 1
    python3 repair_dump.py legacy/esmp_sample_dump.sql | docker exec -i "$NAME" psql -q -v ON_ERROR_STOP=1 -U postgres >/dev/null
    echo "legacy db up on localhost:55433 (schema esmp, $(docker exec "$NAME" psql -U postgres -Atc 'select count(*) from esmp.incidents') incidents)"
    ;;
  down) docker rm -f "$NAME" >/dev/null 2>&1 || true; echo "legacy db removed" ;;
  psql) shift; docker exec -i "$NAME" psql -U postgres "$@" ;;
  *) echo "usage: $0 up|down|psql" >&2; exit 2 ;;
esac
