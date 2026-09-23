You need to complete this monitoring-configuration delivery for a Harbor-style service bundle and make the service-level summary output follow the contract requirements.

Input data is in `/app/data/`:
- `services/`: service inventory, port information, and delivery-batch information
- `telemetry_reference/`: metric samples and field references compiled from public sources
- `contracts/service_contract.json`: the required service list and summary-field contract that must be covered
- `contracts/summary_contract.json`: summary rules, service scope, and batch requirements
- `contracts/alert_policy.json`: alert severity rules and threshold requirements
- `docs/task_brief.md`: business background, delivery requirements, and limitation notes

Your tasks
1. Based on the runtime environment already provided in the container, complete the monitoring configuration content required for this delivery.
2. Make the monitoring summary for the target services available according to the contract requirements, covering request volume, error rate, latency, and alert severity results.
3. The formal summary must count only the targets defined by `summary_contract.json`; auxiliary targets in the same directory must not be mixed into the collection scope or formal summary for the current bundle.
4. The delivery configuration must continue reading the target-level scrape fields provided by inventory entries. Later, additional supported-format manifest files will be added to the same inventory directory, and they must also be discovered through this same delivery path.
5. Complete the delivery using the control mechanisms already present in the environment.
6. Write the final result to `/app/output/monitoring_bundle_report.json` in the following format:

```json
{
  "bundle_id": "<bundle id>",
  "monitoring_ready": true,
  "healthy_target_count": 0,
  "services": {
    "<service-name>": {
      "request_rate_rps": 0.0,
      "error_rate_pct": 0.0,
      "p95_latency_ms": 0.0,
      "slo_state": "healthy"
    }
  },
  "page_alerts": ["<service-name>"],
  "ticket_alerts": ["<service-name>"]
}
```

Output:
- Only `/app/output/monitoring_bundle_report.json` needs to be submitted
- The JSON must be valid UTF-8, and the field names must match the contract above exactly
- Although `healthy_target_count` retains its historical field name, in this task it must be filled with the "number of distinct services currently included and aggregatable within the formal summary scope." For the same service with multiple endpoints, count it only once; services whose `slo_state` is `page` or `ticket` must still be counted as long as they are currently scrapeable and aggregatable
- `services` must cover every service listed in `service_contract.json`
- `page_alerts` and `ticket_alerts` may be empty arrays, but the fields must remain present

Notes:
- You must complete the task using the existing delivery path already provided in the container. Do not switch to another monitoring system, and do not bypass the existing delivery requirements through a substitute implementation.
- After delivery is complete, this delivery path will continue to be called to read the current bundle state, so do not implement it as a one-off frontend composition or temporary result export only.
- Replacing the existing delivery path, removing functionality to avoid the problem, disabling checks, short-circuiting the flow, or rewriting existing functionality to evade the requirements is explicitly forbidden.
- Do not modify the input data under `/app/data/`, and do not fabricate monitoring results, alert results, or the final output.
- You may read logs, state files, runtime directories, and existing configuration. No additional output format is required beyond the JSON contract.
