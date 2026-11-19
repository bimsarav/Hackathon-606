// Local read replica of directory data (users, teams, services, offices) kept in sync from the compacted
// directory.* Kafka topics. Include in services that need directory data; add classpath:db/directory to Flyway.
plugins { id("esm.java-library") }

dependencies {
    api(project(":libs:esm-common"))
}
