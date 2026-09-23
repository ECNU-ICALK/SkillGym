# SkillGym Task Builder

**Developer guide for turning reusable skills and task templates into executable Harbor environments.**

<p align="center">
  <a href="../README.md">Project overview</a>
  &nbsp;·&nbsp;
  <a href="docs/task-generation-pipeline.md">Full pipeline</a>
  &nbsp;·&nbsp;
  <a href="https://huggingface.co/datasets/ecnu-icalk/SkillGym">Dataset</a>
  &nbsp;·&nbsp;
  <a href="../docs/migration.md">Data layout</a>
</p>

> The builder uses Codex for planning, task authoring, review, and repair, then validates each candidate with Harbor and a with-skill / no-skill comparison.

## What this component does

| Stage | Responsibility | Main entry point |
| --- | --- | --- |
| Discover | Find templates and skills in the selected scope | `inventory` |
| Author | Produce a structured plan and Harbor task draft | `generate-family` |
| Validate | Run static checks, preflight, oracle, and reward parsing | `src/validate.ts` |
| Measure skill effect | Compare the same task with and without the target skill | `src/skill_effect.ts` |
| Publish | Copy accepted variants and archive evidence | `src/materialize.ts`, `src/trace_archive.ts` |

The builder is a task-construction pipeline, not a benchmark runner or a complete SFT reproduction script.

## Before you run it

A local checkout should contain:

```text
SkillGym/
├── skill_library/<major>/<minor>/skills/<skill>/
├── task_templates/<major>/<minor>/seed_task/
└── task_builder/
```

Download the skill and template archives from the [SkillGym Hugging Face dataset](https://huggingface.co/datasets/ecnu-icalk/SkillGym), then extract them at the repository root:

```bash
hf download ecnu-icalk/SkillGym \
  skill_library.tar.zst task_templates.tar.zst \
  --repo-type dataset --local-dir .hf/skillgym

tar --zstd -xf .hf/skillgym/skill_library.tar.zst
tar --zstd -xf .hf/skillgym/task_templates.tar.zst
```

Install the locked JavaScript dependencies:

```bash
npm --prefix task_builder ci
```

A full generation run also needs the Harbor CLI, a configured runtime such as e2b, Daytona, or Docker, and the credentials listed in [`.env.example`](../.env.example). Model and sandbox services may incur charges.

## Quick start

### Inspect available units

```bash
npm --prefix task_builder run inventory
```

### Generate one task family

Run from the repository root:

```bash
npm --prefix task_builder run generate-family -- \
  --template-root task_templates \
  --template development/frontend/seed_task \
  --skill-dir skill_library/development/frontend/skills/tailwind-design-system \
  --skill-mode per-skill \
  --task-count 1 \
  --output-root /tmp/skillgym-output \
  --concurrency 1
```

The command above is intentionally small. For long-running production jobs, tune the repair and timeout budgets explicitly:

| Option | Meaning |
| --- | --- |
| `--skill-mode all|per-skill` | Use all skills together or create one unit per skill |
| `--task-count` | Number of tasks to request per unit |
| `--concurrency` | Number of active units |
| `--limit` | Cap the number of discovered units |
| `--scope-slug` | Restrict output to a named scope |
| `--task-attempt-timeout-hours` | Maximum time for one task attempt |
| `--max-task-restarts` | Number of task-level restarts |
| `--max-pre-runtime-repair-rounds` | Repairs before runtime execution |
| `--max-runtime-repair-rounds` | Repairs after runtime failures |
| `--max-skill-effect-repair-rounds` | Repairs after the skill-effect comparison |

A run can take hours. Start with one unit and concurrency `1`, inspect the output, then scale up.

## Pipeline and acceptance gates

Each candidate moves through the following stages:

1. **Discovery** loads a template and one or more skills.
2. **Planning** asks Codex for a structured task plan.
3. **Authoring** writes the draft Harbor task, environment, solution, and tests.
4. **Static review** checks schemas, paths, task structure, and required files.
5. **Oracle validation** runs the task and checks the expected outcome.
6. **Skill-effect validation** compares `with_skill` and `no_skill` runs.
7. **Repair or publish** either spends the configured repair budget or writes an accepted variant and its evidence.

The strict skill-effect gate accepts a candidate when the with-skill run passes and the no-skill run produces a valid reward failure. If the oracle passes but the contrastive evidence is unavailable after the repair budget, the candidate may be written to `oracle_fallback_success/`. This distinction is preserved in the final output directories.

## Output layout

```text
outputs/
├── raw/                         # Workspaces, drafts, repairs, and runtime logs
├── final/
│   ├── pf_success/              # Strict with-skill / no-skill acceptance
│   └── oracle_fallback_success/ # Oracle passed; contrastive evidence incomplete
├── trace_archive/               # Paired runtime evidence and trajectories
└── manifest.jsonl               # Append-only event log and run summaries
```

Published variants contain the task plan, user instruction, metadata, environment, solution, and tests. The materializer copies only approved entries into `final/`; raw workspaces remain useful for debugging and repair analysis.

## Source map

| File | Responsibility |
| --- | --- |
| [`src/cli.ts`](src/cli.ts) | CLI parsing, unit loading, orchestration, budgets, and publishing |
| [`src/discovery.ts`](src/discovery.ts) | Template and skill discovery; all/per-skill modes |
| [`src/codex.ts`](src/codex.ts) | Codex SDK threads, structured outputs, retries, and repair turns |
| [`src/prompts.ts`](src/prompts.ts) | Planner, writer, reviewer, and repair instructions |
| [`src/schema.ts`](src/schema.ts) | Zod schemas and structured-output schemas |
| [`src/validate.ts`](src/validate.ts) | Static checks, Harbor preflight, runtime validation, reward parsing |
| [`src/skill_effect.ts`](src/skill_effect.ts) | With-skill / no-skill construction and evaluation |
| [`src/materialize.ts`](src/materialize.ts) | Sanitized copying of accepted task files |
| [`src/published.ts`](src/published.ts) | Resume support and published-ordinal detection |
| [`src/workspace.ts`](src/workspace.ts) | Family and task-attempt workspace creation |
| [`src/trace_archive.ts`](src/trace_archive.ts) | Paired runtime evidence and trajectory archiving |
| [`src/manifest.ts`](src/manifest.ts) | Append-only manifest and run summaries |

## Configuration

Copy the example only when a local `.env` does not already exist:

```bash
[ -f .env ] || cp .env.example .env
```

Then fill in the provider credentials and runtime settings required by your environment. The example file documents the supported variables, including:

- `OPENAI_API_KEY`
- `OPENAI_BASE_URL`
- `E2B_API_KEY`
- ``X_TASK_BUILDER_RUNTIME_ENV`

The builder does not provision model access or a sandbox automatically. Verify those services before starting a long run.

## Checks and tests

Run the type check and focused tests from the repository root:

```bash
npm --prefix task_builder run check
npm --prefix task_builder run test:codex
npm --prefix task_builder run test:prompts
npm --prefix task_builder run test:validate
npm --prefix task_builder run test:skill-effect
node --import tsx task_builder/tests/harbor_metrics.test.ts
node --import tsx task_builder/tests/repo_paths.test.ts
```

The CI workflow runs the type check and the `tests/*.test.ts` files. It does not start a paid end-to-end generation job.

## Further reading

- [Task-generation pipeline](docs/task-generation-pipeline.md) — detailed stages, artifacts, and repair semantics.
- [Repository overview](../README.md) — release contents, HF downloads, and paper context.
- [Data migration notes](../docs/migration.md) — archive layout and path behavior.
- [Task Builder source](src/) and [tests](tests/) — implementation and regression coverage.
