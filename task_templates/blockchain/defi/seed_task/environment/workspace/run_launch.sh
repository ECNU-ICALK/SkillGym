#!/bin/bash
set -euo pipefail

WORKSPACE_ROOT="${TASK_WORKSPACE_DIR:-${TASK_WORKSPACE_ROOT:-/root/workspace}}"
OUTPUT_ROOT="${TASK_OUTPUT_DIR:-$WORKSPACE_ROOT/out}"

mkdir -p "$OUTPUT_ROOT"
rm -f "$OUTPUT_ROOT/launch_report.json"

cd "$WORKSPACE_ROOT"
npm install --silent --no-audit --no-fund
npx hardhat compile
TASK_WORKSPACE_DIR="$WORKSPACE_ROOT" TASK_OUTPUT_DIR="$OUTPUT_ROOT" npx hardhat run scripts/replay.js --network hardhat
