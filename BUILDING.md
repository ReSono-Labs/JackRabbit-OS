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

## Docker build (recommended)

No local Linux toolchain required: the pinned builder image
(`ghcr.io/resono-labs/jackrabbit-apk-builder`, built from `android/Dockerfile`)
contains the exact JDK 17 / Android SDK 36 / Gradle 9.5.0 / CPython 3.13.2
environment CI uses, in the layout `build_debug.sh` expects. It works on
macOS and Windows (Docker Desktop) and produces the same APK as CI.

Requirements:

- Docker (Docker Desktop on macOS)

From the repository root, run:

```bash
./android/scripts/build_apk_docker.sh
```

The result is written to the same location as a native build:

```text
android/app/build/outputs/apk/debug/app-debug.apk
```

The script mounts your `~/.android/debug.keystore` into the container
read-only and shares `~/.gradle` so dependency downloads are cached between
runs. Override the image tag with `APK_BUILDER_IMAGE`.

### Debug signing

The debug APK is signed with the `sharedDebug` signing config in
`android/app/build.gradle.kts`, which reads `~/.android/debug.keystore`
(alias `androiddebugkey`, store password `android`).

- **CI**: the key is stored as the `ANDROID_DEBUG_KEYSTORE_BASE64` repository
  secret on GitHub. The workflow decodes it onto the runner, then the builder
  container mounts it read-only. The key is never committed (`.gitignore`
  covers `*.keystore`) and is never baked into the Docker image.
- **Local**: place the shared key at `~/.android/debug.keystore` so test
  installs upgrade cleanly over previous builds. Without it,
  `build_apk_docker.sh` generates a fresh local key and warns that builds
  signed with it will not upgrade over shared-key builds.
- The shared key itself is a development convenience, not a release secret.
  Release signing (e.g. Play App Signing) is a separate, more restricted flow.

### Updating the builder image

Toolchain versions are pinned as `ARG`s at the top of `android/Dockerfile`.
After bumping one, publish a new image and point the build at it:

1. Push the change (or run the workflow directly), then run the
   **Publish APK builder image** workflow from any branch
   (`workflow_dispatch`) — it builds `android/Dockerfile` for
   `linux/amd64` and pushes `ghcr.io/resono-labs/jackrabbit-apk-builder:v1`
   (bump to `v2` for a breaking toolchain change).
2. Update `APK_BUILDER_IMAGE` in `.github/workflows/apk-build.yml` to the new
   immutable tag.
3. Local builds pull `latest` by default, so they pick up the new image
   automatically.

## Build (native Linux)

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
