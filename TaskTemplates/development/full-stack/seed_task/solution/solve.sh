#!/bin/bash
set -euo pipefail

TASK_ROOT="${TASK_ROOT:-/app}"
WORKSPACE_ROOT="${WORKSPACE_ROOT:-$TASK_ROOT/workspace}"
SOLUTION_ROOT="$(cd "$(dirname "$0")" && pwd)"
REFERENCE_ROOT="$SOLUTION_ROOT/reference"

mkdir -p "$WORKSPACE_ROOT"
find "$WORKSPACE_ROOT" -mindepth 1 -maxdepth 1 -exec rm -rf {} +
cp -R "$REFERENCE_ROOT"/. "$WORKSPACE_ROOT"/
