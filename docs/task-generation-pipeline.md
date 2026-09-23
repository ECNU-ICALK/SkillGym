# Task Generation Pipeline

SkillGym generates tasks by combining one reusable task template with one or more skills.

## Data prerequisites

The builder expects the two large input trees at the repository root. They are distributed as archives in the [SkillGym Hugging Face dataset](https://huggingface.co/datasets/ecnu-icalk/SkillGym) and are not tracked in GitHub:

```bash
hf download ecnu-icalk/SkillGym skill_library.tar.zst task_templates.tar.zst \
  --repo-type dataset --local-dir .hf/skillgym
tar --zstd -xf .hf/skillgym/skill_library.tar.zst
tar --zstd -xf .hf/skillgym/task_templates.tar.zst
```

After extraction, the expected paths are `skill_library/<major>/<minor>/skills/<skill>/` and `task_templates/<major>/<minor>/seed_task/`. The source commit and archive checksums are recorded in the dataset's `migration_manifest.json`.

## Inputs

- `task_templates/<major>/<minor>/seed_task`
- `skill_library/<major>/<minor>/skills/<skill>/`

Each `seed_task` directory contains the base task files, environment, solution, and tests. Each skill directory must contain `SKILL.md` and may include supporting files such as `references/`, `scripts/`, or `assets/`.

The TypeScript implementation is in `task_builder/`. Default bundled templates are resolved relative to the source module, independent of the shell working directory. The default output directory is `<repository>/outputs`; use `--output-root` to select another location. Explicit relative CLI paths continue to be resolved from the process working directory. When running `npm --prefix task_builder run ...`, npm starts the command in `task_builder/`.

## Flow

1. Load a generation unit from `--template-root`, `--template`, and one or more `--skill-dir` arguments.
2. Ask Codex to plan a derived task for the selected template and skill.
3. Materialize a task draft and run validation checks.
4. Repair the draft before runtime if validation reports issues.
5. Run runtime checks and repair failures up to the configured limits.
6. Run skill-effect evaluation with `with_skill` and `no_skill` variants.
7. Publish accepted variants into `final/`.
8. Archive traces and write `manifest.jsonl` event records.

## Runtime Requirements

The existing implementation uses the Codex SDK and runtime validation/preflight integrations. The example `.env` selects E2B and contains model-provider and sandbox credentials. Runtime services and their command-line tools must be provisioned separately; npm installation only installs the builder's JavaScript dependencies. Keep credentials outside version control.

The local `inventory` command does not execute model-based generation. The `generate-family` command can incur model and sandbox charges and uses the configured repair and time budgets. No full generation, training, or benchmark run is required for the directory migration.

## Key Options

- `--task-count`: number of derived tasks to attempt per generation unit.
- `--concurrency`: number of generation units to run in parallel.
- `--task-attempt-timeout-hours`: wall-clock budget for a single task attempt.
- `--max-task-restarts`: number of full task attempt restarts.
- `--max-pre-runtime-repair-rounds`: repair rounds before runtime checks.
- `--max-runtime-repair-rounds`: repair rounds after runtime failures.
- `--max-skill-effect-repair-rounds`: repair rounds after skill-effect failures.

## Batch Example

From the repository root:

```bash
cd task_builder
CAT="development/frontend"
OUT="/tmp/skillgym-output/$CAT"

for skill in ../skill_library/$CAT/skills/*; do
  [ -f "$skill/SKILL.md" ] || continue
  npm run generate-family -- \
    --template-root ../task_templates \
    --template "$CAT/seed_task" \
    --skill-dir "$skill" \
    --skill-mode per-skill \
    --task-count 1 \
    --output-root "$OUT" \
    --concurrency 1 \
    --task-attempt-timeout-hours 9 \
    --max-task-restarts 0 \
    --max-pre-runtime-repair-rounds 100 \
    --max-runtime-repair-rounds 100 \
    --max-skill-effect-repair-rounds 100
done
```

## Output Layout

The existing output format is unchanged:

```text
raw/             # Workspaces, drafts, and repair artifacts
final/           # Published task variants
trace_archive/   # Archived with_skill/no_skill traces
manifest.jsonl   # Task-builder event log
```

## Published Outcomes

- `pf_success`: the task satisfied the primary publication criteria.
- `oracle_fallback_success`: the task was published through fallback when a valid pair existed but the primary skill-effect split was not accepted.

Published variants keep the existing internal naming:

```text
final/pf_success/<template>/<skill>/task1__with_skill
final/pf_success/<template>/<skill>/task1__no_skill
final/oracle_fallback_success/<template>/<skill>/task1__with_skill
final/oracle_fallback_success/<template>/<skill>/task1__no_skill
```

Do not infer every sampled trajectory's outcome from a construction-time task label. This directory refactor does not relabel tasks, rename variant IDs, rewrite prompts or change acceptance conditions.
