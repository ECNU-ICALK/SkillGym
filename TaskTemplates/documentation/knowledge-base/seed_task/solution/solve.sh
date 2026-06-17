#!/bin/bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TASK_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
FIXED_SCRIPT="${TASK_ROOT}/solution/fixed/curate_resources.py"

resolve_bundle_root() {
  local root="$1"
  for candidate in \
    "${root}/environment/knowledge_base" \
    "${root}/environment/knowledge-base" \
    "${root}/knowledge_base" \
    "${root}/knowledge-base"
  do
    if [ -d "${candidate}" ]; then
      printf '%s\n' "${candidate}"
      return 0
    fi
  done
  return 1
}

resolve_workspace_root() {
  local root="$1"
  for candidate in \
    "${root}/environment/workspace" \
    "${root}/workspace"
  do
    if [ -d "${candidate}" ]; then
      printf '%s\n' "${candidate}"
      return 0
    fi
  done
  return 1
}

if [ -d /app ] && [ -f /solution/fixed/curate_resources.py ]; then
  FIXED_SCRIPT="/solution/fixed/curate_resources.py"
  KB_ROOT="${TASK_BUNDLE_ROOT:-/app/knowledge-base}"
  WORKSPACE_ROOT="${TASK_WORKSPACE_ROOT:-/app/workspace}"
  OUTPUT_ROOT="${TASK_OUTPUT_ROOT:-/app/output}"
  mkdir -p "${WORKSPACE_ROOT}" "${OUTPUT_ROOT}"
  cp "${FIXED_SCRIPT}" "${WORKSPACE_ROOT}/curate_resources.py"
  chmod 755 "${WORKSPACE_ROOT}/curate_resources.py"
else
  KB_ROOT="$(resolve_bundle_root "${TASK_ROOT}")"
  SOURCE_WORKSPACE_ROOT="$(resolve_workspace_root "${TASK_ROOT}")"
  WORKSPACE_ROOT="${TASK_ROOT}/.tmp_local_workspace"
  OUTPUT_ROOT="${TASK_ROOT}/.tmp_local_output"
  rm -rf "${WORKSPACE_ROOT}" "${OUTPUT_ROOT}"
  mkdir -p "${WORKSPACE_ROOT}" "${OUTPUT_ROOT}"
  cp "${FIXED_SCRIPT}" "${WORKSPACE_ROOT}/curate_resources.py"
  chmod 755 "${WORKSPACE_ROOT}/curate_resources.py"
  if [ -d "${SOURCE_WORKSPACE_ROOT}" ]; then
    cp -R "${SOURCE_WORKSPACE_ROOT}/." "${WORKSPACE_ROOT}/" 2>/dev/null || true
    cp "${FIXED_SCRIPT}" "${WORKSPACE_ROOT}/curate_resources.py"
    chmod 755 "${WORKSPACE_ROOT}/curate_resources.py"
  fi
fi

mkdir -p "${OUTPUT_ROOT}"
find "${OUTPUT_ROOT}" -mindepth 1 -maxdepth 1 -exec rm -rf {} +

python3 "${WORKSPACE_ROOT}/curate_resources.py" \
  --bundle-root "${KB_ROOT}" \
  --workspace-root "${WORKSPACE_ROOT}" \
  --output-root "${OUTPUT_ROOT}"
