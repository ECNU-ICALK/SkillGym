<p align="center">
  <picture>
    <source media="(prefers-color-scheme: dark)" srcset="assets/brand-dark.png">
    <source media="(prefers-color-scheme: light)" srcset="assets/brand-light.png">
    <img src="assets/brand-light.png" alt="SkillGym" width="560">
  </picture>
</p>

<div align="center">

<strong>Internalizing large-scale human-written skills into LLMs for real-world problem solving</strong>

[![Paper](https://img.shields.io/badge/Paper-PDF-B31B1B)](assets/Internalizing_Large_Scale_Human_Written_Skills_into_LLMs_for_Real_World_Problem_Solving.pdf)
[![Dataset](https://img.shields.io/badge/🤗%20Dataset-SkillGym-FFD21E)](https://huggingface.co/datasets/ecnu-icalk/SkillGym)
[![Model](https://img.shields.io/badge/🤗%20Model-SkillGym--Agent-FFD21E)](https://huggingface.co/ecnu-icalk/SkillGym-Agent)
[![License](https://img.shields.io/badge/License-MIT-2EA44F)](LICENSE)

[Paper](assets/Internalizing_Large_Scale_Human_Written_Skills_into_LLMs_for_Real_World_Problem_Solving.pdf) · [Dataset](https://huggingface.co/datasets/ecnu-icalk/SkillGym) · [Agent](https://huggingface.co/ecnu-icalk/SkillGym-Agent) · [Task Builder](task_builder/README.md) · [Quick start](#quick-start)

</div>

<p align="center">
  <a href="assets/SkillGym.pdf"><img src="assets/skillgym_framework.jpg" alt="SkillGym framework" width="100%"></a>
</p>

SkillGym is a benchmark and task-construction framework for studying whether human-written skills can become reusable agent capability. It turns skills and task templates into executable environments, verifies outcomes with code, compares paired runs with and without the target skill, and releases successful long-horizon trajectories for training and analysis.

## The three-part release

| Repository | What it contains | Start here when you want to… |
| --- | --- | --- |
| [GitHub](https://github.com/ECNU-ICALK/SkillGym) | Task Builder, documentation, paper materials, and lightweight figures | understand or extend the pipeline |
| [SkillGym-Agent](https://huggingface.co/ecnu-icalk/SkillGym-Agent) | Qwen3.5-35B-A3B checkpoint fine-tuned on verified trajectories | download or run the released model |
| [SkillGym Dataset](https://huggingface.co/datasets/ecnu-icalk/SkillGym) | Skills, templates, task environments, and trajectory JSONL files | inspect or train on the released data |

The three repositories are versioned separately. The large data snapshot is associated with GitHub commit `6ebabba`; see the dataset card for archive contents and provenance.

## What SkillGym contributes

- **Skill-grounded task construction.** Human-written procedural knowledge is converted into executable tasks with explicit runtime requirements and verifiers.
- **Contrastive skill-dependence evaluation.** A paired `with-skill`/`without-skill` execution (stored as `withskill`/`withoutskill`) measures whether a task depends on its target skill under the reference construction setup.
- **Verified long-horizon experience.** Only executions that pass environment-level checks are released as training trajectories.
- **Open research artifacts.** The task builder, archives, trajectory collections, model checkpoint, and paper materials are available through the linked repositories.

## Framework

<p align="center">
  <a href="assets/SkillGym.pdf"><img src="assets/skillgym_framework.jpg" alt="SkillGym workflow" width="100%"></a>
</p>

1. **Ground:** organize skills and templates into reusable units.
2. **Build:** instantiate executable tasks with inputs, tools, and expected outcomes.
3. **Verify:** run static checks, oracle validation, and reward parsing.
4. **Contrast:** compare paired runs with and without the target skill.
5. **Learn:** archive successful long-horizon trajectories for agent training.

`Skill-Dep.` is a construction-time label: the `with-skill` run succeeds and the paired `without-skill` run produces a valid reward failure (stored as `withskill`/`withoutskill`). `Verifier-Passed` tasks have a valid environment and verifier but do not satisfy that stricter contrastive criterion. Neither label guarantees success for every later model or harness.

## Results at a glance

The release contains **2,756 accepted environments**, **5,512 paired variants**, and **8,364 successful trajectories** across **12 major** and **63 sub-categories**.

| Harness | Model | GDPval-AA v2 (Elo) | Terminal-Bench 2.1 (%) | SkillsBench v1.1 (%) | SkillsBench without skills (%) |
| --- | --- | ---: | ---: | ---: | ---: |
| Codex | Qwen3.5-35B-A3B | 942 | 10.11 | 5.33 | 0.69 |
| Codex | **SkillGym-Agent** | **979** | **46.07** | **33.02** | **21.08** |
| Claude Code | Qwen3.5-35B-A3B | 974 | 39.33 | 23.34 | 12.13 |
| Claude Code | **SkillGym-Agent** | **1173** | **58.43** | **51.47** | **26.81** |

Scores are reported from the current manuscript. GDPval-AA v2 is Elo; the other metrics are task success rates. SkillGym-Agent improves every reported metric under both harnesses, and its skill-free score exceeds the base model with skills in both comparisons. Performance remains higher when external skills are available, so internalized capability and explicit skills are complementary. Under Claude Code, the base and trained models use the same standard system prompt. Under Codex, SkillGym-Agent uses the `no-applypatch` prompt while the base model uses the standard prompt, so the Codex difference is not a fine-tuning-only comparison. Public benchmark scores can also depend on harness, runtime, prompt, and inference budget.

For the full ablation tables and evaluation configuration, see the [paper](assets/Internalizing_Large_Scale_Human_Written_Skills_into_LLMs_for_Real_World_Problem_Solving.pdf) and the [dataset card](https://huggingface.co/datasets/ecnu-icalk/SkillGym).

## Quick start

Choose the path that matches your goal. Downloading trajectories and building a task family are independent workflows.

### Use the released trajectories

```bash
python -m pip install -U huggingface_hub datasets

hf download ecnu-icalk/SkillGym \
  --include "Trajectories/*.jsonl" \
  --repo-type dataset \
  --local-dir .hf/skillgym
```

Stream one trajectory collection without materializing the full corpus:

```python
from datasets import load_dataset

records = load_dataset(
    "json",
    data_files={
        "train": "hf://datasets/ecnu-icalk/SkillGym/Trajectories/skill_dependent_claude_code_deepseek_v4_pro.jsonl",
    },
    split="train",
    streaming=True,
)

print(next(iter(records))["session_id"])
```

See the [dataset README](https://huggingface.co/datasets/ecnu-icalk/SkillGym) for the directory layout, schema differences between trajectory files, and task semantics.

### Build a task family

```bash
git clone https://github.com/ECNU-ICALK/SkillGym.git
cd SkillGym

npm --prefix task_builder ci
npm --prefix task_builder run check

python -m pip install -U huggingface_hub
hf download ecnu-icalk/SkillGym \
  skill_library.tar.zst task_templates.tar.zst \
  --repo-type dataset \
  --local-dir .hf/skillgym

tar --zstd -xf .hf/skillgym/skill_library.tar.zst
tar --zstd -xf .hf/skillgym/task_templates.tar.zst
```

Generate one small family from the repository root:

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

The example checks the local pipeline; a full generation run additionally requires Harbor, a configured runtime such as E2B, Daytona, or Docker, and model/runtime credentials. It can take hours and may incur service charges. See the [Task Builder guide](task_builder/README.md) before scaling up.

### Download the model

```bash
hf download ecnu-icalk/SkillGym-Agent --local-dir .hf/skillgym-agent
```

The [SkillGym-Agent model card](https://huggingface.co/ecnu-icalk/SkillGym-Agent) contains the Transformers smoke test and explains why loading the checkpoint alone does not reproduce the reported agent-harness scores.

## Documentation and resources

- [Task Builder guide](task_builder/README.md) — install, configure, generate, validate, and test task families.
- [Task-generation pipeline](task_builder/docs/task-generation-pipeline.md) — stages, repair semantics, acceptance gates, and outputs.
- [Migration notes](docs/migration.md) — archive layout and path behavior.
- [Dataset card](https://huggingface.co/datasets/ecnu-icalk/SkillGym) — task structure, trajectory schema, statistics, and licensing.
- [Model card](https://huggingface.co/ecnu-icalk/SkillGym-Agent) — checkpoint usage, evaluation scope, and limitations.
- [Paper](assets/Internalizing_Large_Scale_Human_Written_Skills_into_LLMs_for_Real_World_Problem_Solving.pdf) — full method and experiments.

## Reproducibility notes

The repository currently releases the task builder, data, trajectories, and checkpoint. It does not include standalone training code or a complete script for reproducing every external benchmark. The paper reports long-context full-parameter SFT with ms-swift/Megatron on 16 NVIDIA H200 GPUs. Use the linked model and dataset cards for the exact release metadata and loading instructions.

## Citation

The accompanying paper is under double-blind review. Until final publication metadata is available, use:

```bibtex
@misc{skillgym,
  title = {SkillGym: Internalizing Human Skills into LLMs for Real-World Problem Solving},
  year  = {2026},
  note  = {Under review at ICLR 2027},
  url   = {https://github.com/ECNU-ICALK/SkillGym}
}
```

## License

Repository-level code and materials are released under the [MIT License](LICENSE). Skills, fixtures, and supporting assets may retain upstream notices or additional licensing terms; preserve those notices when redistributing the corresponding files.
