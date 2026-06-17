You need to prepare a pre-analysis intake package for a coastal temperature anomaly screening study centered on the station and study window defined by the local contract.

Input data is located at:

- `/root/data/grids/`: candidate OISST subset files; choose the subset whose time coverage and spatial coverage match the contract and the selected station coordinates
- `/root/data/buoys/`: candidate buoy observation extracts; choose the extract whose coverage spans the contract study window
- `/root/data/metadata/`: candidate station metadata XML files; choose the file that matches the contract station and the history rule
- `/root/data/contracts/screening_contract.json`: the screening rules, output contract, and shortlist thresholds
- `/root/workspace/`: the official analysis entrypoint and the local workspace

Your tasks

1. Discover the matching local buoy extract, station metadata XML, and OISST subset from the candidate directories. Then prepare the intake summary, identify the station coordinates to use, select the nearest OISST grid point, and build the daily merged panel for the overlapping study window.

2. Summarize the data issues that could affect downstream screening and produce the ranked candidate warming windows required by the contract.

Outputs:

- `/root/output/analysis_intake.md`
  - Must include the headings:
    `Scope`, `Input summary`, `Data issues`, `Overlap window`, `Candidate windows`, `Method notes`

- `/root/output/input_summary.tsv`
  - Must use these columns in this exact order:
    `dataset_name`, `path`, `format`, `coverage_start`, `coverage_end`, `primary_dimensions_or_rows`, `key_variables`, `analysis_ready`

- `/root/output/data_issues.tsv`
  - Must use these columns in this exact order:
    `issue_id`, `dataset_name`, `severity`, `issue_type`, `affected_count`, `evidence`, `follow_up_action`

- `/root/output/daily_merged_panel.csv`
  - Must use these columns in this exact order:
    `date`, `station_id`, `station_lat`, `station_lon`, `grid_lat`, `grid_lon`, `total_timestamp_rows`, `distinct_utc_hours`, `hour_coverage_ratio`, `valid_wtmp_obs`, `wtmp_completeness_ratio`, `valid_wspd_obs`, `wspd_completeness_ratio`, `mean_buoy_wtmp_c`, `max_wind_speed_mps`, `oisst_sst_c`, `oisst_anom_c`

- `/root/output/candidate_windows.csv`
  - Must use these columns in this exact order:
    `rank`, `start_date`, `end_date`, `n_days`, `window_mean_sst_anom_c`, `window_mean_buoy_wtmp_c`, `window_min_hour_coverage_ratio`, `window_min_wtmp_completeness_ratio`, `selection_note`

Notes:

- Use `/root/data/contracts/screening_contract.json` as the source of truth for the station to screen, the study window, candidate-file selection rules, cleaning rules, daily quality thresholds, shortlist thresholds, top-k limit, and required output values.
- Resolve the matching input files, station coordinates, grid mapping, overlap window, text parsing logic, and daily aggregation logic from the local inputs and the contract.
- The merged panel and shortlist must be reproducible from the local data without manual judgment calls.
- In `analysis_intake.md`, explicitly name the selected buoy extract, metadata XML, OISST subset, selected grid point, and the main input issues affecting downstream screening.
- Keep row counts based on parsed observation rows, and keep malformed or non-data lines out of the daily metrics.
- Start with the local preflight probe at `/root/workspace/probe_intake.py` if it is available in the runtime. Treat its JSON output as the output-conventions contract for dataset labels, issue vocabulary, and numeric presentation.
- The following command must successfully generate the results:

```bash
python /root/workspace/run_marine_heat_intake.py --data /root/data --output /root/output
```

- Do not modify input data, test files, environment baselines, or dependency configuration.
- Do not hand-write the final output files, and do not hard-code the final shortlist.
- You may add helper scripts, but the official entrypoint must still write the results to `/root/output`.
