// incident-service: incident lifecycle, business-hours SLA engine, escalation scheduler, auto-close, problem management.
plugins { id("esm.spring-service") }

dependencies {
    implementation(project(":libs:esm-directory-replica"))
}
