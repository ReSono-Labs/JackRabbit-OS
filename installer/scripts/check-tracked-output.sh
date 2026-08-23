#!/usr/bin/env bash
set -euo pipefail

installer_root="$(cd "${1:-$(dirname "${BASH_SOURCE[0]}")/..}" && pwd -P)"
if ! repository_root="$(git -C "$installer_root" rev-parse --show-toplevel 2>/dev/null)"; then
  printf 'JR-TRACKED-OUTPUT-OK: isolated tree has no Git index\n'
  exit 0
fi

relative_installer="${installer_root#"$repository_root/"}"
tracked="$(git -C "$repository_root" ls-files -- "$relative_installer/dist" "$relative_installer/node_modules")"
if [[ -n "$tracked" ]]; then
  printf 'JR-TRACKED-OUTPUT: generated installer dependency/output is tracked:\n%s\n' "$tracked" >&2
  exit 1
fi

printf 'JR-TRACKED-OUTPUT-OK\n'
