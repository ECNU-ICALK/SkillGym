#!/bin/bash
set -euo pipefail

APP_DIR="${APP_DIR:-/app/workspace/app}"
ARTIFACTS_DIR="${ARTIFACTS_DIR:-/app/workspace/artifacts}"

mkdir -p "$ARTIFACTS_DIR"

candidate_roots=(
  "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/fixed"
  "$(pwd)/solution/fixed"
  "/solution/fixed"
)

FIXED_ROOT=""
for candidate in "${candidate_roots[@]}"; do
  if [ -d "$candidate" ]; then
    FIXED_ROOT="$candidate"
    break
  fi
done

if [ -z "$FIXED_ROOT" ] || [ ! -d "$FIXED_ROOT" ]; then
  echo "Unable to locate solution/fixed assets" >&2
  exit 1
fi

cp "$FIXED_ROOT/index.html" "$APP_DIR/index.html"
cp "$FIXED_ROOT/main.jsx" "$APP_DIR/src/main.jsx"
cp "$FIXED_ROOT/api.js" "$APP_DIR/src/api.js"
cp "$FIXED_ROOT/App.jsx" "$APP_DIR/src/App.jsx"
cp "$FIXED_ROOT/app.css" "$APP_DIR/src/app.css"
cp "$FIXED_ROOT/manifest.webmanifest" "$APP_DIR/public/manifest.webmanifest"
cp "$FIXED_ROOT/offline.html" "$APP_DIR/public/offline.html"
cp "$FIXED_ROOT/sw.js" "$APP_DIR/public/sw.js"
cp "$FIXED_ROOT/release-notes.md" "$ARTIFACTS_DIR/release-notes.md"
