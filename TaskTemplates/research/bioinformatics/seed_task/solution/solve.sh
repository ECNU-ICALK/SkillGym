#!/bin/bash
set -euo pipefail

SOLUTION_ROOT="${SOLUTION_ROOT:-/solution}"
WORKSPACE_ROOT="${TASK_WORKSPACE_DIR:-/root/workspace}"
DATA_ROOT="${TASK_DATA_DIR:-/root/data}"
OUTPUT_ROOT="${TASK_OUTPUT_DIR:-/root/output}"

if command -v start-bioinfo-scanpy-service >/dev/null 2>&1; then
  start-bioinfo-scanpy-service
fi

cp "${SOLUTION_ROOT}/fixed/reference_pipeline.py" "${WORKSPACE_ROOT}/reference_pipeline.py"
cp "${SOLUTION_ROOT}/fixed/run_pbmc_cluster_handoff.py" "${WORKSPACE_ROOT}/run_pbmc_cluster_handoff.py"
chmod +x "${WORKSPACE_ROOT}/run_pbmc_cluster_handoff.py"
python3 "${WORKSPACE_ROOT}/run_pbmc_cluster_handoff.py" --data "${DATA_ROOT}" --output "${OUTPUT_ROOT}"
