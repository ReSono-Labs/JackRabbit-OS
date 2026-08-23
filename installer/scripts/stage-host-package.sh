#!/usr/bin/env bash
set -euo pipefail

installer_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd -P)"
platform="${1:?platform is required: linux-x64, macos-x64, macos-arm64, or windows-x64}"
cli_binary="${2:?compiled CLI binary is required}"
release_root="${3:?verified release directory is required}"
contract="$installer_root/images/HOST-DEPENDENCIES.json"

case "$platform" in
  linux-x64|macos-x64|macos-arm64|windows-x64) ;;
  *) printf 'JR-HOST-PACKAGE-PLATFORM: unsupported platform: %s\n' "$platform" >&2; exit 1 ;;
esac

[[ -f "$cli_binary" ]] || { printf 'JR-HOST-PACKAGE-CLI: missing binary: %s\n' "$cli_binary" >&2; exit 1; }
[[ -d "$release_root/images" ]] || { printf 'JR-HOST-PACKAGE-RELEASE: missing verified release images: %s\n' "$release_root" >&2; exit 1; }
node "$installer_root/scripts/verify-release-directory.mjs" "$release_root"

read_contract() {
  node -e 'const data=require(process.argv[1]); const value=process.argv[2].split(".").reduce((current,key)=>current[key],data); process.stdout.write(value)' "$contract" "$1"
}

cache_root="$installer_root/dist/dependency-cache"
bundle_root="$(cd "$release_root/.." && pwd -P)"
[[ "$(basename "$release_root")" == release ]] || { printf 'JR-HOST-PACKAGE-RELEASE: expected the shared bundle release directory: %s\n' "$release_root" >&2; exit 1; }
output_root="$bundle_root/hosts/$platform"
mkdir -p "$cache_root" "$bundle_root/hosts"
[[ ! -e "$output_root" ]] || { printf 'JR-HOST-PACKAGE-EXISTS: remove the existing package first: %s\n' "$output_root" >&2; exit 1; }
mkdir -p "$output_root/bin" "$output_root/tools" "$output_root/drivers"

fetch_exact() {
  local url="$1"
  local digest="$2"
  local destination="$cache_root/$digest.zip"
  if [[ ! -f "$destination" ]]; then
    curl -fL "$url" -o "$destination.part"
    mv "$destination.part" "$destination"
  fi
  printf '%s  %s\n' "$digest" "$destination" | sha256sum -c - >/dev/null
  printf '%s\n' "$destination"
}

tools_url="$(read_contract "platformTools.$platform.url")"
tools_hash="$(read_contract "platformTools.$platform.sha256")"
tools_archive="$(fetch_exact "$tools_url" "$tools_hash")"
temporary="$(mktemp -d)"
trap 'rm -rf "$temporary"' EXIT

unzip -q "$tools_archive" -d "$temporary/platform-tools"
case "$platform" in
  windows-x64)
    cp "$cli_binary" "$output_root/bin/jackrabbit-installer.exe"
    cp "$installer_root/windows/install.cmd" "$installer_root/windows/install.ps1" "$installer_root/windows/install-drivers.ps1" "$output_root/"
    cp "$temporary/platform-tools/platform-tools/fastboot.exe" "$output_root/tools/fastboot.exe"
    cp "$temporary/platform-tools/platform-tools/AdbWinApi.dll" "$temporary/platform-tools/platform-tools/AdbWinUsbApi.dll" "$temporary/platform-tools/platform-tools/libwinpthread-1.dll" "$output_root/tools/"
    cp "$temporary/platform-tools/platform-tools/NOTICE.txt" "$output_root/tools/PLATFORM-TOOLS-NOTICE.txt"

    mediatek_url="$(read_contract 'windowsDrivers.rabbitMediaTekPreloader.url')"
    mediatek_hash="$(read_contract 'windowsDrivers.rabbitMediaTekPreloader.sha256')"
    google_url="$(read_contract 'windowsDrivers.googleUsbDriver.url')"
    google_hash="$(read_contract 'windowsDrivers.googleUsbDriver.sha256')"
    mediatek_archive="$(fetch_exact "$mediatek_url" "$mediatek_hash")"
    google_archive="$(fetch_exact "$google_url" "$google_hash")"
    mkdir -p "$output_root/drivers/mediatek" "$output_root/drivers/google-usb-driver"
    unzip -q "$mediatek_archive" -d "$output_root/drivers/mediatek"
    unzip -q "$google_archive" -d "$output_root/drivers/google-usb-driver"
    ;;
  linux-x64)
    cp "$cli_binary" "$output_root/bin/jackrabbit-installer"
    cp "$installer_root/linux-macos/install.sh" "$output_root/install.sh"
    cp "$installer_root/linux-macos/drivers/51-jackrabbit-r1.rules" "$output_root/drivers/"
    cp "$temporary/platform-tools/platform-tools/fastboot" "$output_root/tools/fastboot"
    cp "$temporary/platform-tools/platform-tools/NOTICE.txt" "$output_root/tools/PLATFORM-TOOLS-NOTICE.txt"
    chmod +x "$output_root/install.sh" "$output_root/bin/jackrabbit-installer" "$output_root/tools/fastboot"
    ;;
  macos-x64|macos-arm64)
    cp "$cli_binary" "$output_root/bin/jackrabbit-installer"
    cp "$installer_root/linux-macos/install.sh" "$installer_root/linux-macos/install.command" "$output_root/"
    cp "$temporary/platform-tools/platform-tools/fastboot" "$output_root/tools/fastboot"
    cp "$temporary/platform-tools/platform-tools/NOTICE.txt" "$output_root/tools/PLATFORM-TOOLS-NOTICE.txt"
    chmod +x "$output_root/install.sh" "$output_root/install.command" "$output_root/bin/jackrabbit-installer" "$output_root/tools/fastboot"
    ;;
esac

cp "$installer_root/$([[ "$platform" == windows-x64 ]] && printf windows || printf linux-macos)/README.md" "$output_root/README.md"
cp "$installer_root/INSTALL.md" "$installer_root/TROUBLESHOOTING.md" "$output_root/"
cp "$contract" "$output_root/HOST-DEPENDENCIES.json"

printf 'JR-HOST-PACKAGE-OK: %s\n' "$output_root"
