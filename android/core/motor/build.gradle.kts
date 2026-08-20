plugins { id("com.android.library") }
android {
    namespace = "com.resonolabs.hardware.motor"
    compileSdk = 36
    defaultConfig { minSdk = 31 }
    buildFeatures { aidl = true }
    compileOptions {
        sourceCompatibility = JavaVersion.VERSION_17
        targetCompatibility = JavaVersion.VERSION_17
    }
}
