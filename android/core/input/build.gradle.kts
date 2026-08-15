plugins { id("com.android.library") }

android {
    namespace = "com.resonolabs.ui.input"
    compileSdk = 36
    defaultConfig { minSdk = 31 }
    compileOptions {
        sourceCompatibility = JavaVersion.VERSION_17
        targetCompatibility = JavaVersion.VERSION_17
    }
}

dependencies { testImplementation("junit:junit:4.13.2") }
