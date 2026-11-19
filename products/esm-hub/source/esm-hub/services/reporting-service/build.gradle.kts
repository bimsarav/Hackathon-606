// reporting-service: CQRS read model built from the compacted state topics; company-scoped reports and CSV exports.
plugins { id("esm.spring-service") }

dependencies {
    implementation(project(":libs:esm-directory-replica"))
}
