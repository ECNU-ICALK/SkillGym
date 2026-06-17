# Airport Zone Rolling Mart Playbook

Use this reference only for the airport rolling-mart task family.

## Recommended build order

1. Read `analysis_contract.json`.
2. Materialize small config tables inside `analysis` for:
   - airport mapping
   - period rules
   - period-airport combinations
   - snapshot dates
3. Build one normalized fact relation from the four raw dispatch batches.
4. Build the zero-filled daily mart from that fact relation.
5. Build the rolling relation from the daily mart.
6. Build the snapshot leaderboard from the rolling relation.
7. Add indexes after the final relation boundaries are fixed.
8. Export CSV, TSV, and report content from PostgreSQL results.

## Batch harmonization mapping

Normalize the four raw trip tables to these canonical columns before downstream logic:

| Canonical field | `raw.dispatch_batch_a` | `raw.dispatch_batch_b` | `raw.dispatch_batch_c` | `raw.dispatch_batch_d` |
| :--- | :--- | :--- | :--- | :--- |
| `pickup_timestamp` | `tpep_pickup_datetime` | `pickup_ts` | `pickup_at` | `trip_begin_ts` |
| `dropoff_timestamp` | `tpep_dropoff_datetime` | `dropoff_ts` | `dropoff_at` | `trip_end_ts` |
| `pickup_location_id` | `PULocationID` | `pickup_loc_id` | `pickup_location_id` | `pu_location` |
| `dropoff_location_id` | `DOLocationID` | `dropoff_loc_id` | `dropoff_location_id` | `do_location` |
| `trip_distance_miles` | `trip_distance` | `trip_distance_mi` | `trip_distance` | `trip_miles` |
| `fare_amount_usd` | `fare_amount` | `fare_amount_usd` | `fare_amount` | `fare_usd` |
| `total_amount_usd` | `total_amount` | `total_amount_usd` | `total_amount` | `total_usd` |
| `airport_fee_usd` | `airport_fee` | `airport_fee_amount` | `"Airport_fee"` | `airport_fee_paid` |

Derived fields used later:

- `service_date = pickup timestamp in local service date`
- `pickup_hour`
- `pickup_isodow`
- `trip_duration_min`
- `implied_mph`

## Candidate-market and period routing

- Candidate market comes from `analysis_contract.json`.
- For `morning_departures`:
  - candidate zone attributes come from the pickup side
  - airport matching comes from the dropoff side
- For `evening_arrivals`:
  - candidate zone attributes come from the dropoff side
  - airport matching comes from the pickup side

## Daily mart pattern

Build `analysis.airport_zone_daily` from three conceptual pieces:

1. `zone_day`
   - one row per observed `(service_date, period, zone_id, zone_name, borough)`
   - `total_trip_count` counts all qualifying candidate-market trips for that zone-day
2. `scoped_airport_pairs`
   - distinct `(period, airport_code, zone_id, zone_name, borough)` pairs that have at least one qualifying airport-linked trip somewhere in the analysis window
3. `airport_zone_day`
   - airport-linked counts by `(service_date, period, airport_code, zone_id, zone_name, borough)`

Then:

- join `scoped_airport_pairs` to `zone_day`
- left join `airport_zone_day`
- zero-fill missing airport counts with `0`
- compute `airport_trip_share` row by row after zero-fill:
  - `airport_trip_share = airport_trip_count / total_trip_count`
  - zero-filled rows keep share `0`

Do not pool totals across airport codes.

## Rolling relation pattern

`analysis.airport_zone_rolling_7d` should start from the zero-filled daily mart.

For each configured `snapshot_date`:

- window start is `snapshot_date - (service_dates_in_window - 1 days)`
- include only daily rows whose `service_date` falls in that window
- aggregate by `(snapshot_date, period, airport_code, zone_id, zone_name, borough)`

Metrics:

- `active_days_in_window = COUNT(*) FILTER (WHERE airport_trip_count > 0)`
- `rolling_airport_trip_count = SUM(airport_trip_count)`
- `rolling_total_trip_count = SUM(total_trip_count)`
- `rolling_airport_trip_share = rolling_airport_trip_count / rolling_total_trip_count`

The active-day count is airport-active day count, not all observed zone-days in the window.

## Leaderboard pattern

1. Filter rolling rows by `min_active_days_in_window`.
2. Within each `(snapshot_date, period, airport_code)` partition compute:
   - `count_component = rolling_airport_trip_count / MAX(rolling_airport_trip_count)`
   - `share_component = rolling_airport_trip_share / MAX(rolling_airport_trip_share)`
   - `active_days_component = active_days_in_window / MAX(active_days_in_window)`
3. Compute:

```text
rolling_opportunity_score =
  count_weight * count_component
  + share_weight * share_component
  + active_days_weight * active_days_component
```

4. Sort strictly by:
   - `rolling_opportunity_score DESC`
   - `rolling_airport_trip_count DESC`
   - `rolling_airport_trip_share DESC`
   - `zone_id ASC`
5. Assign rank with `ROW_NUMBER()` semantics.
6. Keep only `rank <= top_k` for the contract's `(period, airport_code)` rule.

Important:

- keep share metrics and scores at full precision before ranking
- do not normalize across different partitions
- do not pad partitions up to `top_k`
- some snapshot partitions may legitimately yield zero rows

## Query-pack and index guidance

Use `CREATE MATERIALIZED VIEW` for:

- `analysis.trip_fact_normalized`
- `analysis.airport_zone_daily`
- `analysis.airport_zone_rolling_7d`
- `analysis.airport_zone_snapshot_leaderboard`

Recommended indexes after each materialized view is created:

- `analysis.trip_fact_normalized`
  - `(period, zone_id, service_date)`
  - `(period, airport_code, zone_id, service_date)`
- `analysis.airport_zone_daily`
  - unique `(service_date, period, airport_code, zone_id)`
  - `(period, airport_code, service_date, zone_id)`
- `analysis.airport_zone_rolling_7d`
  - `(snapshot_date, period, airport_code, zone_id)`
- `analysis.airport_zone_snapshot_leaderboard`
  - `(snapshot_date, period, airport_code, rank)`

`query_pack.sql` should be replayable on an already initialized local PostgreSQL instance. Do not shut the database down after writing outputs.

## Report checklist

`benchmark_report.md` should:

- include `Scope`, `Daily mart`, `Snapshot leaderboard`, and `Index strategy`
- explicitly mention the analysis-window boundary dates `2023-01-02` and `2023-02-07`
- mention every zone that appears in the final leaderboard
- describe the index strategy in terms of the persisted PostgreSQL relations

## Mutation safety

- Do not hard-code baseline snapshot dates, ranks, or zones.
- Do not turn debugging checks into runtime assertions.
- Always read weights, snapshots, top-k values, and airport-period scope from the live contract.
