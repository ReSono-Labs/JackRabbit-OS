#!/bin/sh
set -eu

package_root=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd -P)
installer_binary="$package_root/bin/jackrabbit-installer"
release_root="$package_root/release"
linux_rule="$package_root/drivers/51-jackrabbit-r1.rules"

fail() {
  printf 'JackRabbit installer: %s\n' "$1" >&2
  exit 1
}

incorrect_then_retry_or_cancel() {
  printf '\nENTRY INCORRECT. WOULD YOU LIKE TO CANCEL?\n'
  while :; do
    printf 'Type Y to cancel, or press Enter to return to the same prompt: '
    IFS= read -r cancel_answer
    case "$cancel_answer" in
      y|Y|yes|YES|Yes) fail 'cancelled by user' ;;
      ''|n|N|no|NO|No) return ;;
      *) printf 'Please type Y to cancel, or press Enter to retry.\n' ;;
    esac
  done
}

install_linux_rule() {
  target=/etc/udev/rules.d/51-jackrabbit-r1.rules
  if [ -f "$target" ] && cmp -s "$linux_rule" "$target"; then
    printf 'Linux R1 USB access is already configured.\n'
    return
  fi

  printf '\nLinux needs one administrator-approved USB setup before flashing.\n'
  printf 'This installs one narrow R1 udev rule. Flashing will not run as root.\n'
  while :; do
    printf 'Press Enter to configure R1 USB access, or type s to stop: '
    IFS= read -r answer
    case "$answer" in
      '') break ;;
      s|S) fail 'stopped before host setup' ;;
      *) incorrect_then_retry_or_cancel ;;
    esac
  done

  if command -v sudo >/dev/null 2>&1; then
    sudo install -m 0644 "$linux_rule" "$target"
    sudo udevadm control --reload-rules
    sudo udevadm trigger --subsystem-match=usb
    sudo udevadm trigger --subsystem-match=tty
  elif command -v pkexec >/dev/null 2>&1; then
    pkexec install -m 0644 "$linux_rule" "$target"
    pkexec udevadm control --reload-rules
    pkexec udevadm trigger --subsystem-match=usb
    pkexec udevadm trigger --subsystem-match=tty
  else
    fail 'neither pkexec nor sudo is available to install the R1 udev rule'
  fi
  printf 'Linux R1 USB access is configured. Reconnect the R1 when prompted.\n'
}

[ -x "$installer_binary" ] || fail "missing installer binary: $installer_binary"
[ -d "$release_root/images" ] || fail "missing packaged release: $release_root"

case "$(uname -s)" in
  Linux)
    [ -f "$linux_rule" ] || fail "missing Linux USB rule: $linux_rule"
    install_linux_rule
    ;;
  Darwin)
    printf 'macOS requires no JackRabbit USB driver installation.\n'
    ;;
  *)
    fail 'this package supports Linux and macOS only'
    ;;
esac

exec "$installer_binary" install "$release_root"
