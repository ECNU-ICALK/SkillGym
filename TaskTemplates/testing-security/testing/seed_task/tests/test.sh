#!/bin/bash
set -euo pipefail

TESTS_ROOT="${TESTS_ROOT:-/tests}"
VERIFIER_LOG_ROOT="${VERIFIER_LOG_ROOT:-/logs/verifier}"

mkdir -p "$VERIFIER_LOG_ROOT"

set +e
python3 -m pytest -q "$TESTS_ROOT/test_outputs.py" "$TESTS_ROOT/test_guardrails.py" 2>&1 | tee "$VERIFIER_LOG_ROOT/pytest-output.txt"
TEST_EXIT=${PIPESTATUS[0]}
set -e

if [ "$TEST_EXIT" -eq 0 ]; then
  echo 1 > "$VERIFIER_LOG_ROOT/reward.txt"
  printf '{"reward": 1.0}\n' > "$VERIFIER_LOG_ROOT/result.json"
else
  echo 0 > "$VERIFIER_LOG_ROOT/reward.txt"
  printf '{"reward": 0.0}\n' > "$VERIFIER_LOG_ROOT/result.json"
fi

exit 0
