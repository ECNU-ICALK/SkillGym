#!/bin/bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
if [ -d /app/workspace ]; then
  TASK_ROOT="/app/workspace"
else
  TASK_ROOT="$(cd "$SCRIPT_DIR/../environment/workspace" && pwd)"
fi

cp "$SCRIPT_DIR/fixed/server.js" "$TASK_ROOT/server.js"
cp "$SCRIPT_DIR/fixed/service/app.js" "$TASK_ROOT/service/app.js"
cp "$SCRIPT_DIR/fixed/service/dataStore.js" "$TASK_ROOT/service/dataStore.js"

cd "$TASK_ROOT"
node scripts/reset_runtime_state.js
