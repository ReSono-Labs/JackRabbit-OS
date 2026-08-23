#!/usr/bin/env bash
set -euo pipefail

installer_root="${1:?installer source root is required}"
destination="${2:?destination is required}"

source_paths=(
  README.md
  INSTALL.md
  TROUBLESHOOTING.md
  VERSION
  package.json
  package-lock.json
  vite.config.mjs
  contracts
  conformance
  cli/Cargo.lock
  cli/Cargo.toml
  cli/README.md
  cli/src
  deployment
  provenance
  linux-macos
  scripts
  tests
  web/README.md
  web/index.html
  web/public
  web/src
  web/tests
  windows
)

mkdir -p "$destination"
(
  cd "$installer_root"
  tar -cf - "${source_paths[@]}"
) | (
  cd "$destination"
  tar -xf -
)
