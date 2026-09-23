#!/bin/bash
set -euo pipefail

CONFIG_FILE=/app/workspace/prometheus/bundle/prometheus.yml
RECORDING_RULES=/app/workspace/prometheus/rules/recording_rules.yml
ALERT_RULES=/app/workspace/prometheus/rules/alert_rules.yml
STATE_DIR=/app/workspace/prometheus/state
LOG_FILE=/app/runtime/logs/prometheus.log

mkdir -p "$STATE_DIR" /app/runtime/logs

/app/bin/start_metrics_services.sh

promtool check config "$CONFIG_FILE" >/tmp/promtool-config.txt
promtool check rules "$RECORDING_RULES" >/tmp/promtool-recording.txt
promtool check rules "$ALERT_RULES" >/tmp/promtool-alerts.txt

if curl -fsS http://127.0.0.1:9090/-/ready >/dev/null 2>&1; then
  /app/bin/reload_bundle.sh
else
  nohup prometheus \
    --config.file="$CONFIG_FILE" \
    --storage.tsdb.path="${STATE_DIR}/tsdb" \
    --web.listen-address=127.0.0.1:9090 \
    --web.enable-lifecycle \
    >"$LOG_FILE" 2>&1 &
fi

for _ in $(seq 1 80); do
  if curl -fsS http://127.0.0.1:9090/-/ready >/dev/null 2>&1; then
    exit 0
  fi
  sleep 0.5
done

echo "prometheus did not become ready" >&2
if [ -f "$LOG_FILE" ]; then
  cat "$LOG_FILE" >&2
fi
exit 1
