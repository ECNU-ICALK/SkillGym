#!/bin/bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TASK_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
FIXED_SCRIPT="${TASK_ROOT}/solution/fixed/build_digest.py"

resolve_bundle_root() {
  local root="$1"
  for candidate in \
    "${root}/environment/release_watch" \
    "${root}/environment/release-watch" \
    "${root}/release_watch" \
    "${root}/release-watch"
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

if [ -d /app ] && [ -f /solution/fixed/build_digest.py ]; then
  FIXED_SCRIPT="/solution/fixed/build_digest.py"
  BUNDLE_ROOT="${TASK_BUNDLE_ROOT:-/app/release-watch}"
  WORKSPACE_ROOT="${TASK_WORKSPACE_ROOT:-/app/workspace}"
  OUTPUT_ROOT="${TASK_OUTPUT_ROOT:-/app/output}"
  mkdir -p "${WORKSPACE_ROOT}" "${OUTPUT_ROOT}"
  cp "${FIXED_SCRIPT}" "${WORKSPACE_ROOT}/build_digest.py"
  chmod 755 "${WORKSPACE_ROOT}/build_digest.py"
else
  BUNDLE_ROOT="$(resolve_bundle_root "${TASK_ROOT}")"
  SOURCE_WORKSPACE_ROOT="$(resolve_workspace_root "${TASK_ROOT}")"
  WORKSPACE_ROOT="${TASK_ROOT}/.tmp_local_workspace"
  OUTPUT_ROOT="${TASK_ROOT}/.tmp_local_output"
  rm -rf "${WORKSPACE_ROOT}" "${OUTPUT_ROOT}"
  mkdir -p "${WORKSPACE_ROOT}" "${OUTPUT_ROOT}"
  if [ -d "${SOURCE_WORKSPACE_ROOT}" ]; then
    cp -R "${SOURCE_WORKSPACE_ROOT}/." "${WORKSPACE_ROOT}/" 2>/dev/null || true
  fi
  cp "${FIXED_SCRIPT}" "${WORKSPACE_ROOT}/build_digest.py"
  chmod 755 "${WORKSPACE_ROOT}/build_digest.py"
fi

mkdir -p "${OUTPUT_ROOT}"
find "${OUTPUT_ROOT}" -mindepth 1 -maxdepth 1 -exec rm -rf {} +

python3 "${WORKSPACE_ROOT}/build_digest.py" \
  --bundle-root "${BUNDLE_ROOT}" \
  --workspace-root "${WORKSPACE_ROOT}" \
  --output-root "${OUTPUT_ROOT}"
