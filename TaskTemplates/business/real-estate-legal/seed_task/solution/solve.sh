#!/bin/bash
set -euo pipefail

if command -v start-real-estate-legal-audit >/dev/null 2>&1; then
  start-real-estate-legal-audit
fi

mkdir -p /root/output
python3 /solution/build_submission.py
