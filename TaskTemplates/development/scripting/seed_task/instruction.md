You need to fix an overnight airport report rebuild task.

Input data is in `/app/data/ourairports/`:
- `countries.tsv`
- `regions.tsv`
- `airports.tsv`
- `runways.tsv`

The current production symptoms are:
- The country-level summary and region-level ranking generated from the same overnight input batch sometimes do not match each other.
- After a report rebuild fails, downstream consumers sometimes still read old outputs that appear to be "completed."
- Different overnight jobs sometimes reuse the same temporary working root directory, and different runs must not reuse one another's intermediate results.
- The orchestrator sometimes terminates the current attempt before the job has actually reached the data-processing stage, then immediately retries the same chain.
- This task pipeline does not provide enough run-to-run consistency.

Your tasks
1. Fix `/app/bin/rebuild_airport_reports.sh` and any scripts in the existing processing chain that need adjustment so the task can run directly in the container and support repeated execution.
2. Keep the existing shell entrypoint and this real processing chain. Do not replace it with another standalone implementation, and do not turn the existing shell entrypoint into a thin wrapper that only forwards to some other primary implementation.
3. After a successful run, make the task generate the following files:
   - `/app/output/country_airport_summary.csv`
   - `/app/output/region_priority_report.json`
   - `/app/output/rebuild.log`

Output:
- `/app/output/country_airport_summary.csv`
  - UTF-8 encoded and must include a header row
  - The header must be:
    `country_code,country_name,airport_count,open_airport_count,scheduled_open_airport_count,runway_count,longest_runway_ft`
  - Each row corresponds to one country
  - The result must be stably sorted by `country_code` in ascending order
  - Numeric columns must use decimal integers
  - When a country has no available runway length, `longest_runway_ft` must remain an empty string

- `/app/output/region_priority_report.json`
  - UTF-8 encoded
  - Must be valid JSON
  - The top-level structure must be:
    `{"generated_from":"ourairports","regions":[...]}`
  - Each object in `regions` must contain the following fields:
    `region_code`
    `region_name`
    `country_code`
    `country_name`
    `open_airport_count`
    `scheduled_open_airport_count`
    `runway_count`
    `longest_runway_ft`
  - `longest_runway_ft` must remain an empty string when there is no available runway length
  - The ranking order must be stable and repeatable
  - `regions` must be sorted by `scheduled_open_airport_count` descending; if tied, then by `open_airport_count` descending; if still tied, then by `region_code` ascending

- `/app/output/rebuild.log`
  - Records information about this run
  - If this execution fails, `country_airport_summary.csv` and `region_priority_report.json` must not be left in the output directory in an apparently "completed" state
  - "Failure" here includes missing required inputs, stage-script errors, and mid-run termination; you must not handle only some failure scenarios
  - If this execution fails or exits partway through, the output directory must not retain this run's internal coordination directories, lock files, or other intermediate traces; at most, only the current run log may remain

Notes:
- You may use only the input data provided under `/app/data/ourairports/` to build the reports.
- Callers may continue using the directory override behavior already exposed by the current script to specify the data directory, output directory, and temporary working directory. After the fix, those existing runtime conventions must still be supported.
- The temporary working directory provided by the caller may be only a shared temporary root directory. Different executions must not directly reuse the same intermediate filenames, and an interrupted run must not leave its temporary files behind for the next run.
- Even if the task is terminated during directory setup, lock acquisition, or intermediate-directory creation, that attempt must not leave old deliverables in the output directory or leave this run's internal coordination traces in the shared temporary root.
- The output directory will be consumed directly downstream as the delivery directory for this report run. When the task ends, the directory must not contain internal control files or temporary directories beyond the actual deliverables.
- It is explicitly forbidden to replace the real chain, remove functionality to avoid the problem, submit precomputed results directly, rely only on manually generated final files, or skip the existing shell entrypoint and submit separately.
- Do not modify the input data files themselves.
- The input includes closed airports and empty fields, and you must not work around this by dropping entire classes of records.
- The output directory will be reused, so the task must support repeated execution.
- Deliverables in the output directory will be consumed directly downstream, so internal control traces must not be mixed into the final delivery directory.
