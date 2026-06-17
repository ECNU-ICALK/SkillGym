#!/usr/bin/env bash
set -euo pipefail

if [ "$#" -ne 1 ]; then
  echo "usage: $0 <root-dir>" >&2
  exit 2
fi

ROOT_DIR="$1"
WORKSPACE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
export TF_PLUGIN_CACHE_DIR="${TF_PLUGIN_CACHE_DIR:-$WORKSPACE_DIR/.terraform.d/plugin-cache}"
mkdir -p "$TF_PLUGIN_CACHE_DIR"
TMP_DIR="$(mktemp -d)"
trap 'rm -rf "$TMP_DIR"' EXIT

# Root plans are expected to work locally without cloud credentials or provider-login side effects.
terraform -chdir="$ROOT_DIR" init -backend=false -input=false >/dev/null
terraform -chdir="$ROOT_DIR" plan -input=false -lock=false -out="$TMP_DIR/plan.bin" >/dev/null
terraform -chdir="$ROOT_DIR" show -json "$TMP_DIR/plan.bin" > "$TMP_DIR/plan.json"
cat "$TMP_DIR/plan.json"
