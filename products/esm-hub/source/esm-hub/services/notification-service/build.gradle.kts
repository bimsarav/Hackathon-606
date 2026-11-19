// notification-service: consumes domain events, keeps in-app notifications, sends email with retry and dead-letter.
plugins { id("esm.spring-service") }

dependencies {
    implementation(project(":libs:esm-directory-replica"))
    implementation(libs.starter.mail)
}
