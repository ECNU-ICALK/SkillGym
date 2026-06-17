#!/bin/bash
set -euo pipefail

mkdir -p /logs/verifier

if pytest -q /tests; then
  printf '1.0\n' > /logs/verifier/reward.txt
else
  status=$?
  printf '0.0\n' > /logs/verifier/reward.txt
  exit "$status"
fi
