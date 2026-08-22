#!/usr/bin/env bash
set -euo pipefail

installer_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd -P)"
checker="$installer_root/scripts/check-boundaries.sh"
scratch_root="$(mktemp -d)"
trap 'rm -rf -- "$scratch_root"' EXIT

pass_count=0

expect_pass() {
  local name="$1"
  local fixture="$2"
  if ! bash "$fixture/scripts/check-boundaries.sh" "$fixture" >/dev/null; then
    printf 'not ok - %s\n' "$name" >&2
    exit 1
  fi
  pass_count=$((pass_count + 1))
  printf 'ok - %s\n' "$name"
}

expect_fail() {
  local name="$1"
  local fixture="$2"
  local expected_code="$3"
  local output
  if output="$(bash "$fixture/scripts/check-boundaries.sh" "$fixture" 2>&1)"; then
    printf 'not ok - %s (unexpected pass)\n' "$name" >&2
    exit 1
  fi
  if [[ "$output" != *"JR-BOUNDARY-$expected_code:"* ]]; then
    printf 'not ok - %s (wrong failure: %s)\n' "$name" "$output" >&2
    exit 1
  fi
  pass_count=$((pass_count + 1))
  printf 'ok - %s\n' "$name"
}

new_fixture() {
  local name="$1"
  local fixture="$scratch_root/$name/installer"
  mkdir -p "$scratch_root/$name"
  cp -R "$installer_root" "$fixture"
  printf '%s\n' "$fixture"
}

expect_pass "repository scaffold" "$installer_root"
node "$installer_root/scripts/check-provenance.mjs" "$installer_root" >/dev/null
pass_count=$((pass_count + 1))
printf 'ok - pinned provenance ledger\n'

isolated_fixture="$(new_fixture isolated)"
expect_pass "isolated installer copy" "$isolated_fixture"

missing_fixture="$(new_fixture missing-required)"
rm -- "$missing_fixture/contracts/README.md"
expect_fail "missing ownership file" "$missing_fixture" "REQUIRED"

symlink_fixture="$(new_fixture symlink-escape)"
ln -s /tmp "$symlink_fixture/web/escape"
expect_fail "symlink escape" "$symlink_fixture" "SYMLINK"

parent_fixture="$(new_fixture parent-reference)"
mkdir -p "$parent_fixture/web/src"
printf '%s\n' 'import value from "../../../runtime/example";' > "$parent_fixture/web/src/escape.ts"
expect_fail "forbidden parent reference" "$parent_fixture" "PARENT-REFERENCE"

absolute_fixture="$(new_fixture absolute-reference)"
mkdir -p "$absolute_fixture/cli/src"
printf '%s\n' 'const fixture = "/home/example/project/release.json";' > "$absolute_fixture/cli/src/absolute.ts"
expect_fail "workspace-specific absolute reference" "$absolute_fixture" "ABSOLUTE-REFERENCE"

dependency_fixture="$(new_fixture local-dependency)"
printf '%s\n' '{"dependencies":{"product":"file:../product"}}' > "$dependency_fixture/web/package.json"
expect_fail "parent-local dependency" "$dependency_fixture" "LOCAL-DEPENDENCY"

provenance_fixture="$(new_fixture changed-provenance)"
sed -i 's/5b613332aa9d66cca5bebb49f147cd084a76c464/0000000000000000000000000000000000000000/' "$provenance_fixture/provenance/sources.json"
if output="$(node "$provenance_fixture/scripts/check-provenance.mjs" "$provenance_fixture" 2>&1)"; then
  printf 'not ok - changed dependency pin (unexpected pass)\n' >&2
  exit 1
fi
if [[ "$output" != *"JR-PROVENANCE-FASTBOOT-PIN:"* ]]; then
  printf 'not ok - changed dependency pin (wrong failure: %s)\n' "$output" >&2
  exit 1
fi
pass_count=$((pass_count + 1))
printf 'ok - changed dependency pin\n'

git_fixture="$(new_fixture nested-git)"
mkdir -p "$git_fixture/web/.git"
expect_fail "nested Git metadata" "$git_fixture" "NESTED-GIT"

dist_fixture="$(new_fixture generated-dist)"
mkdir -p "$dist_fixture/dist"
printf '%s\n' 'generated' > "$dist_fixture/dist/output.bin"
expect_fail "generated output in source" "$dist_fixture" "DIST"

wrong_root="$scratch_root/not-installer"
mkdir -p "$wrong_root"
if output="$(bash "$checker" "$wrong_root" 2>&1)"; then
  printf 'not ok - wrong root (unexpected pass)\n' >&2
  exit 1
fi
if [[ "$output" != *"JR-BOUNDARY-ROOT:"* ]]; then
  printf 'not ok - wrong root (wrong failure: %s)\n' "$output" >&2
  exit 1
fi
pass_count=$((pass_count + 1))
printf 'ok - wrong root\n'

printf '1..%s\n' "$pass_count"
