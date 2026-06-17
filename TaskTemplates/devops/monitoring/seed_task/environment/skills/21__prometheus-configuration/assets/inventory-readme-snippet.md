With this Prometheus workflow:

- Keep discovery inventory-driven and continue watching both `*.json` and `*.yml` manifests in this directory.
- Restrict the formal bundle scope before scrape with relabel `keep` rules on the expected `bundle` and `lane`.
- Keep only targets that carry a non-empty `service_name`, because downstream service-level aggregation depends on that identity.
- Do not hardcode the keep rule to the current contract service names. Later manifests in the same formal bundle may introduce additional valid service labels such as smoke probes, and they still need to be discovered.
- When rewriting `__address__` from `targets` plus `metrics_port`, allow for target addresses that may already contain a port and replace the old port instead of appending a second one.
- Before handoff, drop in a temporary same-bundle `smoke-probe` manifest and verify that the existing `file_sd` job discovers it without another config rewrite; also verify that a different lane or a target missing `service_name` stays out of the formal scrape scope.
