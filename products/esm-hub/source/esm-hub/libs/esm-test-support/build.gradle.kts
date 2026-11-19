// Shared test infrastructure: Testcontainers (PostgreSQL 16, Kafka 4.4) and a JWT minter with a fixed TEST-ONLY key.
plugins { id("esm.java-library") }

dependencies {
    api(libs.starter.test)
    api(libs.starter.security.test)
    api(libs.starter.webmvc.test)
    api(libs.boot.testcontainers)
    api(libs.testcontainers.postgresql)
    api(libs.testcontainers.kafka)
    api(libs.testcontainers.junit)
    api(libs.starter.oauth2.resource.server)
    api(libs.starter.webmvc)
}
