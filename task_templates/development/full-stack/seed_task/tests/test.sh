#!/bin/bash
set -euo pipefail

TESTS_ROOT="${TESTS_ROOT:-/tests}"
VERIFIER_LOG_ROOT="${VERIFIER_LOG_ROOT:-/logs/verifier}"

mkdir -p "$VERIFIER_LOG_ROOT"

set +e
python3 "$TESTS_ROOT/verify_curation_workbench.py" 2>&1 | tee "$VERIFIER_LOG_ROOT/test-output.txt"
VERIFY_EXIT=${PIPESTATUS[0]}
set -e

if [ "$VERIFY_EXIT" -eq 0 ]; then
  echo 1 > "$VERIFIER_LOG_ROOT/reward.txt"
else
  echo 0 > "$VERIFIER_LOG_ROOT/reward.txt"
fi

exit 0
