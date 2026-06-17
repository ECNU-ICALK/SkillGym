#!/bin/bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
WORKSPACE_DIR="/app/workspace"

mkdir -p "$WORKSPACE_DIR/tests/e2e" "$WORKSPACE_DIR/tests/pages"
install -m 0644 "$ROOT_DIR/solution/airportConsolePage.js" "$WORKSPACE_DIR/tests/pages/airportConsolePage.js"
install -m 0644 "$ROOT_DIR/solution/airport-visual-stability.spec.js" "$WORKSPACE_DIR/tests/e2e/airport-visual-stability.spec.js"

cd "$WORKSPACE_DIR"
npm test -- --reporter=line
