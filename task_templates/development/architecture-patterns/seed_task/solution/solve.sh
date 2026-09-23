#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
FIXED_ROOT="$SCRIPT_DIR/fixed"
if [ -n "${WORKSPACE_ROOT:-}" ]; then
  TARGET_ROOT="$WORKSPACE_ROOT"
elif [ -d /environment/workspace ]; then
  TARGET_ROOT="/environment/workspace"
else
  TARGET_ROOT="/app/workspace"
fi

cp -R "$FIXED_ROOT/." "$TARGET_ROOT/"
