You need to prepare a weekday airport partner-zone opportunity analysis package for the airport operations planning team. The team has already placed multi-batch trip staging DBs, an airport weather snapshot, the planning contract, and field references into the local environment, but there are not yet any official delivery files.

Input data is located at:
- `/root/data/trips/airport_partner_ops.db`: a SQLite database containing `dispatch_batch_a`, `dispatch_batch_b`, `dispatch_batch_c`, `dispatch_batch_d`, and `zone_lookup`
- `/root/data/weather/airport_daily_weather.json`: daily weather snapshots for JFK, LGA, and EWR
- `/root/data/planning/analysis_contract.json`: the analysis window, airport mapping, time periods, valid-trip rules, weather bucketing, ranking rules, and output contract
- `/root/data/reference/`: zone lookup reference tables and field description documents
- `/root/workspace/`: the official analysis entrypoint and the local workspace

Your tasks

1. Based on the staging DB, weather, and the planning contract, normalize the multi-batch trip data into a consistent analysis schema, complete the weekday airport partner-zone opportunity analysis, and generate the final deliverables.

2. Deliver two support lists, `morning_departures` and `evening_arrivals`, and ensure the conclusions are traceable back to period-level aggregates and reusable query definitions.

Outputs:

- `/root/output/analysis_brief.md`
  - Must include the headings: `Scope`, `Morning departures`, `Evening arrivals`, `Weather notes`, `Method notes`

- `/root/output/source_inventory.tsv`
  - Must use these columns in this exact order: `source_name`, `path`, `grain`, `date_range`, `key_fields`, `note`
  - List only 4 input bundles: staging DB, airport weather, planning contract, reference docs

- `/root/output/quality_checks.tsv`
  - Must use these columns in this exact order: `check_id`, `dataset`, `status`, `metric_name`, `metric_value`, `note`

- `/root/output/airport_partner_zone_period_summary.csv`
  - Must use these columns in this exact order: `period`, `airport_code`, `partner_zone_id`, `partner_zone_name`, `borough`, `active_service_days`, `total_airport_trips`, `total_partner_zone_trips`, `avg_airport_trip_share`, `median_trip_duration_min`, `median_total_amount`, `weather_resilience_score`, `opportunity_score`

- `/root/output/airport_weather_sensitivity.tsv`
  - Must use these columns in this exact order: `period`, `airport_code`, `weather_bucket`, `avg_airport_trip_count`, `avg_airport_trip_share`, `avg_median_trip_duration_min`, `n_zone_days`, `vs_dry_u_test_pvalue`, `effect_direction`

- `/root/output/airport_partner_zone_rankings.tsv`
  - Must use these columns in this exact order: `period`, `airport_code`, `recommendation_type`, `rank`, `zone_id`, `zone_name`, `borough`, `active_service_days`, `avg_airport_trip_count`, `avg_airport_trip_share`, `weather_resilience_score`, `opportunity_score`, `recommended_action`, `reason_code`

- `/root/output/query_pack.sql`
  - Must be valid UTF-8 SQL text and preserve reusable key extraction queries
  - Organize key queries using numbered comments like `-- Query 1:`

Notes:

- The weekday scope, airport mapping, time window, candidate zones, valid-trip rules, weather bucketing, eligibility thresholds, ranking rules, recommendation slots, and output fields must follow `/root/data/planning/analysis_contract.json`.
- The four staging batches represent the same type of business facts, but their field naming is not consistent; you must first normalize to a unified schema before aggregation, weather comparison, and recommendation ranking.
- Time-window filtering must use the hour-of-day from `pickup_timestamp`; `morning_departures` covers `06:00:00` to `10:59:59`, and `evening_arrivals` covers `17:00:00` to `22:59:59`.
- `airport_partner_zone_period_summary.csv` must only keep `period + airport_code + partner_zone_id` combinations that actually have airport-linked trips within the analysis window.
- `total_partner_zone_trips` is the daily total trip volume for the same `period + partner_zone_id + service_date` after all filters within the corresponding time window, then aggregated to the output grain. This daily denominator panel must cover all observed service days for that `period + partner_zone_id`, not only the active days where a specific airport has airport-linked trips. `total_airport_trips` counts only the trips within that panel that satisfy the airport mapping direction.
- `active_service_days` counts, for each `period + airport_code + partner_zone_id` combination, the number of service days with at least 1 airport-linked trip.
- `avg_airport_trip_share` must be computed per service day as `airport_trip_count / partner_trip_count`, then averaged over all observed service days for that partner zone. If a given service day has no airport-linked trips for the airport, treat `airport_trip_count` for that day as `0`.
- The computation and ranking of `opportunity_score` must read the `ranking_score` definition from the contract: first normalize count/share/resilience within the same `period + airport_code`, then apply the weights and tie-break order given there to produce the support lists.
- The allowed values of `effect_direction` in `airport_weather_sensitivity.tsv` must follow `weather_effect_output.effect_direction_values` in the contract. Weather comparisons must also be based on the full `period + partner_zone_id + service_date` panel described above.
- The recommended check items and dataset naming for `quality_checks.tsv` are also defined in the contract under `quality_check_contract`.
- In `analysis_brief.md`, the `Morning departures` and `Evening arrivals` sections must explicitly name the zone names included in the final selected support lists.
- The following command must successfully generate the results:

```bash
python /root/workspace/run_airport_partner_analysis.py --data /root/data --output /root/output
```

- Do not modify input data, test files, environment baselines, or dependency configuration.
- Do not hand-write the final answer files, and do not hard-code conclusions directly into the outputs.
- Do not skip staging batch normalization, candidate zone filtering, airport mapping, weather bucketing, eligibility thresholds, or generating the two support lists.
- You may add helper scripts, but the official entrypoint must still write the results to `/root/output`.
