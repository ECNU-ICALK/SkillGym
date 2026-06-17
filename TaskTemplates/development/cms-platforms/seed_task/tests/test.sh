#!/usr/bin/env bash
set -euo pipefail

WORKSPACE_ROOT="${WORKSPACE_ROOT:-/app/workspace}"
DATA_ROOT="${DATA_ROOT:-/app/data}"
TEST_ROOT="${TEST_ROOT:-/tests}"
BASE_URL="${BASE_URL:-http://127.0.0.1:3000}"
VERIFIER_LOG_ROOT="${VERIFIER_LOG_ROOT:-/logs/verifier}"

cd "$WORKSPACE_ROOT"
mkdir -p "$VERIFIER_LOG_ROOT"

export NEXT_TELEMETRY_DISABLED=1
export PAYLOAD_SECRET="met-highlight-secret"
export DATABASE_URL="file:./runtime/payload.db"
export PORT=3000
export HOSTNAME=0.0.0.0
export WORKSPACE_ROOT
export DATA_ROOT
export TEST_ROOT
export BASE_URL

cleanup() {
  pkill -f "$WORKSPACE_ROOT/node_modules/.bin/next dev" 2>/dev/null || true
  if [ -f /tmp/met_objects_seed.csv.bak ]; then
    cp /tmp/met_objects_seed.csv.bak "$DATA_ROOT/met_objects_seed.csv"
  fi
}

trap cleanup EXIT

run_verifier() {
  npm run reseed || return $?

  npm run dev >/tmp/met-highlight-app.log 2>&1 &
  APP_PID=$!

  python3 "$TEST_ROOT/test_outputs.py" || return $?

  pkill -f "$WORKSPACE_ROOT/node_modules/.bin/next dev" 2>/dev/null || true
  sleep 2

  cp "$DATA_ROOT/met_objects_seed.csv" /tmp/met_objects_seed.csv.bak
  python3 - <<'PY'
from pathlib import Path
import os

seed_path = Path(os.environ['DATA_ROOT']) / 'met_objects_seed.csv'
lines = seed_path.read_text(encoding='utf-8').splitlines()
mutated = []
for line in lines:
    if line.startswith('436532,'):
        mutated.append(line.replace(',10,publish,', ',99,draft,', 1))
    elif line.startswith('488319,'):
        mutated.append(line.replace(',false,false,false,', ',true,false,false,', 1))
    else:
        mutated.append(line)
seed_path.write_text('\n'.join(mutated) + '\n', encoding='utf-8')
PY

  npm run reseed || return $?

  npm run dev >/tmp/met-highlight-app-mutated.log 2>&1 &
  APP_PID=$!

  python3 "$TEST_ROOT/test_mutation.py" || return $?

  pkill -f "$WORKSPACE_ROOT/node_modules/.bin/next dev" 2>/dev/null || true
  sleep 2
  cp /tmp/met_objects_seed.csv.bak "$DATA_ROOT/met_objects_seed.csv"
}

set +e
run_verifier \
  > >(tee "$VERIFIER_LOG_ROOT/test-stdout.txt") \
  2> >(tee "$VERIFIER_LOG_ROOT/test-stderr.txt" >&2)
status=$?
set -e

if [ "$status" -eq 0 ]; then
  status=0
  printf '1.0\n' > "$VERIFIER_LOG_ROOT/reward.txt"
else
  printf '0.0\n' > "$VERIFIER_LOG_ROOT/reward.txt"
fi

exit "$status"
