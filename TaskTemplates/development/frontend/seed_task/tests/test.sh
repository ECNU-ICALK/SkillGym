#!/bin/bash
set -euo pipefail

VERIFIER_LOG_ROOT="${VERIFIER_LOG_ROOT:-/logs/verifier}"
APP_ROOT="${APP_ROOT:-/app}"
API_ROOT="${API_ROOT:-/services/energy-api}"
TESTS_ROOT="${TESTS_ROOT:-/tests}"
DATA_ROOT="${DATA_ROOT:-/data}"
mkdir -p "$VERIFIER_LOG_ROOT"

kill_servers() {
  fuser -k 3000/tcp 2>/dev/null || true
  fuser -k 3001/tcp 2>/dev/null || true
  pkill -f "vite preview" 2>/dev/null || true
  pkill -f "node server.js" 2>/dev/null || true
  sleep 1
}

wait_for_url() {
  local url="$1"
  local attempts="$2"
  for _ in $(seq 1 "$attempts"); do
    if curl -fsS "$url" >/dev/null 2>&1; then
      return 0
    fi
    sleep 1
  done
  return 1
}

kill_servers

cd "$API_ROOT"
export ENERGY_DATA_DIR="$DATA_ROOT"
npm start > "$VERIFIER_LOG_ROOT/api.log" 2>&1 &
API_PID=$!
wait_for_url "http://localhost:3001/health" 30

cd "$APP_ROOT"
npm run build > "$VERIFIER_LOG_ROOT/build.log" 2>&1
npm run preview > "$VERIFIER_LOG_ROOT/app.log" 2>&1 &
APP_PID=$!
wait_for_url "http://localhost:3000" 40

set +e
python3 "$TESTS_ROOT/verify_energy_workbench.py" 2>&1 | tee "$VERIFIER_LOG_ROOT/verify-output.txt"
VERIFY_EXIT=${PIPESTATUS[0]}
set -e

if [ "$VERIFY_EXIT" -eq 0 ]; then
  echo 1 > "$VERIFIER_LOG_ROOT/reward.txt"
else
  echo 0 > "$VERIFIER_LOG_ROOT/reward.txt"
fi

kill "$APP_PID" 2>/dev/null || true
kill "$API_PID" 2>/dev/null || true
kill_servers

exit 0
