#!/usr/bin/env bash
set -u -o pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
VERIFIER_LOG_ROOT="${VERIFIER_LOG_ROOT:-/logs/verifier}"

if [ "$ROOT_DIR" = "/" ]; then
  DEFAULT_TESTS_ROOT="/tests"
else
  DEFAULT_TESTS_ROOT="$ROOT_DIR/tests"
fi
TESTS_ROOT="${TESTS_ROOT:-$DEFAULT_TESTS_ROOT}"

export TASK_BUNDLE_ROOT="${TASK_BUNDLE_ROOT:-$ROOT_DIR/environment/reference_bundle}"
export TASK_WORKSPACE_ROOT="${TASK_WORKSPACE_ROOT:-$ROOT_DIR/environment/workspace}"
export TASK_OUTPUT_ROOT="${TASK_OUTPUT_ROOT:-$ROOT_DIR/.tmp_test_output}"

rm -rf "$TASK_OUTPUT_ROOT"
mkdir -p "$TASK_OUTPUT_ROOT" "$VERIFIER_LOG_ROOT"

cd "$ROOT_DIR"
python3 -m pytest -q "$TESTS_ROOT" 2>&1 | tee "$VERIFIER_LOG_ROOT/pytest-output.txt"
STATUS=${PIPESTATUS[0]}
if [ "$STATUS" -eq 0 ]; then
  printf '1.0\n' > "$VERIFIER_LOG_ROOT/reward.txt"
  printf '{"reward": 1.0}\n' > "$VERIFIER_LOG_ROOT/result.json"
else
  printf '0.0\n' > "$VERIFIER_LOG_ROOT/reward.txt"
  printf '{"reward": 0.0}\n' > "$VERIFIER_LOG_ROOT/result.json"
fi
exit 0
