#!/bin/bash
set -euo pipefail

if command -v start-launch-copy-service >/dev/null 2>&1; then
  start-launch-copy-service
fi

python3 /solution/solve.py
