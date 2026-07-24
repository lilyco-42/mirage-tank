import java.util.Properties

plugins {
    alias(libs.plugins.android.application)
    alias(libs.plugins.kotlin.compose)
}

android {
    namespace = "com.lilyco.timi"
    compileSdk = 35 // 建议使用稳定版本

    androidResources {
        localeFilters += listOf("zh", "en")
    }

    defaultConfig {
        applicationId = "com.lilyco.timi"
        minSdk = 24
        targetSdk = 35
        versionCode = 1
        versionName = "1.0"

        testInstrumentationRunner = "androidx.test.runner.AndroidJUnitRunner"

        ndk {
            // 合并所有架构到同一个 APK
            abiFilters.addAll(listOf("arm64-v8a", "armeabi-v7a"))
        }
    }

    buildTypes {
        release {
            isMinifyEnabled = true // 开启 R8 混淆和压缩
            isShrinkResources = true
            proguardFiles(getDefaultProguardFile("proguard-android-optimize.txt"), "proguard-rules.pro")
            
            signingConfig = signingConfigs.getByName("debug") // 演示用途，正式需换正式签名
        }
        
        debug {
            // Debug 模式下禁用压缩以加快速度
            isMinifyEnabled = false
        }
    }
    
    compileOptions {
        sourceCompatibility = JavaVersion.VERSION_11
        targetCompatibility = JavaVersion.VERSION_11
    }
    
    buildFeatures {
        compose = true
    }

    packaging {
        jniLibs {
            useLegacyPackaging = true
        }
    }

    // 自动关联 Rust 编译
    sourceSets {
        getByName("main") {
            jniLibs.directories.add("src/main/jniLibs")
        }
    }
}

// === 自动化 Rust 编译任务 (类似 Bevy/Rust 惯用法) ===
tasks.register<Exec>("cargoBuild") {
    group = "build"
    description = "编译 Rust 库并将其输出到 jniLibs 目录"

    val isRelease = gradle.startParameter.taskNames.any { it.contains("Release", ignoreCase = true) }
    
    workingDir = file("../demo")
    
    // 获取环境变量中的 NDK 路径
    val properties = Properties()
    val localProperties = rootProject.file("local.properties")
    if (localProperties.exists()) {
        localProperties.inputStream().use { properties.load(it) }
    }
    val ndkDir = properties.getProperty("ndk.dir") ?: System.getenv("ANDROID_NDK_HOME")
    
    environment("ANDROID_NDK_HOME", ndkDir)
    
    // 执行 cargo ndk 编译
    val command = mutableListOf("cargo", "ndk")
    command.addAll(listOf("-t", "arm64-v8a", "-t", "armeabi-v7a"))
    command.addAll(listOf("-o", "../app/src/main/jniLibs"))
    command.add("build")
    if (isRelease) {
        command.add("--release")
    }
    
    commandLine(command)
}

// 挂载到 Android 预编译阶段
tasks.whenTaskAdded {
    if (name.startsWith("merge") && name.endsWith("JniLibFolders")) {
        dependsOn("cargoBuild")
    }
}

dependencies {
    implementation(platform(libs.androidx.compose.bom))
    implementation(libs.androidx.activity.compose)
    implementation(libs.androidx.compose.material3)
    implementation(libs.androidx.compose.ui)
    implementation(libs.androidx.compose.ui.graphics)
    debugImplementation(libs.androidx.compose.ui.tooling.preview)
    implementation(libs.androidx.core.ktx)
    implementation(libs.androidx.lifecycle.runtime.ktx)
    testImplementation(libs.junit)
    androidTestImplementation(platform(libs.androidx.compose.bom))
    androidTestImplementation(libs.androidx.compose.ui.test.junit4)
    androidTestImplementation(libs.androidx.espresso.core)
    androidTestImplementation(libs.androidx.junit)
    debugImplementation(libs.androidx.compose.ui.test.manifest)
    debugImplementation(libs.androidx.compose.ui.tooling)
}