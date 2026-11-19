# Runtime image for any esm-hub Spring Boot service. Build the jars first (scripts/package.sh runs Gradle in Docker),
# then:  docker build -f infrastructure/docker/service.Dockerfile --build-arg SERVICE=incident-service -t esm-hub/incident-service .
FROM eclipse-temurin:27-jre
ARG SERVICE
RUN groupadd --system esm && useradd --system --gid esm --home-dir /app --shell /usr/sbin/nologin esm \
 && apt-get update && apt-get install -y --no-install-recommends curl && rm -rf /var/lib/apt/lists/*
WORKDIR /app
COPY --chown=root:root services/${SERVICE}/build/libs/app.jar /app/app.jar
USER esm
ENV JAVA_TOOL_OPTIONS="-XX:MaxRAMPercentage=75 -XX:+ExitOnOutOfMemoryError" ESM_LOG_FORMAT=ecs
EXPOSE 8080-8089
HEALTHCHECK --interval=15s --timeout=3s --start-period=60s --retries=5 \
  CMD curl -fs "http://127.0.0.1:${SERVER_PORT}/actuator/health/liveness" || exit 1
ENTRYPOINT ["java", "-jar", "/app/app.jar"]
