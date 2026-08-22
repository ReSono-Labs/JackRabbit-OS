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
  VERSION
  package.json
  package-lock.json
  contracts/README.md
  conformance/README.md
  web/README.md
  cli/README.md
  deployment/README.md
  provenance/README.md
  provenance/sources.json
  provenance/browser-apis.md
  scripts/check-boundaries.sh
  scripts/check-provenance.mjs
  tests/test-boundaries.sh
)

for required_file in "${required_files[@]}"; do
  if [[ ! -f "$installer_root/$required_file" ]]; then
    fail "REQUIRED" "missing required installer-owned file: $required_file"
  fi
done

first_symlink="$(find "$installer_root" -type l -print -quit)"
if [[ -n "$first_symlink" ]]; then
  fail "SYMLINK" "symlinks are not permitted in installer source: ${first_symlink#"$installer_root/"}"
fi

first_nested_git="$(find "$installer_root" -mindepth 1 -name .git -print -quit)"
if [[ -n "$first_nested_git" ]]; then
  fail "NESTED-GIT" "nested Git metadata is not permitted: ${first_nested_git#"$installer_root/"}"
fi

if [[ -d "$installer_root/dist" ]]; then
  first_dist_file="$(find "$installer_root/dist" -type f -print -quit)"
  if [[ -n "$first_dist_file" ]]; then
    fail "DIST" "generated output must not be present in the source boundary: ${first_dist_file#"$installer_root/"}"
  fi
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
done < <(find "$installer_root" -type f \( \
  -name '*.cjs' -o -name '*.go' -o -name '*.js' -o -name '*.json' -o \
  -name '*.jsx' -o -name '*.mjs' -o -name '*.rs' -o -name '*.sh' -o \
  -name '*.toml' -o -name '*.ts' -o -name '*.tsx' -o -name '*.yaml' -o \
  -name '*.yml' \
\) -print0)

printf 'JR-BOUNDARY-OK: %s\n' "$installer_root"
