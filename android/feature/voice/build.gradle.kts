plugins { id("com.android.library") }

android {
    namespace = "com.resonolabs.feature.voice"
    compileSdk = 36

    defaultConfig { minSdk = 31 }

    compileOptions {
        sourceCompatibility = JavaVersion.VERSION_17
        targetCompatibility = JavaVersion.VERSION_17
    }
}

dependencies {
    implementation(project(":core:design"))
    implementation(project(":core:input"))
    implementation(project(":runtime-host"))
    implementation("io.github.webrtc-sdk:android:144.7559.09")
    implementation("com.squareup.okhttp3:okhttp:4.12.0")
    testImplementation("junit:junit:4.13.2")
}
