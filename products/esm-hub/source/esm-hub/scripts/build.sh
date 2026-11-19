#!/usr/bin/env bash
# Runs the Gradle build inside Docker, so no local JDK or Gradle is needed.
#   scripts/build.sh build                      compile + unit + integration tests (Testcontainers)
#   scripts/build.sh :services:incident-service:test
# The Docker socket is shared for Testcontainers; host networking makes mapped container ports reachable on localhost.
# Gradle caches persist in the Docker volume `esmhub-gradle`. For parallel builds in one checkout, give each builder its
# own project cache: ESM_GRADLE_PROJECT_CACHE=.gradle-<name> scripts/build.sh ...
set -euo pipefail
cd "$(dirname "$0")/.."
IMAGE="${GRADLE_IMAGE:-gradle:9.9.1-jdk27}"
SOCK_GID="$(stat -c %g /var/run/docker.sock)"
if ! docker volume inspect esmhub-gradle >/dev/null 2>&1; then
  docker volume create esmhub-gradle >/dev/null
  docker run --rm -v esmhub-gradle:/cache "$IMAGE" chown -R "$(id -u):$(id -g)" /cache
fi
exec docker run --rm -u "$(id -u):$(id -g)" --group-add "$SOCK_GID" --network host \
  -v /var/run/docker.sock:/var/run/docker.sock \
  -e GRADLE_USER_HOME=/cache -e HOME=/tmp -e TESTCONTAINERS_HOST_OVERRIDE=localhost \
  -v esmhub-gradle:/cache -v "$PWD":/workspace -w /workspace \
  "$IMAGE" ./gradlew --no-daemon --console=plain ${ESM_GRADLE_PROJECT_CACHE:+--project-cache-dir "$ESM_GRADLE_PROJECT_CACHE"} "$@"
