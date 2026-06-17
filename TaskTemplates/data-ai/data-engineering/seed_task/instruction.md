You are taking over a local ClickHouse data pipeline in `/app/workspace/`. It is supposed to load two months of NYC Yellow Taxi trip data and the Taxi Zone dimension table into the container's local ClickHouse, and produce daily and monthly analytics outputs for the operations team. Right now, the existing pipeline produces incorrect results; some downstream objects are missing or their definitions are inconsistent.

Input data is in `/app/workspace/data/`:
- `yellow_tripdata_2023-01.parquet`
- `yellow_tripdata_2023-02.parquet`
- `taxi_zone_lookup.csv`
- `trip_record_user_guide.pdf`
- `data_dictionary_trip_records_yellow.pdf`

The provided run entrypoints and related code are in `/app/workspace/`:
- `run_pipeline.sh`: the unified entrypoint for rebuilding the pipeline locally; do not change the path or filename
- `pipeline/`
- `sql/`

Your tasks
1. Fix the existing local ClickHouse loading and transformation pipeline so that `run_pipeline.sh` can rebuild the full results from the two Parquet files above and the zone lookup dimension table. Preserve the existing directory structure, run entrypoints, and the real data pipeline; do not replace ClickHouse with another implementation.
2. After the pipeline finishes, it must produce and keep the following results usable:
   - Table `daily_borough_metrics` in ClickHouse database `analytics`
   - Table `top_zone_routes` in ClickHouse database `analytics`
   - File `/app/workspace/output/summary.json`
3. Satisfy the following business definitions:
   - Both months of Parquet inputs must be included in computation; you must not process only a single month.
   - `daily_borough_metrics` must aggregate by `service_date` and `pickup_borough`, and include at least `trip_count`, `gross_revenue`, `avg_trip_miles`, `avg_tip_pct`, `airport_trip_count`.
   - `airport_trip_count` counts valid trips whose pickup or dropoff is in an airport service zone.
   - `top_zone_routes` must produce the top 20 high-revenue route rankings for each calendar month, and include at least `service_month`, `pickup_zone`, `dropoff_zone`, `trip_count`, `gross_revenue`, `avg_duration_minutes`, `revenue_rank`.
   - Aggregated results must include only trips that are business-valid; records that are clearly invalid, missing critical fields, or cannot be mapped to zones must not enter the final statistics.
   - `avg_tip_pct` must be computed only from records where tip percentage is computable.

Output
- `/app/workspace/output/summary.json` must be valid UTF-8 JSON and include at least the following fields:
  - `source_months`
  - `raw_trip_rows`
  - `accepted_trip_rows`
  - `daily_borough_metrics_rows`
  - `top_zone_routes_rows`
- `source_months` must be exactly `["2023-01", "2023-02"]` in that order.
- After `run_pipeline.sh` completes, the two ClickHouse tables above must be directly queryable, and `summary.json` must be regenerated from the current source data.

Notes
- Do not delete required downstream tables, output files, or any input data to evade the issues.
- Do not replace the real pipeline with a solution that only uses pandas, SQLite, static CSV/JSON exports, or any other approach that bypasses ClickHouse.
- Do not hard-code final results, do not submit precomputed answer files, and do not modify source data to evade errors.
- Do not evade issues by creating empty tables, writing placeholder results, or skipping the actual loading and transformation steps.
- You may add helper scripts or SQL within the existing workspace, but you must preserve the existing entrypoint paths and deliverable names.
