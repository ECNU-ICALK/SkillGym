#!/bin/bash
set -uo pipefail

VERIFIER_LOG_ROOT="${VERIFIER_LOG_ROOT:-/logs/verifier}"
mkdir -p "$VERIFIER_LOG_ROOT"

cd /app

if python3 -m pytest /tests/test_outputs.py /tests/test_guardrails.py -rA -v "$@" \
  | tee "$VERIFIER_LOG_ROOT/pytest-output.txt"; then
  printf '1.0\n' > "$VERIFIER_LOG_ROOT/reward.txt"
else
  printf '0.0\n' > "$VERIFIER_LOG_ROOT/reward.txt"
fi

cp /app/output/frame_index.json "$VERIFIER_LOG_ROOT/" 2>/dev/null || true
cp /app/output/delivery_report.json "$VERIFIER_LOG_ROOT/" 2>/dev/null || true
cp -R /app/output/stills "$VERIFIER_LOG_ROOT/" 2>/dev/null || true
cp -R /app/output/previews "$VERIFIER_LOG_ROOT/" 2>/dev/null || true
cp -R /app/output/sheets "$VERIFIER_LOG_ROOT/" 2>/dev/null || true

exit 0
