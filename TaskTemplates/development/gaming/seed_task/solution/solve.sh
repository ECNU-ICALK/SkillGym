#!/bin/bash
set -euo pipefail

TARGET_DIR="${1:-/app/workspace/studio}"
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

mkdir -p "$TARGET_DIR"
cp -R "$SCRIPT_DIR/studio/." "$TARGET_DIR/"
