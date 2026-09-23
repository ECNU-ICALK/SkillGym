#!/bin/bash
set -euo pipefail

SOLUTION_ROOT="${SOLUTION_ROOT:-/solution}"
WORKSPACE_ROOT="${TASK_WORKSPACE_DIR:-/root/workspace}"
DATA_ROOT="${TASK_DATA_DIR:-/root/data}"
OUTPUT_ROOT="${TASK_OUTPUT_DIR:-/root/output}"

cp "${SOLUTION_ROOT}/fixed/run_marine_heat_intake.py" "${WORKSPACE_ROOT}/run_marine_heat_intake.py"
chmod +x "${WORKSPACE_ROOT}/run_marine_heat_intake.py"
python3 "${WORKSPACE_ROOT}/run_marine_heat_intake.py" --data "${DATA_ROOT}" --output "${OUTPUT_ROOT}"
