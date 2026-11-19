// gateway: single entry point for /api/v1/** (Spring Cloud Gateway Server WebMVC). Routes are configuration only.
plugins {
    id("esm.java-library")
    id("org.springframework.boot")
}

dependencies {
    implementation(platform(libs.spring.cloud.bom))
    implementation("org.springframework.cloud:spring-cloud-starter-gateway-server-webmvc")
    implementation(libs.starter.actuator)
    implementation(libs.micrometer.prometheus)
}

tasks.named<org.springframework.boot.gradle.tasks.bundling.BootJar>("bootJar") { archiveFileName = "app.jar" }
