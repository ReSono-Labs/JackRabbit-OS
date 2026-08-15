pluginManagement {
    repositories {
        google()
        mavenCentral()
        gradlePluginPortal()
    }
}

dependencyResolutionManagement {
    repositoriesMode.set(RepositoriesMode.FAIL_ON_PROJECT_REPOS)
    repositories {
        google()
        mavenCentral()
    }
}

rootProject.name = "ReSonoR1"
include(
    ":app",
    ":core:design",
    ":core:input",
    ":core:power",
    ":feature:settings",
    ":feature:voice",
    ":runtime-host",
)
