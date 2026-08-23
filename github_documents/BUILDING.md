# Build the JackRabbit APK

JackRabbit is built as one Android APK containing the native Rabbit R1 interface, the embedded Python runtime, and the local management website.

## Source directories

- `android/` contains the Android application, native R1 interface, device integration, and APK packaging.
- `runtime/` contains the embedded Python runtime, agents, tools, storage, and domain services.
- `web/` contains the management interface embedded into the APK.

All three directories are required to build the complete application.

## Requirements

- Linux development environment
- JDK 17
- Android SDK with API 36 and Build Tools 36.0.0
- Android NDK and platform tools available to the Android build
- A local `android/local.properties` pointing to the Android SDK

Do not commit SDK paths, signing keys, API keys, OAuth tokens, certificates, or device credentials.

## Build

From the repository root, run:

```bash
./android/scripts/build_debug.sh
```

The project build performs the Android build and verifies the standalone module and embedded-runtime package boundaries.

The resulting development APK is written to:

```text
android/app/build/outputs/apk/debug/app-debug.apk
```

The application version is controlled by:

```text
android/app-version.properties
```

Increase `VERSION_CODE` for every new installable build. Keep `VERSION_NAME` under the current Carrot1 release identity until the project owner changes it.

## Local toolchain override

The project build script uses the repository's configured Android toolchain. If the local Gradle native runtime must be initialized explicitly, use JDK 17 and then rerun the authoritative build:

```bash
JAVA_HOME=/tmp/r1-jdk17 \
PATH=/tmp/r1-jdk17/bin:/tmp/r1-android-sdk/platform-tools:$PATH \
/tmp/gradle-9.5.0/bin/gradle --no-daemon --version

./android/scripts/build_debug.sh
```

The `/tmp` paths above are examples from the reference development environment. Contributors may use equivalent local JDK, Gradle, Android SDK, and platform-tools locations.

## Generated files

Do not commit generated APKs, Android build directories, Gradle caches, local SDK configuration, credentials, or logical device images. Release binaries and installer images are published separately from the application source.
