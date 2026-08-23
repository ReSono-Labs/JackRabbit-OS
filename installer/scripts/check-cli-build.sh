#!/usr/bin/env bash
set -euo pipefail

installer_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd -P)"
binary="$installer_root/cli/target/release/jackrabbit-installer-cli"
udev_rule="$installer_root/linux-macos/drivers/51-jackrabbit-r1.rules"

fail() {
  printf 'JR-CLI-BUILD-%s: %s\n' "$1" "$2" >&2
  exit 1
}

if [[ ! -x "$binary" ]]; then
  fail "MISSING" "release binary is absent or not executable: $binary"
fi

version="$($binary version)"
if [[ "$version" != "JackRabbit installer CLI 0.1.0-dev" ]]; then
  fail "VERSION" "unexpected version output: $version"
fi

help="$($binary --help)"
if [[ "$help" != *"install RELEASE_DIRECTORY"* || "$help" != *"prompt-based menu"* ]]; then
  fail "HELP" "help does not expose the guided install boundary"
fi

preparation="$(printf '\n\n\n\n' | "$binary" prepare)"
for expected in \
  "Request developer mode" \
  "Back up the R1" \
  "Prepare the hardware" \
  "Let JackRabbit enter FASTBOOT" \
  "DO THIS" \
  "EXPECTED" \
  "WARNING" \
  "sends only FASTBOOT at 115200 baud"
do
  if [[ "$preparation" != *"$expected"* ]]; then
    fail "PREPARE" "missing physical instruction: $expected"
  fi
done

install_error="$($binary install /definitely/absent 2>&1 || true)"
if [[ "$install_error" != *JR-CLI-RELEASE-MISSING:* ]]; then
  fail "INSTALL" "install did not verify the release before device access"
fi

for rejected in flash erase reboot fastboot repair restore; do
  if rejection="$($binary "$rejected" 2>&1)"; then
    fail "COMMAND" "unsupported command unexpectedly succeeded: $rejected"
  fi
  if [[ "$rejection" != JR-CLI-COMMAND:* ]]; then
    fail "COMMAND" "unsupported command did not return the stable error contract: $rejected"
  fi
done

digest="$(sha256sum "$binary" | cut -d ' ' -f 1)"
for identity in '0e8d.*2000' '0e8d.*201c' '18d1.*4ee0'; do
  if ! grep -E "$identity" "$udev_rule" >/dev/null; then fail "UDEV" "missing R1 USB identity: $identity"; fi
done
if rg -n 'finish-current-product|REHEARSAL|rehearsal' "$installer_root/cli" >/dev/null; then
  fail "DRIFT" "obsolete rehearsal or ADB finish route remains in the CLI"
fi
printf 'JR-CLI-BUILD-OK: linux development binary sha256=%s\n' "$digest"
