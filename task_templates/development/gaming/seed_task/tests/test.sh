#!/bin/bash
set -euo pipefail

VERIFIER_DIR="${VERIFIER_DIR:-/logs/verifier}"
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

mkdir -p "$VERIFIER_DIR"

set +e
python3 -m pytest -q "$SCRIPT_DIR/test_outputs.py" "$SCRIPT_DIR/test_guardrails.py" 2>&1 | tee "$VERIFIER_DIR/pytest-output.txt"
PYTEST_EXIT=${PIPESTATUS[0]}
set -e

if [ "$PYTEST_EXIT" -eq 0 ]; then
  echo 1 > "$VERIFIER_DIR/reward.txt"
  printf '{"reward": 1.0}\n' > "$VERIFIER_DIR/result.json"
else
  echo 0 > "$VERIFIER_DIR/reward.txt"
  printf '{"reward": 0.0}\n' > "$VERIFIER_DIR/result.json"
fi

exit 0
