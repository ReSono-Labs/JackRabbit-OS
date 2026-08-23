#!/usr/bin/env bash
set -euo pipefail

installer_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd -P)"
scratch_root="$(mktemp -d)"
isolated_root="$scratch_root/installer"
trap 'rm -rf -- "$scratch_root"' EXIT

bash "$installer_root/scripts/copy-source-tree.sh" "$installer_root" "$isolated_root"

(
  cd "$isolated_root"
  npm ci --ignore-scripts --no-audit --no-fund
  bash scripts/check-boundaries.sh
  node scripts/check-provenance.mjs
  cargo test --locked --manifest-path cli/Cargo.toml
  cargo build --locked --release --manifest-path cli/Cargo.toml
  bash scripts/check-cli-build.sh
)

printf 'JR-ISOLATED-BUILD-OK\n'
