plugins { id("com.android.library") }
android {
    namespace = "com.resonolabs.feature.camera"
    compileSdk = 36
    defaultConfig { minSdk = 31 }
    compileOptions { sourceCompatibility = JavaVersion.VERSION_17; targetCompatibility = JavaVersion.VERSION_17 }
}
dependencies {
    implementation(project(":core:motor"))
    implementation(project(":core:design"))
    implementation(project(":feature:voice"))
    testImplementation("junit:junit:4.13.2")
}
