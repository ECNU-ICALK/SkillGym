#!/usr/bin/env bash
set -u -o pipefail

mkdir -p /logs/verifier
REWARD_FILE="/logs/verifier/reward.txt"
RESULT_FILE="/logs/verifier/result.json"

python -m pytest -q /tests/test_outputs.py
STATUS=$?
if [ "$STATUS" -eq 0 ]; then
  printf '1.0\n' > "${REWARD_FILE}"
  printf '{"reward": 1.0}\n' > "${RESULT_FILE}"
else
  printf '0.0\n' > "${REWARD_FILE}"
  printf '{"reward": 0.0}\n' > "${RESULT_FILE}"
fi
exit 0
