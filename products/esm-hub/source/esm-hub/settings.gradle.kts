rootProject.name = "esm-hub"

dependencyResolutionManagement {
    repositories { mavenCentral() }
}

include(
    "libs:esm-common",
    "libs:esm-test-support",
    "libs:esm-directory-replica",
    "services:directory-service",
    "services:incident-service",
    "services:request-service",
    "services:change-service",
    "services:asset-service",
    "services:knowledge-service",
    "services:notification-service",
    "services:audit-service",
    "services:reporting-service",
    "services:gateway",
)
