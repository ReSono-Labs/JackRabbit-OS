#!/usr/bin/env bash
set -euo pipefail

# Rebuild the three native arm64 dependencies required by openai-agents on the
# R1. This script writes only to a temporary directory and this project's
# runtime-host/wheels directory.

ANDROID_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
OUTPUT_DIR="$ANDROID_ROOT/runtime-host/wheels"
WORK_DIR="$(mktemp -d)"
trap 'rm -rf "$WORK_DIR"' EXIT

: "${ANDROID_NDK_ROOT:?Set ANDROID_NDK_ROOT to Android NDK 27.3 or compatible}"
: "${RESONO_ANDROID_PYTHON_PREFIX:?Set to an Android CPython 3.13 arm64 prefix}"

HOST_PYTHON="${RESONO_BUILD_PYTHON:-python3.13}"
RUST_TOOLCHAIN="${RESONO_RUST_TOOLCHAIN:-1.88.0}"
TARGET="aarch64-linux-android"
API="31"
CLANG="$ANDROID_NDK_ROOT/toolchains/llvm/prebuilt/linux-x86_64/bin/aarch64-linux-android${API}-clang"

command -v curl >/dev/null
command -v rustup >/dev/null
"$HOST_PYTHON" -c 'import maturin, wheel' >/dev/null
[[ -x "$CLANG" ]]
[[ -f "$RESONO_ANDROID_PYTHON_PREFIX/lib/libpython3.13.so" ]]

cat > "$WORK_DIR/pyo3-cross.conf" <<EOF
implementation=CPython
version=3.13
shared=true
abi3=false
lib_name=python3.13
lib_dir=$RESONO_ANDROID_PYTHON_PREFIX/lib
executable=$HOST_PYTHON
pointer_width=64
build_flags=
suppress_build_script_link_lines=false
EOF

packages=(
    "jiter|0.16.0|jiter-0.16.0.tar.gz|https://files.pythonhosted.org/packages/source/j/jiter/jiter-0.16.0.tar.gz|7b24c3492c5f4f84a37946ad9cf504910cf6a782d6a4e0689b6673c5894b4a1c"
    "pydantic_core|2.41.4|pydantic_core-2.41.4.tar.gz|https://files.pythonhosted.org/packages/source/p/pydantic_core/pydantic_core-2.41.4.tar.gz|70e47929a9d4a1905a67e4b687d5946026390568a8e952b92824118063cee4d5"
    "rpds_py|0.25.1|rpds_py-0.25.1.tar.gz|https://files.pythonhosted.org/packages/source/r/rpds_py/rpds_py-0.25.1.tar.gz|8960b6dac09b62dac26e75d7e2c4a22efb835d827a7278c34f72b2b84fa160e3"
)

mkdir -p "$WORK_DIR/dist" "$OUTPUT_DIR"
for record in "${packages[@]}"; do
    IFS='|' read -r package version archive url expected_sha <<< "$record"
    curl --fail --location --silent --show-error "$url" -o "$WORK_DIR/$archive"
    echo "$expected_sha  $WORK_DIR/$archive" | sha256sum --check --status
    mkdir "$WORK_DIR/$package"
    tar -xzf "$WORK_DIR/$archive" -C "$WORK_DIR/$package" --strip-components=1
    (
        cd "$WORK_DIR/$package"
        PYO3_CONFIG_FILE="$WORK_DIR/pyo3-cross.conf" \
        CC_aarch64_linux_android="$CLANG" \
        AR_aarch64_linux_android="$ANDROID_NDK_ROOT/toolchains/llvm/prebuilt/linux-x86_64/bin/llvm-ar" \
        CARGO_TARGET_AARCH64_LINUX_ANDROID_LINKER="$CLANG" \
        RUSTUP_TOOLCHAIN="$RUST_TOOLCHAIN" \
        "$HOST_PYTHON" -m maturin build --release --target "$TARGET" \
            --compatibility off --out "$WORK_DIR/dist"
    )
done

# Maturin's Android platform name can leak into the CPython extension suffix.
# Android CPython 3.13 imports the standard aarch64-linux-android suffix.
for wheel_path in "$WORK_DIR"/dist/*.whl; do
    unpack_dir="$WORK_DIR/unpack-$(basename "$wheel_path" .whl)"
    "$HOST_PYTHON" -m wheel unpack "$wheel_path" --dest "$unpack_dir" >/dev/null
    package_dir="$(find "$unpack_dir" -mindepth 1 -maxdepth 1 -type d -print -quit)"
    while IFS= read -r extension; do
        mv "$extension" "${extension/aarch64-android-android/aarch64-linux-android}"
    done < <(find "$package_dir" -type f -name '*aarch64-android-android.so')
    "$HOST_PYTHON" -m wheel pack "$package_dir" --dest-dir "$OUTPUT_DIR" >/dev/null
done

sha256sum "$OUTPUT_DIR"/*.whl
