# ADR-0009: Gradle with Kotlin DSL

- **Status:** Accepted (2026-11-19)
- **Context:** The client requested Gradle (stack update 2026-11-19).
- **Decision:** Gradle 9.9 wrapper, Kotlin DSL, version catalog, buildSrc convention plugins (esm.java-library, esm.spring-service with an integrationTest suite).
- **Consequences:** One place for versions and conventions. Builds run in Docker (scripts/build.sh) without a local JDK.
