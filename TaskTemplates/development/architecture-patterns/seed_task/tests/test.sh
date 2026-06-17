#!/usr/bin/env bash
set -euo pipefail

WORKSPACE_ROOT="${WORKSPACE_ROOT:-/app/workspace}"
TESTS_ROOT="${TESTS_ROOT:-/tests}"
VERIFIER_LOG_ROOT="${VERIFIER_LOG_ROOT:-/logs/verifier}"

mkdir -p "$VERIFIER_LOG_ROOT"
cd "$WORKSPACE_ROOT"

set +e
pytest -q "$TESTS_ROOT" 2>&1 | tee "$VERIFIER_LOG_ROOT/test-output.txt"
PYTEST_EXIT=${PIPESTATUS[0]}
set -e

if [ "$PYTEST_EXIT" -eq 0 ]; then
  printf '1.0\n' > "$VERIFIER_LOG_ROOT/reward.txt"
  printf '{"reward": 1.0}\n' > "$VERIFIER_LOG_ROOT/result.json"
else
  printf '0.0\n' > "$VERIFIER_LOG_ROOT/reward.txt"
  printf '{"reward": 0.0}\n' > "$VERIFIER_LOG_ROOT/result.json"
fi

exit 0
