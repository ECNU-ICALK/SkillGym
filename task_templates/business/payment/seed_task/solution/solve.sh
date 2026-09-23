#!/bin/bash
set -euo pipefail

mkdir -p /root/output
if command -v start-ap-review >/dev/null 2>&1; then
  start-ap-review
fi

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
python3 "$SCRIPT_DIR/solve.py"
