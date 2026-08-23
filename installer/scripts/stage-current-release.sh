#!/usr/bin/env bash
set -euo pipefail

project_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
bundle_root="$project_root/installer/dist/bundles/jackrabbit-current-v0.2"
release_root="$bundle_root/release"

if [[ -e "$release_root" ]]; then
  echo "release already exists: $release_root" >&2
  exit 1
fi

mkdir -p \
  "$release_root/images/stock" \
  "$release_root/images/jackrabbit" \
  "$release_root/images/cipheros"

link_image() {
  local source="$1" destination="$2"
  [[ -f "$source" ]] || { echo "missing release input: $source" >&2; exit 1; }
  ln "$source" "$destination"
}

stock="$project_root/image/baseline/rabbit-0.8.293/official"
cipher="$project_root/image/extracted"
product_candidate="$project_root/image/candidates/v0.1"
system_candidate="$project_root/image/candidates/installer-system-v0.4.26-Carrot1"
vendor_candidate="$project_root/image/candidates/installer-delta-v0.2"

link_image "$stock/boot.img" "$release_root/images/stock/boot.img"
link_image "$stock/super.img" "$release_root/images/stock/super.img"
cp "$stock/vbmeta.img" "$release_root/images/stock/vbmeta.img"
printf '\000\000\000\003' | dd of="$release_root/images/stock/vbmeta.img" bs=1 seek=120 conv=notrunc status=none
link_image "$stock/vbmeta_system.img" "$release_root/images/stock/vbmeta_system.img"
link_image "$stock/vbmeta_vendor.img" "$release_root/images/stock/vbmeta_vendor.img"

link_image "$system_candidate/system.img" "$release_root/images/jackrabbit/system.img"
link_image "$product_candidate/product.img" "$release_root/images/jackrabbit/product.img"
link_image "$cipher/system_ext.img" "$release_root/images/cipheros/system_ext.img"
link_image "$vendor_candidate/vendor.img" "$release_root/images/cipheros/vendor.img"
link_image "$cipher/vbmeta.img" "$release_root/images/cipheros/vbmeta.img"
link_image "$cipher/vbmeta_system.img" "$release_root/images/cipheros/vbmeta_system.img"
link_image "$cipher/vbmeta_vendor.img" "$release_root/images/cipheros/vbmeta_vendor.img"

node "$project_root/installer/scripts/verify-release-directory.mjs" "$release_root"
printf '%s\n' "$bundle_root"
