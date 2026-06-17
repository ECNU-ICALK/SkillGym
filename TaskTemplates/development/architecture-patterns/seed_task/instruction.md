You need to deliver a local timetable query integration for a regional transit partner.

Input data is in `/app/workspace/data/`:
- `gtfs/agency.txt`: agency base information
- `gtfs/routes.txt`: route master data
- `gtfs/stops.txt`: stop and platform relationships
- `gtfs/trips.txt`: trip master data
- `gtfs/stop_times.txt`: stop-time sequence data
- `gtfs/calendar.txt`: regular service calendar
- `gtfs/calendar_dates.txt`: exception service calendar
- `seed_queries.json`: a set of sample queries
- `delivery_contract.yaml`: delivery field constraints

Your tasks
1. Review and complete the delivery implementation of the current service so that the following query capabilities satisfy the contract under the current GTFS snapshot:
- Next-departure lookup for a stop
- Route service-window summary
- Stop search

2. Generate a batch export result corresponding to the query capabilities above.

3. Ensure the query results, export results, and the existing run method are all computed from the current GTFS snapshot and satisfy this delivery contract.

Output:
- Modify the existing code under `/app/workspace/schedule_gateway/`.
- Preserve the existing startup and export entrypoints:
  - `/app/workspace/scripts/start_server.sh`
  - `/app/workspace/scripts/export_snapshot.sh`
- Generate `/app/workspace/output/schedule_snapshot.json`
  - The file must be valid UTF-8 JSON.
  - The contents must satisfy the field requirements defined in `delivery_contract.yaml`.
- After the service starts, the HTTP query capabilities must be available.

Notes:
- `delivery_contract.yaml` is the source of truth for the field and result constraints in this delivery.
- After delivery, the existing run method must remain executable.
- Do not delete existing entries in the provider catalog.
- You may add a small number of dependencies, but do not introduce components that require external accounts, external cloud permissions, or additional login steps.
- Do not modify any input data under `/app/workspace/data/`.
- Do not rewrite the task into a purely offline script.
- Do not submit precomputed export results.
- Do not evade general computation by only handling a single stop, a single route, or a single date.
