#!/bin/bash
set -euo pipefail

VERIFIER_LOG_ROOT="${VERIFIER_LOG_ROOT:-/logs/verifier}"
TESTS_ROOT="${TESTS_ROOT:-/tests}"
mkdir -p "$VERIFIER_LOG_ROOT"

cd "$TESTS_ROOT"

set +e
pytest -q test_outputs.py test_guardrails.py 2>&1 | tee "$VERIFIER_LOG_ROOT/pytest-output.txt"
VERIFY_EXIT=${PIPESTATUS[0]}
set -e

if [ "$VERIFY_EXIT" -eq 0 ]; then
  echo 1 > "$VERIFIER_LOG_ROOT/reward.txt"
else
  echo 0 > "$VERIFIER_LOG_ROOT/reward.txt"
fi

exit 0
