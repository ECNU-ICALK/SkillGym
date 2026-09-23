#!/bin/bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"

cp "$ROOT_DIR/solution/fixed/App.jsx" /app/src/App.jsx
cp "$ROOT_DIR/solution/fixed/overview-metrics.js" /app/src/overview-metrics.js
cp "$ROOT_DIR/solution/fixed/workbench-state.js" /app/src/workbench-state.js
cp "$ROOT_DIR/solution/fixed/use-country-details.js" /app/src/use-country-details.js
cp "$ROOT_DIR/solution/fixed/country-drawer.jsx" /app/src/country-drawer.jsx
