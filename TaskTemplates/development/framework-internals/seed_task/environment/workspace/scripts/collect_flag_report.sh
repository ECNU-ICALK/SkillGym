#!/bin/bash
set -euo pipefail

WORKSPACE_DIR="${WORKSPACE_DIR:-/app/workspace}"
if [ ! -d "$WORKSPACE_DIR" ]; then
  WORKSPACE_DIR="$(cd "$(dirname "$0")/.." && pwd)"
fi

cd "$WORKSPACE_DIR"
exec npm run framework:report
