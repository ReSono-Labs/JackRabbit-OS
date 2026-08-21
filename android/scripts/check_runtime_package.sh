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
    'assets/management/background-agent.js' \
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

unzip -p "$APK" assets/chaquopy/app.imy > "$CHECK_DIR/runtime-source.zip"
unzip -l "$CHECK_DIR/runtime-source.zip" > "$CHECK_DIR/runtime-source.txt"
unzip -q "$CHECK_DIR/runtime-source.zip" -d "$CHECK_DIR/runtime-source"

RUNTIME_CHECK_PYTHON="${RESONO_BUILD_PYTHON:-/tmp/resono-python/cpython-3.13.2-linux-x86_64-gnu/bin/python3.13}"
if [[ ! -x "$RUNTIME_CHECK_PYTHON" ]]; then
    echo "Python 3.13 runtime package checker not found: $RUNTIME_CHECK_PYTHON" >&2
    exit 1
fi
PYTHONDONTWRITEBYTECODE=1 "$RUNTIME_CHECK_PYTHON" -m compileall -q \
    "$CHECK_DIR/runtime-source/resono_runtime"

for required_source in \
    'resono_runtime/plugins/bundled/resono-mail/plugin.json' \
    'resono_runtime/plugins/bundled/resono-mail/skills/voice-mail/SKILL.md' \
    'resono_runtime/standards/agent_plugins/plugin.schema.json' \
    'resono_runtime/standards/agent_plugins/mcp.schema.json'; do
    if ! rg -Fq "$required_source" "$CHECK_DIR/runtime-source.txt"; then
        echo "required Build 7 standard artifact missing: $required_source" >&2
        exit 1
    fi
done

for required_extension in \
    'jiter/jiter.cpython-313-aarch64-linux-android.so' \
    'pydantic_core/_pydantic_core.cpython-313-aarch64-linux-android.so' \
    'rpds/rpds.cpython-313-aarch64-linux-android.so' \
    'yaml/_yaml.so' \
    'chaquopy_libyaml-0.2.5.dist-info/License'; do
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
