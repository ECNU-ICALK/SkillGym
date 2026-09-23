Prometheus bundle pre-handoff checklist

1. `promtool check config /app/workspace/prometheus/bundle/prometheus.yml`
2. `promtool check rules /app/workspace/prometheus/rules/recording_rules.yml`
3. `promtool check rules /app/workspace/prometheus/rules/alert_rules.yml`
4. `curl -fsS 'http://127.0.0.1:9090/api/v1/targets?state=active'`
5. Add a temporary manifest in `/app/workspace/prometheus/inventory/` with:

```yaml
- targets:
  - 127.0.0.1:18086
  labels:
    service_name: smoke-probe
    component: smoke
    team: observability
    metrics_port: "18086"
    metrics_path: /probe/metrics
    lane: primary
    bundle: release-2026-05-monitoring
```

6. Confirm the existing Prometheus process discovers that target without replacing the job with `static_configs`.
7. Confirm a canary lane target is excluded from the formal bundle scope.
8. Confirm a target missing `service_name` is excluded from the formal bundle scope.
