#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cp "$ROOT_DIR/solution/fixed/render_changelog.py" \
  "$ROOT_DIR/environment/reference_bundle/workspace/scripts/render_changelog.py"

python3 "$ROOT_DIR/environment/reference_bundle/workspace/scripts/render_changelog.py"
