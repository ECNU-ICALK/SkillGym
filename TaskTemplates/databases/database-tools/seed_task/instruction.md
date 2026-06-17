You need to finish the first weekday rapid-transit schedule release for a service planning team. The in-container PostgreSQL service is part of the required workflow, and the team needs a rebuilt schedule warehouse plus two analysis deliverables before the next planning review.

Input data is located at:

- `/root/data/gtfs/agency.txt`: agency metadata for the transit feed.
- `/root/data/gtfs/routes.txt`: route identities, route types, and public line names.
- `/root/data/gtfs/stops.txt`: stop and parent-station metadata.
- `/root/data/gtfs/trips.txt`: scheduled trip definitions and service IDs.
- `/root/data/gtfs/stop_times.txt`: ordered stop-level schedule events for each trip.
- `/root/data/gtfs/calendar.txt`: base weekly service calendars.
- `/root/data/gtfs/calendar_dates.txt`: added and removed service dates.
- `/root/data/release_contract.json`: release scope, business rules, output rules, and review checkpoints for this release.
- `/root/data/reference/`: field notes and source metadata for the shipped GTFS feed.

Your tasks

1. Build the local PostgreSQL release workflow, including the required migration SQL assets and the managed relations needed for this release package.
2. Load the shipped GTFS schedule files into the local PostgreSQL workflow and use the shipped contract and reference material to derive the in-scope weekday release outputs.
3. Keep repeated runs with the same inputs consistent, and make the emitted migration SQL sufficient to rebuild the managed downstream relations after the raw GTFS tables have been loaded.

Output

1. `/root/output/weekday_station_window_panel.csv`

The CSV must include these columns in this exact order:

- `service_date`
- `route_family`
- `route_id`
- `route_short_name`
- `direction_id`
- `parent_station_id`
- `parent_station_name`
- `window_name`
- `scheduled_trip_count`
- `first_departure_local`
- `last_departure_local`

Rules:

- Use one row for every qualifying parent-station, service-date, route, direction, and service-window combination required by the contract.
- `scheduled_trip_count` must stay machine-readable as an integer.
- `first_departure_local` and `last_departure_local` must use local wall-clock time in `HH:MM:SS` format when service exists for that row.

2. `/root/output/terminal_service_gap_leaderboard.tsv`

The TSV must include these columns in this exact order:

- `snapshot_date`
- `route_family`
- `route_id`
- `route_short_name`
- `direction_id`
- `window_name`
- `rank`
- `terminal_station_id`
- `terminal_station_name`
- `active_service_days`
- `scheduled_departure_count`
- `median_headway_minutes`
- `p90_headway_minutes`
- `max_headway_minutes`
- `service_gap_score`

Rules:

- `rank` must stay machine-readable as a positive integer.
- Headway columns must stay numeric and remain on their minute scale.
- `service_gap_score` must stay numeric.

3. `/root/output/migrations/`

Create these files exactly:

- `/root/output/migrations/001_raw_gtfs.sql`
- `/root/output/migrations/002_service_core.sql`
- `/root/output/migrations/003_release_marts.sql`

Rules:

- All three files must be valid UTF-8 SQL text.
- They must run in lexical order against the local PostgreSQL instance after the provided init helper starts the database.
- After `001_raw_gtfs.sql` creates the raw layer and the shipped GTFS text files are loaded into those raw tables, `002_service_core.sql` plus `003_release_marts.sql` must be enough to rebuild the managed downstream relations on the same PostgreSQL database without extra manual steps.
- That replay path may rely only on the emitted SQL files plus the loaded raw GTFS tables.
- You may create additional helper tables, views, materialized views, and indexes when they support the release workflow.

4. `/root/output/release_notes.md`

- Must include the headings `Scope`, `Migration order`, `Panel checks`, and `Leaderboard checks`.
- Mention every terminal station that appears in `terminal_service_gap_leaderboard.tsv`.
- Mention the boundary dates defined in `release_contract.json`.

Notes

- Use the shipped contract and reference files as the authority for service scope, date handling, station rollups, output rules, and release checks.
- Derive the deliverables from the shipped inputs and contract rules. Do not hard-code station IDs, ranked outputs, or summary values for one sample.
- The SQL migration files must be sufficient to rebuild the managed downstream relations from the loaded raw GTFS tables on a rerun. Do not depend on precomputed answer files, manual follow-up SQL, post-migration Python data patches, or derived data that lives only outside PostgreSQL.
- Do not modify input data, test files, environment baselines, or dependency configuration.
- You may add helper scripts under `/root/workspace/`, but the required deliverables must be written to `/root/output/`.
- Local PostgreSQL staging helpers are available in `/root/workspace/bin/`.
- The required command must initialize the local PostgreSQL service, rebuild the managed release schemas and deliverables from the current inputs, and leave the database available for follow-up SQL checks.
- Assume prior runs may already have created the managed schemas and tables in the same local PostgreSQL instance. Running the required command again with the same or updated inputs must still produce the current deliverables cleanly.

The following command must write the deliverables:

```bash
python /root/workspace/run_rapid_transit_release.py --data /root/data --output /root/output
```
