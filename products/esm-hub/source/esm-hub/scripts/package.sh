#!/usr/bin/env bash
# Builds all service jars (Gradle in Docker, tests skipped) and the Docker images used by docker-compose.yml.
#   scripts/package.sh            build jars + images
#   SKIP_TESTS=0 scripts/package.sh  also run unit + integration tests first
set -euo pipefail
cd "$(dirname "$0")/.."
if [ "${SKIP_TESTS:-1}" = "0" ]; then scripts/build.sh build; fi
scripts/build.sh bootJar
docker compose build
