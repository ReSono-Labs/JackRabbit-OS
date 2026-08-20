#!/usr/bin/env bash
set -euo pipefail

if [[ $# -ne 2 ]]; then
  echo "usage: $0 /path/to/platform.pk8 /path/to/platform.x509.pem" >&2
  exit 2
fi

project_root="$(cd "$(dirname "$0")/../.." && pwd)"
android_root="$project_root/android"
sdk_root="${ANDROID_SDK_ROOT:-${ANDROID_HOME:-/tmp/r1-android-sdk}}"
java_home="${JAVA_HOME:-/tmp/r1-jdk17}"
apksigner="$sdk_root/build-tools/36.0.0/apksigner"
unsigned="$android_root/system/motor-service/build/outputs/apk/debug/motor-service-debug.apk"
output="$android_root/system/motor-service/build/outputs/apk/debug/motor-service-r1-platform.apk"
expected="c8a2e9bccf597c2fb6dc66bee293fc13f2fc47ec77bc6b2b0d52c11f51192ab8"

JAVA_HOME="$java_home" PATH="$java_home/bin:$PATH" \
  "$apksigner" sign --key "$1" --cert "$2" --out "$output" "$unsigned"

actual="$(JAVA_HOME="$java_home" PATH="$java_home/bin:$PATH" \
  "$apksigner" verify --print-certs "$output" \
  | sed -n 's/^Signer #1 certificate SHA-256 digest: //p')"
if [[ "$actual" != "$expected" ]]; then
  rm -f "$output"
  echo "platform certificate mismatch: expected $expected, got $actual" >&2
  exit 1
fi

echo "$output"
