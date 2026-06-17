#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
export TF_PLUGIN_CACHE_DIR="${TF_PLUGIN_CACHE_DIR:-$ROOT_DIR/.terraform.d/plugin-cache}"
mkdir -p "$TF_PLUGIN_CACHE_DIR"

# Keep the current local, providerless Terraform plan workflow intact across roots and the shared module.
python3 "$ROOT_DIR/scripts/structure_guard.py"

for target in "$ROOT_DIR/live/staging" "$ROOT_DIR/live/prod" "$ROOT_DIR/examples/complete"; do
  terraform -chdir="$target" fmt -check
  terraform -chdir="$target" init -backend=false -input=false >/tmp/terraform-init-$(basename "$target").log
  terraform -chdir="$target" validate
done
