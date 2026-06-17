#!/bin/bash
set -euo pipefail

VERIFIER_LOG_ROOT="${VERIFIER_LOG_ROOT:-/logs/verifier}"
WORKSPACE_ROOT="${WORKSPACE_ROOT:-/app/workspace}"
APP_ROOT="${APP_ROOT:-$WORKSPACE_ROOT/app}"
API_ROOT="${API_ROOT:-/services/citibike-api}"
TESTS_ROOT="${TESTS_ROOT:-/tests}"
DATA_ROOT="${DATA_ROOT:-$WORKSPACE_ROOT/data}"
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
export CITIBIKE_DATA_DIR="$DATA_ROOT"
export CITIBIKE_API_PORT=3001
npm install > "$VERIFIER_LOG_ROOT/api-npm.log" 2>&1
npm start > "$VERIFIER_LOG_ROOT/api.log" 2>&1 &
API_PID=$!
wait_for_url "http://localhost:3001/health" 30

cd "$APP_ROOT"
npm install > "$VERIFIER_LOG_ROOT/app-npm.log" 2>&1
npm run build > "$VERIFIER_LOG_ROOT/build.log" 2>&1
npm run preview -- --host 0.0.0.0 --port 3000 > "$VERIFIER_LOG_ROOT/app.log" 2>&1 &
APP_PID=$!
wait_for_url "http://localhost:3000" 40

set +e
python3 "$TESTS_ROOT/test_outputs.py" 2>&1 | tee "$VERIFIER_LOG_ROOT/test-outputs.txt"
OUTPUT_EXIT=${PIPESTATUS[0]}
python3 "$TESTS_ROOT/test_guardrails.py" 2>&1 | tee "$VERIFIER_LOG_ROOT/test-guardrails.txt"
GUARD_EXIT=${PIPESTATUS[0]}
set -e

if [ "$OUTPUT_EXIT" -eq 0 ] && [ "$GUARD_EXIT" -eq 0 ]; then
  echo 1 > "$VERIFIER_LOG_ROOT/reward.txt"
else
  echo 0 > "$VERIFIER_LOG_ROOT/reward.txt"
fi

kill "$APP_PID" 2>/dev/null || true
kill "$API_PID" 2>/dev/null || true
kill_servers

exit 0
