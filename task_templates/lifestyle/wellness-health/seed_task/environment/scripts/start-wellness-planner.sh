#!/bin/bash
set -euo pipefail

if ! python3 -c 'import urllib.request; urllib.request.urlopen("http://127.0.0.1:8147/health", timeout=1).read()' >/dev/null 2>&1; then
  nohup python3 /opt/wellness-runtime/server_runtime.pyc >/tmp/wellness-planner.log 2>&1 &
  for i in $(seq 1 60); do
    if python3 -c 'import urllib.request; urllib.request.urlopen("http://127.0.0.1:8147/health", timeout=1).read()' >/dev/null 2>&1; then
      break
    fi
    sleep 0.5
  done
fi

python3 -c 'import urllib.request; urllib.request.urlopen("http://127.0.0.1:8147/health", timeout=1).read()' >/dev/null 2>&1 || {
  echo "wellness planner service failed to start" >&2
  [ -f /tmp/wellness-planner.log ] && cat /tmp/wellness-planner.log >&2 || true
  exit 1
}

rm -rf /services/wellness-planner /opt/wellness-planner/seed
