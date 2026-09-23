#!/bin/bash
set -euo pipefail

WORKSPACE_ROOT="${WORKSPACE_ROOT:-/app/workspace}"
PORT="${PORT:-3000}"
IMDB_DATA_DIR="${IMDB_DATA_DIR:-/app/data}"
STATE_DIR="${STATE_DIR:-/app/workspace/state}"
RUN_INSTALL="${RUN_INSTALL:-1}"
RUN_BUILD="${RUN_BUILD:-1}"
LOG_PATH="${LOG_PATH:-/tmp/curation-workbench.log}"

mkdir -p "$STATE_DIR"
cd "$WORKSPACE_ROOT"
export IMDB_DATA_DIR
export STATE_DIR
export PORT

if [ "$RUN_INSTALL" = "1" ]; then
  npm install > /tmp/curation-workbench-install.log 2>&1
fi

if [ "$RUN_BUILD" = "1" ]; then
  npm run build > /tmp/curation-workbench-build.log 2>&1
fi

npm start > "$LOG_PATH" 2>&1
