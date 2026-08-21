plugins { id("com.android.application") }

android {
    namespace = "com.resonolabs.voice"
    compileSdk = 36

    defaultConfig {
        applicationId = "com.resonolabs.voice"
        minSdk = 31
        targetSdk = 36
        ndk { abiFilters += listOf("arm64-v8a") }
        versionCode = 29
        versionName = "0.4.24-openai-settings-controls"
    }

    buildTypes {
        debug {
            applicationIdSuffix = ".engineering"
            versionNameSuffix = "-debug"
        }
        release {
            isMinifyEnabled = true
            proguardFiles(
                getDefaultProguardFile("proguard-android-optimize.txt"),
                "proguard-rules.pro",
            )
        }
    }

    compileOptions {
        sourceCompatibility = JavaVersion.VERSION_17
        targetCompatibility = JavaVersion.VERSION_17
    }
}

dependencies {
    implementation(project(":core:design"))
    implementation(project(":core:input"))
    implementation(project(":core:power"))
    implementation(project(":feature:settings"))
    implementation(project(":feature:voice"))
    implementation(project(":feature:cards"))
    implementation(project(":feature:camera"))
    implementation(project(":feature:background-run"))
    implementation(project(":core:motor"))
    implementation(project(":runtime-host"))
    testImplementation("junit:junit:4.13.2")
}
