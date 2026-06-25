# SkillGym

SkillGym is an open skill library and task-generation framework for AI agents. It contains reusable skills, task templates, and an automated builder that generates benchmark tasks from selected skills.

## Dataset

The released SkillGym task dataset is available on Hugging Face:

[ecnu-icalk/SkillGym](https://huggingface.co/datasets/ecnu-icalk/SkillGym)

## Contents

```text
SkillGym/
  SkillLibrary/      # 2,636 skills across 63 categories
  TaskTemplates/     # 63 reusable seed_task directories
  TaskBuilder/       # TypeScript task-generation pipeline
  docs/              # Pipeline notes
```

## Environment

Copy `.env.example` to `.env` and fill the variables used by your model provider and runtime:

```bash
OPENAI_API_KEY=
OPENAI_BASE_URL=
E2B_API_KEY=
CODEX_TASK_BUILDER_RUNTIME_ENV=e2b
```

Load the variables before running the builder:

```bash
set -a
source .env
set +a
```

## Install

```bash
cd TaskBuilder
npm install
npm run check
```

## Generate One Task

This example generates one task from the `development/frontend` template and the `tailwind-design-system` skill.

```bash
cd /path/to/SkillGym/TaskBuilder

npm run generate-family -- \
  --template-root ../TaskTemplates \
  --template development/frontend/seed_task \
  --skill-dir ../SkillLibrary/development/frontend/skills/tailwind-design-system \
  --skill-mode per-skill \
  --task-count 1 \
  --output-root /tmp/skillgym-output/development/frontend \
  --concurrency 1 \
  --codex-run-retries 3 \
  --task-attempt-timeout-hours 9 \
  --max-task-restarts 0 \
  --max-pre-runtime-repair-rounds 100 \
  --max-runtime-repair-rounds 100 \
  --max-skill-effect-repair-rounds 100
```

## Batch Example

Run one category by looping over all skills in that category:

```bash
cd /path/to/SkillGym/TaskBuilder

CAT="development/frontend"
OUT="/tmp/skillgym-output/$CAT"

for skill in ../SkillLibrary/$CAT/skills/*; do
  [ -f "$skill/SKILL.md" ] || continue
  npm run generate-family -- \
    --template-root ../TaskTemplates \
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

The builder writes task-generation state under the selected output root:

```text
raw/             # workspaces, drafts, repair artifacts
final/           # published task variants
trace_archive/   # archived with_skill/no_skill traces
manifest.jsonl   # task-builder event log
```

Published tasks are grouped by outcome. The directory names are internal status names:

```text
final/pf_success/<template>/<skill>/task1__with_skill
final/pf_success/<template>/<skill>/task1__no_skill
final/oracle_fallback_success/<template>/<skill>/task1__with_skill
final/oracle_fallback_success/<template>/<skill>/task1__no_skill
```

`pf_success` means the task passed skill-effect validation, with `with_skill` passing and `no_skill` failing. `oracle_fallback_success` means the task did not pass the default skill-effect validation, but a valid `with_skill` / `no_skill` pair was still available, so it was published through the fallback path.

## Development Checks

```bash
cd TaskBuilder
npm run check
npm run test:prompts
npm run test:validate
npm run test:skill-effect
```
