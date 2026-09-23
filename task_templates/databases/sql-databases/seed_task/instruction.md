You need to build an indexed airport-zone rolling demand mart for a transportation planning team.

Input data is located at:

- `/root/data/dispatch_batch_a.csv`: airport-linked NYC taxi trip export batch A.
- `/root/data/dispatch_batch_b.csv`: airport-linked NYC taxi trip export batch B.
- `/root/data/dispatch_batch_c.csv`: airport-linked NYC taxi trip export batch C.
- `/root/data/dispatch_batch_d.csv`: airport-linked NYC taxi trip export batch D.
- `/root/data/taxi_zone_lookup.csv`: taxi zone and borough reference data.
- `/root/data/analysis_contract.json`: candidate market rules, rolling window rules, snapshot dates, ranking weights, and benchmark requirements.
- `/root/data/reference/`: field guides for the trip export.

Your tasks

1. Harmonize the four trip batches into a reusable local PostgreSQL fact layer for candidate Manhattan zones and airport-linked trips.
2. Produce a zero-filled daily mart and a rolling snapshot leaderboard from the contract rules.
3. Deliver a reusable SQL pack for the local PostgreSQL data source. The SQL pack may create helper tables, materialized views, and indexes if they support repeated analytical runs.

Output

1. `/root/output/airport_zone_daily_mart.csv`

The CSV must include these columns in this exact order:

- `service_date`
- `period`
- `airport_code`
- `zone_id`
- `zone_name`
- `borough`
- `airport_trip_count`
- `total_trip_count`
- `airport_trip_share`

Numeric metric columns must stay as machine-readable numeric values.

2. `/root/output/airport_zone_snapshot_leaderboard.tsv`

The TSV must include these columns in this exact order:

- `snapshot_date`
- `period`
- `airport_code`
- `rank`
- `zone_id`
- `zone_name`
- `borough`
- `active_days_in_window`
- `rolling_airport_trip_count`
- `rolling_total_trip_count`
- `rolling_airport_trip_share`
- `rolling_opportunity_score`

Numeric metric columns must stay as machine-readable numeric values.

3. `/root/output/query_pack.sql`

- Must be valid UTF-8 SQL text.
- Organize reusable queries with numbered comments such as `-- Query 1:`.
- It must run against the local PostgreSQL source tables after `/root/workspace/bin/init_airport_ops.sh`.
- It must recreate these PostgreSQL objects as reusable analysis relations: `analysis.trip_fact_normalized`, `analysis.airport_zone_daily`, `analysis.airport_zone_rolling_7d`, and `analysis.airport_zone_snapshot_leaderboard`.
- Use `CREATE MATERIALIZED VIEW` for the reusable analysis layers in `query_pack.sql` rather than plain `CREATE VIEW` for all four required `analysis.*` objects.
- It may create additional helper tables, materialized views, and indexes when needed.
- The verifier will rerun `query_pack.sql` against the same local PostgreSQL instance. Your final pipeline must initialize the local PostgreSQL service and leave the database available for that replay step.

4. `/root/output/benchmark_report.md`

- Must include the headings `Scope`, `Daily mart`, `Snapshot leaderboard`, and `Index strategy`.
- Mention every ranked zone that appears in `airport_zone_snapshot_leaderboard.tsv`.
- Explicitly mention the analysis-window boundary dates `2023-01-02` and `2023-02-07`.

Notes

- Use New York local time for all period splits.
- `morning_departures` covers `06:00:00` to `10:59:59`.
- `evening_arrivals` covers `17:00:00` to `22:59:59`.
- Only weekday trips are in scope.
- Daily panel rules, rolling-window rules, snapshot dates, ranking rules, benchmark requirements, and tie-break order are defined in `analysis_contract.json`. Read that contract carefully and implement it literally.
- The daily mart is an airport-specific zero-filled panel over qualifying candidate-market zone-days, not a raw trip dump.
- `total_trip_count` is the denominator over all qualifying candidate-market trips for that zone-day and period. It is not limited to airport-linked trips.
- Compute share metrics with floating-point division and keep ranking inputs at full precision until after score-first ranking is complete.
- `airport_zone_snapshot_leaderboard.tsv` should contain only rows that survive the contract's rolling-window and eligibility rules. Some configured snapshot partitions may legitimately produce zero rows.
- Apply the contract tie-break order exactly and assign ranks with `ROW_NUMBER`-style semantics after the strict final sort.
- When `exclude_same_zone_short_hops` is enabled, exclude same-zone trips only when trip distance is strictly below `same_zone_short_hop_miles`. Trips exactly at the threshold stay in scope.
- All conclusions must come from the input data and contract rules. Do not hard-code conclusions into the deliverables.
- Do not modify input data, test files, environment baselines, or dependency configuration.
- You may add helper scripts in the workspace, but the required deliverables must be written to `/root/output`.
- Local PostgreSQL staging helpers are available in `/root/workspace/bin/`. The task data is expected to stay inside the provided container.
- The required command should call the local PostgreSQL init helper rather than assuming the database is already running, and it should not shut the database down before exiting.
- In skill-enabled runs, read the local PostgreSQL skill first. Use the task-specific playbook bundled in that skill for schema harmonization, rolling-window SQL organization, and index strategy. The task contract remains the final authority.
- The following command must write the deliverables:

```bash
python /root/workspace/run_airport_zone_analysis.py --data /root/data --output /root/output
```
