#!/bin/bash
set -uo pipefail

mkdir -p /logs/verifier
REWARD_FILE="/logs/verifier/reward.txt"
RESULT_FILE="/logs/verifier/result.json"

python3 -m pytest -q /tests/test_outputs.py /tests/test_guardrails.py 2>&1 | tee /logs/verifier/pytest-output.txt
STATUS=${PIPESTATUS[0]}
if [ "$STATUS" -eq 0 ]; then
  printf '1.0\n' > "${REWARD_FILE}"
  printf '{"reward": 1.0}\n' > "${RESULT_FILE}"
else
  printf '0.0\n' > "${REWARD_FILE}"
  printf '{"reward": 0.0}\n' > "${RESULT_FILE}"
fi
exit 0
