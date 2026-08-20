plugins { id("com.android.application") }
android {
    namespace = "com.resonolabs.hardware"
    compileSdk = 36
    defaultConfig {
        applicationId = "com.resonolabs.hardware"
        minSdk = 31
        targetSdk = 36
        versionCode = 2
        versionName = "1.1-r1-physical-map"
    }
    compileOptions {
        sourceCompatibility = JavaVersion.VERSION_17
        targetCompatibility = JavaVersion.VERSION_17
    }
}
dependencies {
    implementation(project(":core:motor"))
    testImplementation("junit:junit:4.13.2")
}
