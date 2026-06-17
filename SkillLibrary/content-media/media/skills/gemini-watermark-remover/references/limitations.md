# Limitations

- This Skill is a thin wrapper over the `gwr` CLI. In this repo it prefers local `bin/gwr.mjs`; in standalone installs it first looks for `gwr` on PATH and can fall back to `pnpm dlx @pilio/gemini-watermark-remover`. For staged rollouts or local validation, the package spec can be overridden with `GWR_SKILL_CLI_SPEC`.
- Input sources are local files; remote URLs are out of scope.
- The Skill does not implement watermark-removal logic directly.
