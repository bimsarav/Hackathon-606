// Convention for every Java module: Java 27 toolchain, Spring Boot BOM, JUnit 5, JaCoCo.
plugins {
    `java-library`
    jacoco
}

val catalog = the<VersionCatalogsExtension>().named("libs")
fun lib(alias: String) = catalog.findLibrary(alias).get()

java {
    toolchain { languageVersion = JavaLanguageVersion.of(catalog.findVersion("java").get().requiredVersion.toInt()) }
}

dependencies {
    val bom = platform(lib("spring-boot-bom"))
    api(bom)
    annotationProcessor(bom)
    testImplementation(bom)
    testImplementation(lib("starter-test"))
    testRuntimeOnly(lib("junit-launcher"))
}

tasks.withType<JavaCompile>().configureEach {
    options.encoding = "UTF-8"
    options.compilerArgs.addAll(listOf("-parameters", "-Xlint:deprecation"))
}

tasks.withType<Test>().configureEach {
    useJUnitPlatform()
    testLogging { events("failed"); exceptionFormat = org.gradle.api.tasks.testing.logging.TestExceptionFormat.SHORT }
}

tasks.named<JacocoReport>("jacocoTestReport") { reports { xml.required = true; html.required = true } }
