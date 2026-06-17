You need to prepare a release delivery for the `airdesk` command-line utility.

Input data is available in:
- `/app/data/ourairports/countries.csv`: country reference data
- `/app/data/ourairports/regions.csv`: region reference data
- `/app/data/ourairports/airports.csv`: airport catalog snapshot
- `/app/data/ourairports/runways.csv`: runway metadata
- `/app/data/ourairports/airport-frequencies.csv`: airport radio frequency metadata
- `/app/data/contracts/release_contract.json`: release version, artifact naming, smoke scenarios, and output schema
- `/app/workspace/airdesk/`: current project workspace and project entrypoints

Your task
1. Build the required release outputs from the provided data and the project in `/app/workspace/airdesk/`.
2. You may add or adjust code, scripts, and build configuration inside the workspace when needed, but the final delivery must still come from the project in `/app/workspace/airdesk/`.
3. Make the delivery stable for the same inputs, and ensure the packaged CLI artifact matches the manifest, checksum file, command catalog, and smoke expectations.

Output:

- `/app/output/release/release_manifest.json`
  - UTF-8 encoded JSON
  - Top-level fields must be:
    `package_name`
    `version`
    `artifact_name`
    `entrypoint`
    `build_target`
    `source_files`
    `source_sha256`
    `source_row_counts`
    `smoke_cases`
  - `build_target` must be the make target used for the packaged release that backs the final delivery
  - `source_files` must list the five CSV inputs in the order defined by the contract
  - `source_sha256` must map each source file name to its SHA-256 digest
  - `source_row_counts` must map each source file name to its row count
  - `smoke_cases` must list every scenario from the contract in order

- `/app/output/release/command_catalog.md`
  - UTF-8 encoded Markdown
  - Must contain the headings:
    `Build`
    `Smoke checks`
    `Examples`

- `/app/output/release/smoke_expected.json`
  - UTF-8 encoded JSON
  - Must contain one entry per smoke scenario from the contract
  - Each entry must define the expected stdout payload for the packaged CLI command

- `/app/output/release/sha256sums.txt`
  - UTF-8 encoded text
  - Must include SHA-256 lines for the packaged artifact, `release_manifest.json`, and `smoke_expected.json`

- `/app/output/release/`
  - Must contain the packaged CLI artifact named by the contract
  - The packaged CLI must support the smoke scenarios from the contract
  - The packaged CLI must be runnable after unpacking the release artifact in a clean directory

Notes:
- Version, artifact naming, smoke scenarios, and output scope must follow `/app/data/contracts/release_contract.json`.
- `command_catalog.md` must reflect the build, packaging, and smoke-check command surface provided by the workspace project.
- The smoke expectations must be computed from the provided data snapshot; do not hardcode command outputs.
- The packaged artifact must be produced by the workspace project and must include the CLI entrypoint declared in the manifest.
- Smoke expectations must be generated for the packaged CLI delivered in this task.
- Do not modify the input data files.
- Do not write the final answer files by hand.
- Do not bypass `/app/workspace/airdesk/` by building a separate throwaway implementation elsewhere.
- You may add helper files, but the required outputs must be written under `/app/output/release/`.
