#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TASK_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

if [ -d /environment ] && [ -f /environment/solution/fixed/build_reference.py ]; then
  TASK_ROOT="/environment"
  BUNDLE_ROOT="/environment/reference_bundle"
  WORKSPACE_ROOT="/environment/workspace"
  OUTPUT_ROOT="/environment/output"
elif [ -d /app ] && [ -f /app/solution/fixed/build_reference.py ]; then
  TASK_ROOT="/app"
  BUNDLE_ROOT="/app/reference_bundle"
  WORKSPACE_ROOT="/app/workspace"
  OUTPUT_ROOT="/app/output"
else
  BUNDLE_ROOT="${TASK_ROOT}/environment/reference_bundle"
  WORKSPACE_ROOT="${TASK_ROOT}/environment/workspace"
  OUTPUT_ROOT="${TASK_ROOT}/.tmp_local_output"
fi

cp "${TASK_ROOT}/solution/fixed/build_reference.py" "${WORKSPACE_ROOT}/build_reference.py"
chmod 755 "${WORKSPACE_ROOT}/build_reference.py"

python3 "${WORKSPACE_ROOT}/build_reference.py" \
  --bundle-root "${BUNDLE_ROOT}" \
  --workspace-root "${WORKSPACE_ROOT}" \
  --output-root "${OUTPUT_ROOT}"
