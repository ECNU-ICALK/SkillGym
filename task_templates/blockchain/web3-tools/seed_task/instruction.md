You need to prepare a cross-exchange daily surveillance delivery for the `marketwatch` Python service.

Input data is available in:

- `/app/data/contracts/surveillance_contract.json`: tracked symbols, thresholds, output field order, and severity mapping
- `/app/data/task_manifest.json`: task manifest and the live market-data service entrypoint
- `/app/data/reference/market_reference.csv`: older market naming reference for context
- `/app/data/service_fixtures/market_data.json`: task-side source package used by the delivery manifest
- `/app/workspace/marketwatch/`: current project workspace and project entrypoint

Your task:

1. Use `/app/workspace/marketwatch/` to prepare the surveillance outputs required by the contract for every in-scope market.
2. Treat the live market-data service described by `/app/data/task_manifest.json` as the authoritative source for market coverage and daily OHLCV payloads.
3. Produce a delivery that stays stable for the same inputs.

Output:

- `/app/output/surveillance/market_report.json`
  - UTF-8 encoded JSON
  - Top-level fields must be:
    `report_id`
    `as_of_date`
    `analysis_window_days`
    `symbols`
    `exchange_summary`
    `coverage_summary`
  - Each symbol entry must include:
    `canonical_symbol`
    `markets`
    `cross_exchange`
  - Each market entry must include:
    `exchange`
    `native_symbol`
    `canonical_symbol`
    `latest_date`
    `latest_close`
    `return_1d`
    `return_7d`
    `return_30d`
    `quote_volume_7d_usd`
    `avg_spread_bps_7d`
    `bar_count`
    `status`
  - Each `cross_exchange` entry must include:
    `best_return_30d_exchange`
    `lowest_spread_exchange`
    `close_gap_bps`
    `has_full_coverage`
    `alert_codes`

- `/app/output/surveillance/liquidity_alerts.csv`
  - UTF-8 encoded CSV
  - Header must be:
    `canonical_symbol,exchange,alert_code,observed_value,threshold,severity`
  - Must contain one row for every triggered market-level alert
  - Rows must be sorted by `canonical_symbol`, `exchange`, `alert_code`

- `/app/output/surveillance/source_manifest.json`
  - UTF-8 encoded JSON
  - Top-level fields must be:
    `source_files`
    `source_sha256`
    `records_used`
    `contract_symbols`
    `exchanges`
  - `source_files` must list every consumed input file path in sorted order
  - `records_used` must map every in-scope market to its consumed bar count using the exact key format `exchange:native_symbol`
  - Keep the authoritative native symbol text exactly as reported by the live catalog for those keys
  - `exchanges` must be the sorted distinct exchange names represented in the delivery

- `/app/output/surveillance/runbook.md`
  - UTF-8 encoded Markdown
  - Must contain the headings:
    `Collection`
    `Checks`
    `Outputs`
  - The `Collection` section must name the manifest step and mention `/api/manifest`

Notes:

- Symbol scope, alert thresholds, field ordering, and alias handling must follow `/app/data/contracts/surveillance_contract.json`.
- The reference export is supporting context and does not define the full market set.
- Keep both the exchange-native symbol and the canonical symbol in the market-level output rows.
- The final delivery must come from the project in `/app/workspace/marketwatch/`.
- Derive all reported values from the provided inputs and the local service responses.
- Do not modify the input data files.
- Do not modify tests, verifier files, task metadata, or environment files.
- Do not bypass `/app/workspace/marketwatch/` with a separate throwaway implementation outside the workspace.
- Do not hand-write the final answer files.
