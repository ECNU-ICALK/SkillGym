# Inputs And Outputs

- Accept local file paths only.
- Require explicit output path(s) or an explicit output directory before running the CLI.
- If the user did not specify output location, the agent must choose one and tell the user first.
- Use the `remove` subcommand explicitly, for example:
  - `node scripts/run.mjs remove <input> --output <file>`
  - `node scripts/run.mjs remove <input-dir> --out-dir <dir>`
- Return the final written file path(s).
