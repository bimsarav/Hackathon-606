// request-service: service catalogue, service requests, sequential cost-conditional approvals, fulfilment.
plugins { id("esm.spring-service") }

dependencies {
    implementation(project(":libs:esm-directory-replica"))
}
