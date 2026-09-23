#!/bin/bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
TARGET_ROOT="/app/workspace/framework/src"
FRAMEWORK_ROOT="/app/workspace/framework"

cp "$ROOT_DIR/solution/fixed/config-shared.ts" "$TARGET_ROOT/server/config-shared.ts"
cp "$ROOT_DIR/solution/fixed/config-schema.ts" "$TARGET_ROOT/server/config-schema.ts"
cp "$ROOT_DIR/solution/fixed/define-env-plugin.ts" "$TARGET_ROOT/build/define-env-plugin.ts"
cp "$ROOT_DIR/solution/fixed/next-server.ts" "$TARGET_ROOT/server/next-server.ts"
cp "$ROOT_DIR/solution/fixed/export-worker.ts" "$TARGET_ROOT/export/worker.ts"
cp "$ROOT_DIR/solution/fixed/module.compiled.js" "$TARGET_ROOT/compiled/module.compiled.js"
cp "$ROOT_DIR/solution/fixed/next-runtime.webpack-config.js" "$FRAMEWORK_ROOT/next-runtime.webpack-config.js"
cp "$ROOT_DIR/solution/fixed/taskfile.js" "$FRAMEWORK_ROOT/taskfile.js"
mkdir -p "$TARGET_ROOT/server/route-modules/app-page"
cp "$ROOT_DIR/solution/fixed/app-page-module.compiled.js" "$TARGET_ROOT/server/route-modules/app-page/module.compiled.js"
