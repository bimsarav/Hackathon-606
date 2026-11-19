// asset-service: see docs/architecture/architecture.md.
plugins { id("esm.spring-service") }

dependencies {
    implementation(project(":libs:esm-directory-replica"))
}
