plugins {
    id("com.android.application")
    id("org.jetbrains.kotlin.android")
    id("org.jetbrains.kotlin.plugin.compose")
}

android {
    namespace = "com.velo.vpn"
    compileSdk = 35

    defaultConfig {
        applicationId = "com.velo.vpn"
        minSdk = 26
        targetSdk = 35
        versionCode = 7
        versionName = "0.7.0"

        testInstrumentationRunner = "androidx.test.runner.AndroidJUnitRunner"
        vectorDrawables.useSupportLibrary = true

        val apiBaseUrl = (project.findProperty("VELO_API_BASE_URL") as String?)
            ?: "http://10.0.2.2:8000/"
        val tapsellAppKey = (project.findProperty("VELO_TAPSELL_APP_KEY") as String?)
            ?: "00000000-0000-0000-0000-000000000000"
        val supportEmail = (project.findProperty("VELO_SUPPORT_EMAIL") as String?) ?: "support@example.com"
        val releaseRequested = gradle.startParameter.taskNames.any { it.contains("release", ignoreCase = true) }
        if (releaseRequested && !apiBaseUrl.startsWith("https://")) {
            error("Release builds require -PVELO_API_BASE_URL=https://...")
        }
        if (releaseRequested && tapsellAppKey == "00000000-0000-0000-0000-000000000000") {
            error("Release builds require -PVELO_TAPSELL_APP_KEY=<real key>")
        }
        buildConfigField("String", "API_BASE_URL", "\"$apiBaseUrl\"")
        buildConfigField("String", "TAPSELL_APP_KEY", "\"$tapsellAppKey\"")
        buildConfigField("String", "PRIVACY_URL", "\"${apiBaseUrl}legal/privacy\"")
        buildConfigField("String", "TERMS_URL", "\"${apiBaseUrl}legal/terms\"")
        buildConfigField("String", "SUPPORT_EMAIL", "\"$supportEmail\"")
        manifestPlaceholders["usesCleartextTraffic"] = apiBaseUrl.startsWith("http://").toString()
        manifestPlaceholders["TapsellMediationAppKey"] = tapsellAppKey
    }

    buildFeatures {
        compose = true
        buildConfig = true
    }

    compileOptions {
        sourceCompatibility = JavaVersion.VERSION_17
        targetCompatibility = JavaVersion.VERSION_17
        isCoreLibraryDesugaringEnabled = true
    }
    kotlinOptions { jvmTarget = "17" }

    packaging {
        resources.excludes += "/META-INF/{AL2.0,LGPL2.1}"
    }
}

dependencies {
    implementation("androidx.core:core-ktx:1.15.0")
    implementation("androidx.lifecycle:lifecycle-runtime-ktx:2.8.7")
    implementation("androidx.lifecycle:lifecycle-viewmodel-compose:2.8.7")
    implementation("androidx.activity:activity-compose:1.10.0")
    implementation("androidx.datastore:datastore-preferences:1.1.1")
    implementation("com.android.installreferrer:installreferrer:2.2")

    implementation(platform("androidx.compose:compose-bom:2024.12.01"))
    implementation("androidx.compose.ui:ui")
    implementation("androidx.compose.ui:ui-tooling-preview")
    implementation("androidx.compose.foundation:foundation")
    implementation("androidx.compose.material3:material3")
    implementation("androidx.compose.material:material-icons-extended")
    implementation("androidx.navigation:navigation-compose:2.8.5")

    implementation("com.squareup.retrofit2:retrofit:2.11.0")
    implementation("com.squareup.retrofit2:converter-gson:2.11.0")
    implementation("com.squareup.okhttp3:logging-interceptor:4.12.0")
    implementation("org.jetbrains.kotlinx:kotlinx-coroutines-android:1.9.0")

    // Official WireGuard embeddable Android tunnel library.
    implementation("com.wireguard.android:tunnel:1.0.20260102")
    coreLibraryDesugaring("com.android.tools:desugar_jdk_libs:2.0.3")

    // Tapsell Mediation stable SDK. App key is a manifest/build property; rewarded zone id stays remote-configured.
    implementation("ir.tapsell:tapsell:1.2.0")

    debugImplementation("androidx.compose.ui:ui-tooling")
}
