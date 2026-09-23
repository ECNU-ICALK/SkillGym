# Directory Naming Migration

This update is limited to three top-level directory names, their path references, and the paper-oriented README. It does not migrate data to Hugging Face or change task-generation, repair, or verification criteria.

## Paths

| Previous path | Current path |
| --- | --- |
| `SkillLibrary/` | `skill_library/` |
| `TaskTemplates/` | `task_templates/` |
| `TaskBuilder/` | `task_builder/` |

Update local shell scripts and saved commands to use the current paths. No filesystem aliases for the old directory names are created.

The `skill_library/` and `task_templates/` subtrees retain their original file contents, permissions, and internal directory structures. Names such as `SKILL.md`, `task.toml`, `instruction.md`, `environment/`, `tests/`, `solution/`, `seed_task/`, category slugs, and skill slugs are unchanged. Task/template IDs and runtime output names remain unchanged.

## Default Resource Paths

Bundled templates now resolve to `<repository>/task_templates` based on the location of `task_builder/src/utils.ts`, rather than `process.cwd()`. The default output root is `<repository>/outputs`. This makes defaults consistent when starting from the repository root, `task_builder/`, or another working directory.

Existing explicit `--template-root`, `--skill-dir`, and `--output-root` arguments remain supported. Relative arguments are still interpreted from the process working directory; npm runs package scripts inside the package directory.

## Existing Data and Local Installations

`Trajectories/` and its Git LFS attributes are unchanged. HF repository contents, visibility, dataset labels, and model checkpoints are not modified. Keep using the current data locations until a separately validated migration is completed.

An existing ignored `TaskBuilder/node_modules/` directory is local state, not part of the tracked rename. Reinstall with `npm --prefix task_builder ci`. Preserve any locally generated outputs before cleaning an old checkout.

## Checks

Run the commands in the README's Development Checks section. The new `repo_paths.test.ts` covers the renamed default paths and explicit external template roots. The CI workflow runs type checking and the builder test files without model-provider credentials or a sandbox job.

Static/unit checks are not an end-to-end environment-generation run and do not reproduce the paper's experimental scores.
