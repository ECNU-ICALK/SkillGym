# Task Generation Pipeline

SkillGym generates tasks by combining one reusable task template with one or more skills.

## Inputs

- `TaskTemplates/<major>/<minor>/seed_task`
- `SkillLibrary/<major>/<minor>/skills/<skill>/`

Each `seed_task` directory contains the base task files, environment, solution, and tests. Each skill directory must contain `SKILL.md` and may include supporting files such as `references/`, `scripts/`, or `assets/`.

## Flow

1. Load a generation unit from `--template-root`, `--template`, and one or more `--skill-dir` arguments.
2. Ask Codex to plan a derived task for the selected template and skill.
3. Materialize a task draft and run validation checks.
4. Repair the draft before runtime if validation reports issues.
5. Run runtime checks and repair failures up to the configured limits.
6. Run skill-effect evaluation with `with_skill` and `no_skill` variants.
7. Publish accepted variants into `final/`.
8. Archive traces and write `manifest.jsonl` event records.

## Key Options

- `--task-count`: number of derived tasks to attempt per generation unit.
- `--concurrency`: number of generation units to run in parallel.
- `--task-attempt-timeout-hours`: wall-clock budget for a single task attempt.
- `--max-task-restarts`: number of full task attempt restarts.
- `--max-pre-runtime-repair-rounds`: repair rounds before runtime checks.
- `--max-runtime-repair-rounds`: repair rounds after runtime failures.
- `--max-skill-effect-repair-rounds`: repair rounds after skill-effect failures.

## Published Outcomes

- `pf_success`: the task satisfied the primary publication criteria.
- `oracle_fallback_success`: the task was published through fallback when a valid pair existed but the primary skill-effect split was not accepted.
