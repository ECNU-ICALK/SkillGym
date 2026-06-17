#!/bin/bash
set -euo pipefail

WORKSPACE_ROOT="${TASK_WORKSPACE_DIR:-/root/workspace}"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

cp "$SCRIPT_DIR/fixed/contracts/GovernanceToken.sol" "$WORKSPACE_ROOT/contracts/GovernanceToken.sol"
cp "$SCRIPT_DIR/fixed/contracts/LaunchGovernor.sol" "$WORKSPACE_ROOT/contracts/LaunchGovernor.sol"
cp "$SCRIPT_DIR/fixed/contracts/LaunchStaking.sol" "$WORKSPACE_ROOT/contracts/LaunchStaking.sol"
cp "$SCRIPT_DIR/fixed/contracts/MintableERC20.sol" "$WORKSPACE_ROOT/contracts/MintableERC20.sol"
cp "$SCRIPT_DIR/fixed/contracts/SimplePair.sol" "$WORKSPACE_ROOT/contracts/SimplePair.sol"
cp "$SCRIPT_DIR/fixed/scripts/replay.js" "$WORKSPACE_ROOT/scripts/replay.js"

chmod +x "$WORKSPACE_ROOT/run_launch.sh"
TASK_WORKSPACE_ROOT="$WORKSPACE_ROOT" \
TASK_WORKSPACE_DIR="$WORKSPACE_ROOT" \
TASK_OUTPUT_DIR="${TASK_OUTPUT_DIR:-$WORKSPACE_ROOT/out}" \
"$WORKSPACE_ROOT/run_launch.sh"
