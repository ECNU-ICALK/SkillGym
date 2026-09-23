# SkillGym Task Builder

The Task Builder turns a reusable task template and one or more human-written skills into executable Harbor tasks. It uses Codex for planning, task authoring, review, and repair, then validates the task with an oracle run and a with_skill / no_skill comparison.

For the repository overview, see the [root README](../README.md). For the data release layout, see [Data Release Migration](../docs/migration.md). The full construction flow is documented in [Task Generation Pipeline](docs/task-generation-pipeline.md).

## Prerequisites

The builder expects these directories at the repository root:

```text
skill_library/<major>/<minor>/skills/<skill>/
task_templates/<major>/<minor>/seed_task/
```

Download the archives from the [SkillGym Hugging Face dataset](https://huggingface.co/datasets/ecnu-icalk/SkillGym) and extract them before running the builder:

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

A full generation run also requires the Harbor CLI, a configured runtime (e2b, daytona, or docker), and the credentials described in [.env.example](../.env.example). Model and sandbox services may incur charges.

## End-to-end flow

1. Discover a template and input skills.
2. Ask Codex to produce a structured task plan.
3. Write a draft Harbor task.
4. Run a blocking review and static validation.
5. Run the oracle task through Harbor.
6. Run the same task with and without the target skill.
7. Repair failures within the configured budgets.
8. Publish accepted variants and archive logs, rewards, and trajectories.

The strict skill-effect gate accepts a task when with_skill passes and no_skill produces a valid reward failure. Other outcomes are retained as repair evidence or may be published as oracle_fallback_success after repair budgets are exhausted.

## CLI

Inspect the available templates and their metadata:

```bash
npm --prefix task_builder run inventory
```

Generate one family of tasks:

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

Important options include:

- --skill-mode all|per-skill
- --task-count
- --concurrency
- --limit
- --scope-slug
- --task-attempt-timeout-hours
- --max-task-restarts
- --max-pre-runtime-repair-rounds
- --max-runtime-repair-rounds
- --max-skill-effect-repair-rounds

## Source modules

| Module | Responsibility |
| --- | --- |
| [cli.ts](src/cli.ts) | CLI parsing, unit loading, orchestration, repair budgets, and publishing |
| [discovery.ts](src/discovery.ts) | Template and skill discovery; all and per-skill modes |
| [codex.ts](src/codex.ts) | Codex SDK threads, structured outputs, retries, and repair turns |
| [prompts.ts](src/prompts.ts) | Planner, writer, reviewer, and repair instructions |
| [schema.ts](src/schema.ts) | Zod schemas and structured-output JSON schemas |
| [validate.ts](src/validate.ts) | Static checks, Harbor preflight, runtime validation, and reward parsing |
| [skill_effect.ts](src/skill_effect.ts) | with_skill / no_skill variant construction and evaluation |
| [materialize.ts](src/materialize.ts) | Sanitized copying of accepted task files into final/ |
| [published.ts](src/published.ts) | Resume support and detection of already-published task ordinals |
| [workspace.ts](src/workspace.ts) | Family and task-attempt workspace creation |
| [trace_archive.ts](src/trace_archive.ts) | Archiving paired runtime evidence and trajectories |
| [manifest.ts](src/manifest.ts) | Append-only manifest.jsonl and run summaries |

## Output layout

```text
outputs/
├── raw/             # Workspaces, drafts, repair artifacts, and runtime logs
├── final/
│   ├── pf_success/
│   └── oracle_fallback_success/
├── trace_archive/   # Paired with_skill/no_skill evidence
└── manifest.jsonl   # Task-builder event log
```

Published task variants contain the task plan, user instruction, task metadata, environment, solution, and tests. The materializer copies only the approved task entries into the final directory.

## Tests

Run the local checks from the repository root:

```bash
npm --prefix task_builder run check
npm --prefix task_builder run test:codex
npm --prefix task_builder run test:prompts
npm --prefix task_builder run test:validate
npm --prefix task_builder run test:skill-effect
node --import tsx task_builder/tests/harbor_metrics.test.ts
node --import tsx task_builder/tests/repo_paths.test.ts
```

The CI workflow runs the type check and all tests/*.test.ts files. It does not run a paid end-to-end generation job.

## Further reading

- [Full task-generation pipeline](docs/task-generation-pipeline.md)
- [Repository data migration](../docs/migration.md)
- [Task Builder source](src/)
- [Task Builder tests](tests/)