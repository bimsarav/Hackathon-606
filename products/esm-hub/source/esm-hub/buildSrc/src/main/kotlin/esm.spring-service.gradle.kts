// Convention for a deployable Spring Boot microservice: esm-common, Boot plugin, and an integrationTest suite
// (src/integrationTest/java) using esm-test-support. `check` runs unit and integration tests.
plugins {
    id("esm.java-library")
    id("org.springframework.boot")
}

val catalog = the<VersionCatalogsExtension>().named("libs")
fun lib(alias: String) = catalog.findLibrary(alias).get()

dependencies {
    implementation(project(":libs:esm-common"))
    testImplementation(project(":libs:esm-test-support"))
}

testing {
    suites {
        register<JvmTestSuite>("integrationTest") {
            useJUnitJupiter()
            dependencies {
                implementation(project())
                implementation(platform(lib("spring-boot-bom")))
                implementation(project(":libs:esm-test-support"))
            }
            targets.all {
                testTask.configure {
                    shouldRunAfter(tasks.named("test"))
                    systemProperty("spring.profiles.active", "test")
                }
            }
        }
    }
}

configurations.named("integrationTestImplementation") { extendsFrom(configurations.implementation.get()) }
configurations.named("integrationTestRuntimeOnly") { extendsFrom(configurations.runtimeOnly.get()) }

tasks.named("check") { dependsOn(testing.suites.named("integrationTest")) }

tasks.named<org.springframework.boot.gradle.tasks.bundling.BootJar>("bootJar") { archiveFileName = "app.jar" }
