#!/bin/bash
set -euo pipefail

WORKSPACE_DIR="${WORKSPACE_DIR:-/app/workspace}"
if [ ! -d "$WORKSPACE_DIR" ]; then
  WORKSPACE_DIR="$(cd "$(dirname "$0")/.." && pwd)"
fi

cd "$WORKSPACE_DIR"
export SCENARIO_ID="${SCENARIO_ID:-docs-segment-cache}"
exec npm run framework:build -- --scenario "$SCENARIO_ID"
