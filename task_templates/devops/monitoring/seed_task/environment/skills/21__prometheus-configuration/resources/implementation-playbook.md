# Prometheus Implementation Playbook

Use this playbook when the task requires a complete Prometheus bundle rather than a single scrape job.

## Harbor-style inventory bundle checklist

1. Keep the bundle inventory-driven with `file_sd_configs`.
2. Read both `*.json` and `*.yml` target files when the inventory directory may receive new manifests.
3. Filter discovery scope early with relabel `keep` rules when the same directory can contain auxiliary manifests.
4. Keep only targets that provide the service identity needed by downstream aggregation.
5. If target entries carry transport fields such as port and path, rewrite `__address__` and `__metrics_path__` from those labels instead of hardcoding endpoint lists.
6. When target addresses may already include a port, strip the old port before appending the inventory port.
7. Aggregate service-level recording rules over all endpoints that share the same service label.
8. Before finishing, prove that the bundle still discovers a later manifest in the same inventory directory without editing the config again.

## Recommended relabel pattern for file_sd inventories

```yaml
scrape_configs:
  - job_name: harbor-bundle
    file_sd_configs:
      - files:
          - /app/workspace/prometheus/inventory/*.json
          - /app/workspace/prometheus/inventory/*.yml
        refresh_interval: 5s
    relabel_configs:
      - source_labels: [bundle, lane]
        separator: ';'
        regex: release-2026-05-monitoring;primary
        action: keep
      - source_labels: [service_name]
        regex: .+
        action: keep
      - source_labels: [__address__, metrics_port]
        separator: ';'
        regex: '([^;]+?)(?::[0-9]+)?;([0-9]+)'
        replacement: '$1:$2'
        target_label: __address__
      - source_labels: [metrics_path]
        regex: '(.+)'
        replacement: '$1'
        target_label: __metrics_path__
      - source_labels: [service_name]
        regex: '(.+)'
        replacement: '$1'
        target_label: service
```

Notes:

- Do not replace the non-empty `service_name` keep rule with a fixed service-name whitelist.
- Do not convert the seed inventory into `static_configs`; later manifests must flow through the same `file_sd` job.
- It is fine to require non-empty `service_name` for service-level aggregation, but avoid extra relabel `keep` rules that only fit the current seed files if the task brief says the directory may receive later manifests.

## Pre-handoff self-check

After the base bundle is healthy, add a temporary manifest under `/app/workspace/prometheus/inventory/` and confirm all of the following before removing or leaving the file:

1. A same-bundle, same-lane target with `service_name: smoke-probe` and `targets: ["127.0.0.1:18086"]` appears in `/api/v1/targets` within the existing `file_sd` job.
2. A same-bundle target on another lane does not appear in the formal scrape scope.
3. A target missing `service_name` does not appear in the formal scrape scope.

If this self-check fails, the bundle is still too specific to the seed manifests.

## Service-level rules

- Request rate: `sum by (bundle, lane, service) (rate(harbor_http_requests_total[10s]))`
- Error rate: divide the `5xx` request rate by the total request rate with `clamp_min`
- P95 latency: `histogram_quantile` over `sum by (bundle, lane, service, le)`

## Common failure modes

- Appending a new port onto an address that already contains a port, producing an invalid target.
- Scraping auxiliary manifests because discovery scope was not narrowed with `keep` rules.
- Scraping unlabeled auxiliary targets that cannot be aggregated at the service level.
- Replacing the non-empty `service_name` keep rule with a fixed service-name whitelist, which breaks discovery of later valid manifests in the same bundle.
- Aggregating only one endpoint of a multi-endpoint service.
- Building alert rules directly from raw metrics instead of the service-level recording rules.
