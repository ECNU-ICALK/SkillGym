#!/usr/bin/env bash
set -euo pipefail

VERIFIER_LOG_ROOT="${VERIFIER_LOG_ROOT:-/logs/verifier}"
mkdir -p "$VERIFIER_LOG_ROOT"

set +e
pytest -q /tests/test_outputs.py /tests/test_guardrails.py -rA 2>&1 | tee "$VERIFIER_LOG_ROOT/pytest-output.txt"
TEST_EXIT=${PIPESTATUS[0]}
set -e

if [ "$TEST_EXIT" -eq 0 ]; then
  printf '1.0\n' > "$VERIFIER_LOG_ROOT/reward.txt"
else
  printf '0.0\n' > "$VERIFIER_LOG_ROOT/reward.txt"
fi

exit "$TEST_EXIT"
