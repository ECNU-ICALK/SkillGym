#!/bin/bash
set -euo pipefail

PROFILE_FILE=/services/metrics/service_profiles.json
LOG_DIR=/app/runtime/logs
mkdir -p "$LOG_DIR"

start_one() {
  local service="$1"
  local port="$2"
  if curl -fsS "http://127.0.0.1:${port}/health" >/dev/null 2>&1; then
    return 0
  fi
  nohup python3 /services/metrics/serve_metrics.py \
    --profiles "$PROFILE_FILE" \
    --service "$service" \
    >"${LOG_DIR}/${service}.log" 2>&1 &
  for _ in $(seq 1 40); do
    if curl -fsS "http://127.0.0.1:${port}/health" >/dev/null 2>&1; then
      return 0
    fi
    sleep 0.25
  done
  echo "failed to start metrics service ${service} on ${port}" >&2
  return 1
}

start_one harbor-core 18081
start_one harbor-jobservice 18082
start_one harbor-registry-api 18083
start_one harbor-registry-storage 18087
start_one harbor-exporter 18084
start_one shadow-target 18085
start_one smoke-probe 18086
