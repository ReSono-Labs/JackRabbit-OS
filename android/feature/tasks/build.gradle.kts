plugins { id("com.android.library") }
android {
    namespace = "com.resonolabs.feature.tasks"
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
}
