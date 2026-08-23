#!/usr/bin/env bash
set -euo pipefail

installer_root="${1:-$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd -P)}"

fail() {
  printf 'JR-BOUNDARY-%s: %s\n' "$1" "$2" >&2
  exit 1
}

if [[ ! -d "$installer_root" ]]; then
  fail "ROOT" "installer root does not exist: $installer_root"
fi

installer_root="$(cd "$installer_root" && pwd -P)"
if [[ "${installer_root##*/}" != "installer" ]]; then
  fail "ROOT" "expected a directory named installer: $installer_root"
fi

required_files=(
  README.md
  INSTALL.md
  TROUBLESHOOTING.md
  VERSION
  package.json
  package-lock.json
  contracts/README.md
  contracts/current-release-v0.2.json
  contracts/errors-v1.json
  contracts/host-dependencies-v1.json
  contracts/journal-v1.schema.json
  contracts/operations-v1.schema.json
  contracts/preparation-prompts-v1.json
  contracts/prompts-v1.schema.json
  contracts/recovery-v1.schema.json
  contracts/release-v1.schema.json
  contracts/signature-v1.schema.json
  contracts/support-v1.json
  conformance/README.md
  conformance/update-plan-valid-v1.json
  cli/README.md
  cli/Cargo.lock
  cli/Cargo.toml
  cli/src/main.rs
  cli/src/command.rs
  cli/src/diagnose.rs
  cli/src/fastboot.rs
  cli/src/install.rs
  cli/src/physical.rs
  cli/src/preloader.rs
  cli/src/prompt.rs
  cli/src/release.rs
  linux-macos/README.md
  linux-macos/install.sh
  linux-macos/install.command
  linux-macos/drivers/51-jackrabbit-r1.rules
  windows/README.md
  windows/install.cmd
  windows/install.ps1
  windows/install-drivers.ps1
  deployment/README.md
  deployment/ci.md
  provenance/README.md
  provenance/sources.json
  provenance/browser-apis.md
  provenance/cli-usb-transport.md
  provenance/stock-flash-route.md
  scripts/check-boundaries.sh
  scripts/copy-source-tree.sh
  scripts/check-cli-build.sh
  scripts/check-host-packages.mjs
  scripts/check-provenance.mjs
  scripts/check-tracked-output.sh
  scripts/assemble-host-packages.sh
  scripts/stage-host-package.sh
  scripts/verify-release-directory.mjs
  tests/test-boundaries.sh
  tests/test-isolated-build.sh
)

for required_file in "${required_files[@]}"; do
  if [[ ! -f "$installer_root/$required_file" ]]; then
    fail "REQUIRED" "missing required installer-owned file: $required_file"
  fi
done

first_symlink="$(find "$installer_root" \( -path "$installer_root/node_modules" -o -path "$installer_root/cli/target" -o -path "$installer_root/dist" \) -prune -o -type l -print -quit)"
if [[ -n "$first_symlink" ]]; then
  fail "SYMLINK" "symlinks are not permitted in installer source: ${first_symlink#"$installer_root/"}"
fi

first_nested_git="$(find "$installer_root" \( -path "$installer_root/node_modules" -o -path "$installer_root/cli/target" -o -path "$installer_root/dist" \) -prune -o -mindepth 1 -name .git -print -quit)"
if [[ -n "$first_nested_git" ]]; then
  fail "NESTED-GIT" "nested Git metadata is not permitted: ${first_nested_git#"$installer_root/"}"
fi

forbidden_parent="(\\.\\./)+(android|runtime|web|image|artifacts|reference|docs/planning|docs/reviews|docs/evidence|\\.agents|\\.codex)(/|[[:space:]\"']|$)"
forbidden_absolute='(/home/|/Users/|[A-Za-z]:\\Users\\)'
forbidden_local_dependency="(file:|path[[:space:]]*=[[:space:]]*[\"'])(\\.\\./)"

while IFS= read -r -d '' source_file; do
  relative_file="${source_file#"$installer_root/"}"
  case "$relative_file" in
    README.md|*/README.md|scripts/check-boundaries.sh|tests/test-boundaries.sh)
      continue
      ;;
  esac

  if LC_ALL=C grep -nE "$forbidden_parent" "$source_file" >/dev/null; then
    fail "PARENT-REFERENCE" "forbidden product/internal parent reference in $relative_file"
  fi
  if LC_ALL=C grep -nE "$forbidden_absolute" "$source_file" >/dev/null; then
    fail "ABSOLUTE-REFERENCE" "workspace-specific absolute reference in $relative_file"
  fi
  if LC_ALL=C grep -nE "$forbidden_local_dependency" "$source_file" >/dev/null; then
    fail "LOCAL-DEPENDENCY" "parent-local dependency in $relative_file"
  fi
done < <(find "$installer_root" \( -path "$installer_root/node_modules" -o -path "$installer_root/cli/target" -o -path "$installer_root/dist" \) -prune -o -type f \( \
  -name '*.cjs' -o -name '*.go' -o -name '*.js' -o -name '*.json' -o \
  -name '*.jsx' -o -name '*.mjs' -o -name '*.rs' -o -name '*.sh' -o \
  -name '*.toml' -o -name '*.ts' -o -name '*.tsx' -o -name '*.yaml' -o \
  -name '*.yml' \
\) -print0)

printf 'JR-BOUNDARY-OK: %s\n' "$installer_root"
