You need to add an experimental configuration capability to an internal React / SSR framework so that the existing fixture app can, with the capability both enabled and disabled, complete dev startup, build/export, and result aggregation under the current delivery constraints.

Inputs are located at:
- `/app/workspace/framework/`: existing TypeScript framework code, including the config entrypoint, build pipeline, runtime code, export pipeline, and the task-provided fixture app
- `/app/workspace/data/upstream/flag_contract.json`: snapshot of the config contract and field constraints
- `/app/workspace/data/upstream/flag_behavior_notes.json`: snapshot of behavioral notes for the config
- `/app/workspace/data/upstream/docs_route_snapshot.json`: snapshot of public documentation routes and segments
- `/app/workspace/data/upstream/fixture_matrix.json`: constraints for fixtures, modes, and report fields
- `/app/workspace/scripts/`: scripts for dev startup, build/export, and report collection

Your tasks
1. Add support for the `experimental.segmentCache` configuration flag so it can be enabled and disabled via the existing configuration entrypoint.
2. Ensure the task-provided fixture app can complete the dev startup, build, and export flows in both cases: with the flag enabled and with the flag disabled.
3. Ensure the report collection entrypoint outputs execution results for both cases and generates a complete report file.
4. Ensure this configuration capability takes effect by continuing to use the existing framework code paths and existing run entrypoints.

Output:
- Directly modify existing code under `/app/workspace/framework/`.
- Keep the existing run entrypoints; validation will execute the following scripts using the repository's default method:
  - `/app/workspace/scripts/start_dev.sh`
  - `/app/workspace/scripts/build_and_export.sh`
  - `/app/workspace/scripts/collect_flag_report.sh`
- Generate `/app/workspace/output/segment_cache_report.json`:
  - The file must be valid UTF-8 JSON.
  - The content must cover both the enabled and disabled scenarios.
  - The content must match the actual execution results in the current container.

Notes:
- The dev startup, build, and export entrypoints must remain usable; do not rewrite the task into submitting static results or a one-off offline script.
- You may add necessary types, validation, config propagation, test helper code, and a small number of dependencies, but do not introduce components that require external accounts, extra cloud permissions, or manual logins.
- Do not modify input data under `/app/workspace/data/upstream/`.
- Do not evade the task by removing existing config entrypoints, export entrypoints, report entrypoints, default behavior, or the fixture app.
- Do not evade the task by adding a separate custom toggle that only serves a specific fixture.
- Do not spin up a second service, a second framework, a reverse-proxy layer, or a standalone mock flow.
- Do not hard-code the report so it only works for a fixed path, a fixed config filename, or a single fixture.
- Do not require internet access during solve; the final result must be fully based on code, data, and scripts inside the container.
