#!/bin/bash
set -euo pipefail

cat > /app/workspace/prometheus/bundle/prometheus.yml <<'EOF'
global:
  scrape_interval: 5s
  evaluation_interval: 5s

rule_files:
  - /app/workspace/prometheus/rules/*.yml

scrape_configs:
  - job_name: harbor-bundle
    file_sd_configs:
      - files:
          - /app/workspace/prometheus/inventory/*.json
          - /app/workspace/prometheus/inventory/*.yml
        refresh_interval: 5s
    relabel_configs:
      - source_labels: [__address__, metrics_port]
        regex: '([^:;]+)(:[0-9]+)?;([0-9]+)'
        replacement: '$1:$3'
        target_label: __address__
        action: replace
      - source_labels: [metrics_path]
        regex: '(.+)'
        replacement: '$1'
        target_label: __metrics_path__
        action: replace
      - source_labels: [service_name]
        regex: '(.+)'
        replacement: '$1'
        target_label: service
        action: replace
      - source_labels: [bundle]
        regex: release-2026-05-monitoring
        action: keep
      - source_labels: [lane]
        regex: primary
        action: keep
      - source_labels: [service_name]
        regex: .+
        action: keep
EOF

cat > /app/workspace/prometheus/rules/recording_rules.yml <<'EOF'
groups:
  - name: harbor-recording
    interval: 5s
    rules:
      - record: harbor:up:sum
        expr: sum by (service, lane) (up{bundle="release-2026-05-monitoring",lane="primary"})
      - record: harbor:service_request_rate_rps
        expr: sum by (service, lane) (rate(harbor_http_requests_total{bundle="release-2026-05-monitoring",lane="primary"}[10s]))
      - record: harbor:service_error_rate_pct
        expr: |
          100 *
          sum by (service, lane) (rate(harbor_http_requests_total{bundle="release-2026-05-monitoring",lane="primary",code=~"5.."}[10s]))
          /
          clamp_min(sum by (service, lane) (rate(harbor_http_requests_total{bundle="release-2026-05-monitoring",lane="primary"}[10s])), 0.0001)
      - record: harbor:service_p95_latency_ms
        expr: |
          1000 *
          histogram_quantile(
            0.95,
            sum by (service, lane, le) (
              rate(harbor_http_request_duration_seconds_bucket{bundle="release-2026-05-monitoring",lane="primary"}[10s])
            )
          )
EOF

cat > /app/workspace/prometheus/rules/alert_rules.yml <<'EOF'
groups:
  - name: harbor-alerts
    interval: 5s
    rules:
      - alert: HarborServiceDown
        expr: harbor:up:sum < 1
        for: 0s
        labels:
          severity: page
          bundle: release-2026-05-monitoring
        annotations:
          summary: "{{ $labels.service }} is down"
      - alert: HarborHighErrorRatePage
        expr: harbor:service_error_rate_pct > 5
        for: 0s
        labels:
          severity: page
          bundle: release-2026-05-monitoring
        annotations:
          summary: "{{ $labels.service }} error rate is above page threshold"
      - alert: HarborHighErrorRateTicket
        expr: harbor:service_error_rate_pct > 1 and harbor:service_error_rate_pct <= 5
        for: 0s
        labels:
          severity: ticket
          bundle: release-2026-05-monitoring
        annotations:
          summary: "{{ $labels.service }} error rate is above ticket threshold"
      - alert: HarborHighLatencyPage
        expr: harbor:service_p95_latency_ms > 600
        for: 0s
        labels:
          severity: page
          bundle: release-2026-05-monitoring
        annotations:
          summary: "{{ $labels.service }} latency is above page threshold"
      - alert: HarborHighLatencyTicket
        expr: harbor:service_p95_latency_ms > 300 and harbor:service_p95_latency_ms <= 600
        for: 0s
        labels:
          severity: ticket
          bundle: release-2026-05-monitoring
        annotations:
          summary: "{{ $labels.service }} latency is above ticket threshold"
EOF

cp /app/runtime/inventory/release-bundle.json /app/workspace/prometheus/inventory/release-bundle.json
cp /app/runtime/inventory/shadow-bundle.json /app/workspace/prometheus/inventory/shadow-bundle.json

/app/bin/start_bundle.sh
/app/bin/render_report.py
