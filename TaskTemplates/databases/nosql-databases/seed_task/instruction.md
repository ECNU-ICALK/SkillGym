You are completing a bike-share dispatch preparation job for the next operating window. The in-container Redis service is part of the required workflow, and the operations team needs an updated station plan plus a network summary before truck assignments are reviewed.

Input data is under `/app/workspace/`:

- `planner/`: starter Python code for the dispatch preparation job and its Redis integration.
- `data/station_information.json`: station metadata, capacity, coordinates, and region identifiers.
- `data/station_status.json`: current station availability, dock counts, and operating flags.
- `data/system_regions.json`: region identifiers and region names used by the operating team.
- `data/system_information.json`: system metadata for the current bike-share network.
- `data/dispatch_rules.json`: the current planning window, operating thresholds, region limits, and excluded stations.

## Your Task

1. Complete the provided planning job so it loads the input files, updates the Redis-backed working state, and produces the required dispatch outputs for the current window.
2. Select the stations that require `pickup` or `dropoff` actions, rank them by operational priority, and calculate how many bikes should move at each selected station.
3. Make repeated runs with the same inputs safe so the Redis state and output files stay consistent instead of accumulating duplicate planning state.

## Business Constraints

- Use `station_information.json`, `station_status.json`, `system_regions.json`, `system_information.json`, and `dispatch_rules.json` together when producing the plan.
- Keep the current entrypoint path and startup flow. Validation will run the repository's existing dispatch preparation entrypoint.
- Derive the plan from the shipped inputs. Do not hard-code station IDs, scores, move counts, or output rows for one sample.
- Keep the provided Redis service in the workflow and leave the final Redis working state queryable after the job finishes.
- Build `priority_score` from the current inputs and `dispatch_rules.priority_weights`.
- Keep `occupancy_ratio`, `target_ratio`, `region_fill_ratio`, and `region_pressure` on their ratio scale throughout planning and scoring. Do not convert them to percentages or add extra scaling constants.
- Determine `action` from the current occupancy ratio for each eligible station: use `dropoff` when `num_bikes_available / capacity <= low_fill_ratio`, use `pickup` when `num_bikes_available / capacity >= high_fill_ratio`, and skip stations in between.
- Compute `desired_bikes` as `max(1, round-half-up(target_ratio * capacity))` for the station's managed region, then compute `bike_gap` from the difference between `num_bikes_available` and `desired_bikes`.
- Compute directional region pressure against the current managed-region fill ratio: `pickup` rows must use `max(0, region_fill_ratio - target_ratio)` and `dropoff` rows must use `max(0, target_ratio - region_fill_ratio)`.
- Apply zero-side urgency only when a `pickup` station currently has `0` docks available or a `dropoff` station currently has `0` bikes available.
- Compute `bikes_to_move` from the current inputs and `dispatch_rules.max_move_per_station`. It must stay within the available movement side for the selected action: available bikes for `pickup`, available docks for `dropoff`.
- Use `priority_score = bike_gap * bike_gap_weight + capacity * capacity_weight + region_pressure * region_pressure_weight + zero_side_bonus`, where `zero_side_bonus` is included only for zero-side urgent rows.
- Use each value in `dispatch_rules.priority_weights` exactly once in that formula. Do not introduce extra multipliers, alternate weight sets, or a second scoring formula.
- Rank candidates within each managed region before applying `dispatch_rules.region_action_limits`, then produce the final plan ordering from the selected rows.
- Order the final plan by descending `priority_score`, then by `region`, `station_name`, and `station_id`.
- Keep the Redis working state queryable under the configured namespace for downstream review. It must include station objects, one selected-plan object for each selected station, selected-plan membership, a priority-ordered selected-plan index, and a manifest that points reviewers to the selected-membership key and the ordered selected-plan index key.

## Output

Write your deliverables to `/app/output/`. Create the directory if it does not exist.

1. `/app/output/rebalance_plan.csv`

The CSV must include these columns exactly:

- `station_id`
- `station_name`
- `region`
- `action`
- `priority_score`
- `bikes_to_move`
- `evidence`

Rules:

- `action` must be `pickup` or `dropoff`.
- Use one row per selected station.
- `priority_score` must be numeric.
- `bikes_to_move` must be a positive integer.
- `evidence` must be valid JSON stored in a single CSV field.
- `evidence` must expose reviewer-audit fields at the top level, including `capacity`, `num_bikes_available`, `num_docks_available`, `occupancy_ratio`, `target_ratio`, and `run_digest`.
- `evidence` should also expose the calculation inputs used for review, including `desired_bikes`, `bike_gap`, `region_fill_ratio`, and `region_pressure`.

2. `/app/output/network_summary.json`

The JSON file must include these top-level keys exactly:

- `window`
- `totals`
- `action_counts`
- `regions`
- `ingest`
- `notes`

Rules:

- `totals.plan_rows` must match the number of CSV rows.
- Include both `pickup` and `dropoff` in `action_counts`, even when one of them is `0`.
- `regions` must summarize the selected plan rows by region.
- Each region summary must include the region identifier or region name, selected row count, candidate row count, action limit, pickup/dropoff row counts, pickup/dropoff bike totals, average priority score, region fill ratio, target ratio, and eligible station count.
- The Redis manifest must identify the selected-membership key and the ordered selected-plan index key used for downstream review.
- Station objects for selected rows must expose a selected-membership flag, the selected action, and the selected bikes-to-move in the final Redis working state.

## Notes

- Do not modify files under `/app/workspace/data/`, the Redis server configuration, or the verifier files.
- Do not replace the provided service workflow with a flat-file-only path, a different database, or an extra service.
- Do not fetch more network data at solve time.
- Do not remove required functionality, bypass the provided entrypoint, or return a hand-written sample output.
- You may add helper code under `/app/workspace/`, but the only required deliverables are the two files under `/app/output/`.
