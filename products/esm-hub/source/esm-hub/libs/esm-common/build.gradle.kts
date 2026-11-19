// Cross-cutting library: problem+json errors, JWT resource-server security, request id, transactional outbox,
// idempotent consumers, snapshot bootstrap, audit events, paging, CSV. Exposed as `api` so services inherit it.
plugins { id("esm.java-library") }

dependencies {
    api(libs.starter.webmvc)
    api(libs.starter.validation)
    api(libs.starter.data.jpa)
    api(libs.starter.flyway)
    api(libs.flyway.postgresql)
    api(libs.starter.kafka)
    api(libs.starter.oauth2.resource.server)
    api(libs.starter.actuator)
    api(libs.micrometer.prometheus)
    api(libs.springdoc.webmvc)
    runtimeOnly(libs.postgresql)
}
