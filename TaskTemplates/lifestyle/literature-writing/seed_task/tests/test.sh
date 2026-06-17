#!/bin/bash
set -euo pipefail

TESTS_ROOT="${TESTS_ROOT:-/tests}"
VERIFIER_LOG_ROOT="${VERIFIER_LOG_ROOT:-/logs/verifier}"

mkdir -p "$VERIFIER_LOG_ROOT"
if command -v start-launch-copy-service >/dev/null 2>&1; then
  start-launch-copy-service
fi

set +e
pytest -q "$TESTS_ROOT" 2>&1 | tee "$VERIFIER_LOG_ROOT/test-stdout.txt"
TEST_EXIT=${PIPESTATUS[0]}
set -e

if [ "$TEST_EXIT" -eq 0 ]; then
  echo 1 > "$VERIFIER_LOG_ROOT/reward.txt"
else
  echo 0 > "$VERIFIER_LOG_ROOT/reward.txt"
fi

exit 0
