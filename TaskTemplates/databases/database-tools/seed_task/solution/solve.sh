#!/bin/bash
set -euo pipefail

SOLUTION_ROOT="${SOLUTION_ROOT:-/solution}"
WORKSPACE_ROOT="${TASK_WORKSPACE_DIR:-/root/workspace}"
DATA_ROOT="${TASK_DATA_DIR:-/root/data}"
OUTPUT_ROOT="${TASK_OUTPUT_DIR:-/root/output}"

cp -R "${SOLUTION_ROOT}/fixed/." "${WORKSPACE_ROOT}/"
chmod +x "${WORKSPACE_ROOT}/run_rapid_transit_release.py"

python3 "${WORKSPACE_ROOT}/run_rapid_transit_release.py" --data "${DATA_ROOT}" --output "${OUTPUT_ROOT}"
