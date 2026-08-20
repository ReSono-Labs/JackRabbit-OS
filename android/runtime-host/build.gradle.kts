plugins {
    id("com.android.library")
    id("com.chaquo.python")
}

android {
    namespace = "com.resonolabs.runtime.host"
    compileSdk = 36

    defaultConfig {
        minSdk = 31
        ndk { abiFilters += listOf("arm64-v8a") }
    }

    compileOptions {
        sourceCompatibility = JavaVersion.VERSION_17
        targetCompatibility = JavaVersion.VERSION_17
    }
}

chaquopy {
    defaultConfig {
        version = "3.13"
        buildPython(
            providers.environmentVariable("RESONO_BUILD_PYTHON")
                .getOrElse("python3.13")
        )
        pip {
            install("wheels/jiter-0.16.0-cp313-cp313-android_31_arm64_v8a.whl")
            install("wheels/pydantic_core-2.41.4-cp313-cp313-android_31_arm64_v8a.whl")
            install("wheels/rpds_py-0.25.1-cp313-cp313-android_31_arm64_v8a.whl")
            install("pydantic==2.12.2")
            install("jsonschema==4.25.1")
            install("PyYAML==6.0.3")
            install("openai-agents==0.18.3")
        }
    }
    sourceSets.getByName("main") {
        setSrcDirs(listOf(rootProject.file("../runtime")))
    }
}
