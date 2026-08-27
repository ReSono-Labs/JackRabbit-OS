#!/usr/bin/env bash
# Build the debug APK inside the pinned jackrabbit-apk-builder container.
#
# This is the recommended way to build on any host (especially macOS, because
# the project's reference build env is Linux): no local JDK / Android SDK /
# Gradle / Python needed, and the result matches CI exactly.
#
# Signing: the container mounts ~/.android/debug.keystore read-only. If that
# file is missing, a fresh local debug key is generated (with a warning: it
# will NOT upgrade over APKs signed with the shared JackRabbit key).
# See BUILDING.md -> "Debug signing" for the shared key.
#
# Usage:
#   ./android/scripts/build_apk_docker.sh
#
# Env overrides:
#   APK_BUILDER_IMAGE   image tag to use (default: ghcr.io/resono-labs/jackrabbit-apk-builder:latest)
#
set -euo pipefail

IMAGE="${APK_BUILDER_IMAGE:-ghcr.io/resono-labs/jackrabbit-apk-builder:latest}"
PROJECT_ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
KEYSTORE="$HOME/.android/debug.keystore"

if ! docker info >/dev/null 2>&1; then
    echo "Docker is not running. Start Docker Desktop and retry." >&2
    exit 1
fi

if [[ ! -f "$KEYSTORE" ]]; then
    KEYTOOL="$(command -v keytool || true)"
    if [[ -x "/Applications/Android Studio.app/Contents/jbr/Contents/Home/bin/keytool" ]]; then
        KEYTOOL="/Applications/Android Studio.app/Contents/jbr/Contents/Home/bin/keytool"
    fi
    # Some macOS installations ship a keytool stub that cannot actually run;
    # probe it and fall back to the container's JDK if broken.
    if [[ -n "$KEYTOOL" ]] && ! "$KEYTOOL" -help >/dev/null 2>&1; then
        echo "Host keytool at $KEYTOOL is not functional; will use the container's JDK." >&2
        KEYTOOL=""
    fi
    mkdir -p "$HOME/.android"
    echo "Generating a fresh local debug key at $KEYSTORE." >&2
    echo "WARNING: builds signed with this key will NOT upgrade over APKs signed with the shared JackRabbit key." >&2
    if [[ -n "$KEYTOOL" ]]; then
        "$KEYTOOL" -genkeypair -v -keystore "$KEYSTORE" -storepass android -keypass android \
            -alias androiddebugkey -keyalg RSA -keysize 2048 -validity 10000 \
            -dname "CN=Android Debug,O=Android,C=US"
        chmod 600 "$KEYSTORE"
    else
        # No host JDK/Android Studio: generate inside the builder container
        # (its JDK ships keytool). The key is created at runtime, never baked
        # into the image.
        docker run --rm -v "$HOME/.android":/root/.android "$IMAGE" sh -c \
            'keytool -genkeypair -v -keystore /root/.android/debug.keystore -storepass android \
             -keypass android -alias androiddebugkey -keyalg RSA -keysize 2048 -validity 10000 \
             -dname "CN=Android Debug,O=Android,C=US" && chmod 600 /root/.android/debug.keystore'
    fi
fi

mkdir -p "$HOME/.gradle"

cd "$PROJECT_ROOT"
echo "Building with $IMAGE ..."
# Only auto-pull registry images; local test tags (e.g. manually built
# android/Dockerfile) must be used as-is.
PULL_FLAG="--pull=always"
[[ "$IMAGE" != ghcr.io/* ]] && PULL_FLAG=""
docker run --rm $PULL_FLAG \
    -v "$HOME/.android":/root/.android:ro \
    -v "$HOME/.gradle":/root/.gradle \
    -v "$PROJECT_ROOT":/src -w /src \
    "$IMAGE" ./android/scripts/build_debug.sh

echo
echo "APK ready: $PROJECT_ROOT/android/app/build/outputs/apk/debug/app-debug.apk"
