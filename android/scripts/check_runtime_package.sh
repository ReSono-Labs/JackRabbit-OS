#!/usr/bin/env bash
set -euo pipefail

ANDROID_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
APK="$ANDROID_ROOT/app/build/outputs/apk/debug/app-debug.apk"

if [[ ! -f "$APK" ]]; then
    echo "runtime APK not found: $APK" >&2
    exit 1
fi

CONTENTS="$(mktemp)"
CHECK_DIR="$(mktemp -d)"
trap 'rm -f "$CONTENTS"; rm -rf "$CHECK_DIR"' EXIT
unzip -l "$APK" > "$CONTENTS"

for required in \
    'lib/arm64-v8a/libpython3.13.so' \
    'lib/arm64-v8a/libsqlite3_' \
    'lib/arm64-v8a/libssl_' \
    'lib/arm64-v8a/libcrypto_' \
    'assets/chaquopy/app.imy' \
    'assets/management/index.html' \
    'assets/management/app.js' \
    'assets/management/management.css' \
    'assets/design/tokens.css' \
    'assets/design/base.css'; do
    if ! rg -q "$required" "$CONTENTS"; then
        echo "required embedded runtime asset missing: $required" >&2
        exit 1
    fi
done

if rg -q 'lib/(armeabi-v7a|x86|x86_64)/' "$CONTENTS"; then
    echo "unexpected non-arm64 native runtime found" >&2
    exit 1
fi

unzip -p "$APK" assets/chaquopy/requirements-common.imy \
    > "$CHECK_DIR/requirements-common.zip"
unzip -l "$CHECK_DIR/requirements-common.zip" \
    > "$CHECK_DIR/requirements-common.txt"

for required_extension in \
    'jiter/jiter.cpython-313-aarch64-linux-android.so' \
    'pydantic_core/_pydantic_core.cpython-313-aarch64-linux-android.so' \
    'rpds/rpds.cpython-313-aarch64-linux-android.so'; do
    if ! rg -Fq "$required_extension" "$CHECK_DIR/requirements-common.txt"; then
        echo "required Android Python extension missing: $required_extension" >&2
        exit 1
    fi
done

if rg -q 'aarch64-android-android' "$CHECK_DIR/requirements-common.txt"; then
    echo "invalid Android Python extension suffix packaged" >&2
    exit 1
fi

echo "embedded runtime package: OK"
