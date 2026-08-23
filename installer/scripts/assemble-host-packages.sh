#!/usr/bin/env bash
set -euo pipefail

installer_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd -P)"
native_root="${1:?downloaded native-artifact directory is required}"
release_root="${2:?verified release directory is required}"

native_root="$(cd "$native_root" && pwd -P)"
release_root="$(cd "$release_root" && pwd -P)"
platforms=(linux-x64 macos-x64 macos-arm64 windows-x64)

binary_for() {
  local platform="$1" suffix=""
  [[ "$platform" != windows-x64 ]] || suffix=".exe"
  printf '%s/jackrabbit-native-%s/jackrabbit-installer%s\n' "$native_root" "$platform" "$suffix"
}

for platform in "${platforms[@]}"; do
  binary="$(binary_for "$platform")"
  [[ -f "$binary" ]] || {
    printf 'JR-HOST-ASSEMBLY-BINARY: missing %s\n' "$binary" >&2
    exit 1
  }
done

node "$installer_root/scripts/verify-release-directory.mjs" "$release_root"

for platform in "${platforms[@]}"; do
  binary="$(binary_for "$platform")"
  [[ "$platform" == windows-x64 ]] || chmod +x "$binary"
  output="$installer_root/dist/packages/jackrabbit-${platform}-current-v0.1"
  if [[ -e "$output" ]]; then
    printf 'JR-HOST-ASSEMBLY-EXISTS: retaining %s for final comparison\n' "$output"
  else
    "$installer_root/scripts/stage-host-package.sh" "$platform" "$binary" "$release_root"
  fi
  packaged_binary="$output/bin/jackrabbit-installer"
  [[ "$platform" != windows-x64 ]] || packaged_binary="$packaged_binary.exe"
  cmp -s "$binary" "$packaged_binary" || {
    printf 'JR-HOST-ASSEMBLY-BINARY: %s does not contain the CI-native executable\n' "$output" >&2
    exit 1
  }
done

node "$installer_root/scripts/check-host-packages.mjs"
printf 'JR-HOST-ASSEMBLY-OK: four packages assembled and compared\n'
