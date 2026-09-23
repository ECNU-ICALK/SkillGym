#!/bin/bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"

bash /opt/bootstrap/start_stack.sh

rm -rf /app/workspace/plugin
mkdir -p /app/workspace/plugin /app/workspace/scripts /app/workspace/output
cp -R "$ROOT_DIR/solution/fixed/plugin/." /app/workspace/plugin/
cp "$ROOT_DIR/solution/fixed/scripts/reseed.php" /app/workspace/scripts/reseed.php
cp "$ROOT_DIR/solution/fixed/scripts/run_smoke_checks.sh" /app/workspace/scripts/run_smoke_checks.sh
chmod +x /app/workspace/scripts/run_smoke_checks.sh
php /app/workspace/scripts/reseed.php
