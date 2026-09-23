# Scrape Configuration Reference

For file-based service discovery, prefer explicit file globs and relabel-driven target shaping.

## File SD pattern

```yaml
scrape_configs:
  - job_name: file-sd
    file_sd_configs:
      - files:
          - /app/workspace/prometheus/inventory/*.json
          - /app/workspace/prometheus/inventory/*.yml
        refresh_interval: 5s
```

## Address rewrite pattern

If the inventory provides the host in `targets` and the port in a label:

```yaml
relabel_configs:
  - source_labels: [__address__, metrics_port]
    separator: ';'
    regex: '([^;]+?)(?::[0-9]+)?;([0-9]+)'
    replacement: '$1:$2'
    target_label: __address__
```

This pattern also works when a later manifest already stores the address with a port.

## Scope filtering pattern

When the inventory directory can contain auxiliary manifests, filter before scrape:

```yaml
relabel_configs:
  - source_labels: [bundle, lane]
    separator: ';'
    regex: release-2026-05-monitoring;primary
    action: keep
  - source_labels: [service_name]
    regex: .+
    action: keep
```
