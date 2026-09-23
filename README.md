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

[Task Builder](task_builder/README.md) · [Documentation](task_builder/docs/task-generation-pipeline.md) · [Quick Start](#quick-start)

</div>

**SkillGym** is a framework for converting human-written skills into executable, verifier-backed training environments and verified long-horizon agent trajectories. It studies whether procedural knowledge supplied as external skills can be transformed into reusable capability inside an LLM agent.

> **Core question:** Can verified experience generated from human-written skills become reusable procedural competence inside the model?

## Release Map

The SkillGym release is split across three repositories with distinct roles:

| Resource | Primary contents | Start here when you want to… |
| --- | --- | --- |
| [**Code · GitHub**](https://github.com/ECNU-ICALK/SkillGym) | Task Builder, construction pipeline, documentation, figures, and paper materials | understand, reproduce, or extend the task-construction workflow |
| [**Data · Hugging Face**](https://huggingface.co/datasets/ecnu-icalk/SkillGym) | Skill library, task templates, executable task environments, and trajectory collections | inspect the released data or train on SkillGym trajectories |
| [**Model · Hugging Face**](https://huggingface.co/ecnu-icalk/SkillGym-Agent) | **SkillGym-Agent**, a Qwen3.5-35B-A3B checkpoint trained on verified SkillGym trajectories | download, load, or evaluate the released agent checkpoint |

The repositories are versioned independently. The large-artifact dataset snapshot is associated with GitHub commit `6ebabba`. Dataset-specific provenance, archive layout, schemas, and licensing live in the **Dataset Card**; checkpoint-specific loading, evaluation, and limitations live in the **Model Card**.

## What SkillGym Contributes

- **Skill-to-task construction.** Human-written procedural knowledge is converted into executable tasks with explicit runtime requirements, assets, and task-specific outcome verifiers.
- **Verifier-backed acceptance.** Candidate environments must pass feasibility and outcome-verification checks before release.
- **Contrastive skill-dependency assessment.** Paired runs with and without the target skill identify tasks whose success depends on the provided procedural knowledge under the reference construction setup.
- **Verified long-horizon experience.** Successful executions are retained as trajectories for supervised fine-tuning and analysis; the environments and verifiers can also support outcome-based learning.
- **A released trained agent.** SkillGym-Agent enables evaluation of how verified workflow experience transfers into the model and how that capability interacts with explicit skills at inference time.

## At a Glance

<table>
  <tr>
    <td align="center" width="25%">
      <sub><strong>ACCEPTED ENVIRONMENTS</strong></sub><br>
      <strong>2,756</strong><br>
      <sub>executable and verifier-passed</sub>
    </td>
    <td align="center" width="25%">
      <sub><strong>SKILL-DEPENDENT</strong></sub><br>
      <strong>1,081</strong><br>
      <sub>39.2% of accepted environments</sub>
    </td>
    <td align="center" width="25%">
      <sub><strong>SUCCESSFUL TRAJECTORIES</strong></sub><br>
      <strong>8,364</strong><br>
      <sub>verified long-horizon executions</sub>
    </td>
    <td align="center" width="25%">
      <sub><strong>TAXONOMY</strong></sub><br>
      <strong>12 / 63</strong><br>
      <sub>major / sub-categories</sub>
    </td>
  </tr>
</table>

## How SkillGym Works

<p align="center">
  <a href="assets/SkillGym.pdf">
    <img src="assets/skillgym_framework.jpg" alt="SkillGym framework" width="100%">
  </a>
</p>

1. **Ground** human-written skills and reusable task templates.
2. **Construct** executable tasks with inputs, tools, runtime requirements, and verifiers.
3. **Validate** task feasibility and verifier correctness.
4. **Contrast** paired execution with and without the target skill to assess skill dependence.
5. **Sample** multi-harness agent trajectories and retain verified outcomes.
6. **Train** SkillGym-Agent on successful trajectories and evaluate transfer on external agent benchmarks.

In the released data, **Skill-Dep.** denotes environments satisfying the stricter contrastive criterion under the reference construction setup; **Verifier-Passed** denotes environments that pass execution and verification checks without satisfying that additional criterion. These are task-construction labels, not guarantees about every later model or harness.

## Main Results

<p align="center">
  <a href="assets/skillgym_baseline.pdf">
    <img
      src="assets/skillgym_baseline.png"
      alt="SkillGym-Agent performance across general-agent benchmarks"
      width="95%"
    >
  </a>
</p>

Higher is better for every metric. **GDPval-AA v2** is reported as Elo; the remaining metrics are task success rates (%).

| Harness | Model | GDPval-AA v2<br>(Elo) ↑ | Terminal-Bench 2.1<br>(%) ↑ | SkillsBench v1.1<br>w/ Skills (%) ↑ | SkillsBench v1.1<br>w/o Skills (%) ↑ |
| --- | --- | ---: | ---: | ---: | ---: |
| Codex | Qwen3.5-35B-A3B | 942 | 10.11 | 5.33 | 0.69 |
| Codex | **SkillGym-Agent** | **979** | **46.07** | **33.02** | **21.08** |
| Claude Code | Qwen3.5-35B-A3B | 974 | 39.33 | 23.34 | 12.13 |
| Claude Code | **SkillGym-Agent** | **1173** | **58.43** | **51.47** | **26.81** |

The released **SkillGym-Agent** checkpoint corresponds to the paper's **All Teachers** setting and is trained on the full set of **8,364 successful trajectories** from the released teacher–harness configurations.

A central observation is **skill-free transfer**: after training on verified SkillGym trajectories, the released agent retains substantial performance even when the external skill is removed at inference time. Performance remains strongest when external skills are available, **suggesting that internalized capability and explicit skills are complementary**.

> [!NOTE]
> Under Claude Code, the base and trained models use the same standard system prompt. Under Codex, the base uses the standard prompt while SkillGym-Agent uses the `no-applypatch` prompt, so the Codex difference is not a pure fine-tuning-only comparison. See the paper for the complete evaluation configuration, teacher/harness ablations, and public-reference results.

<a id="quick-start"></a>

## Quick Start

Choose the path that matches your goal.

### Use the Released Data

```bash
python -m pip install -U huggingface_hub

hf download ecnu-icalk/SkillGym \
  --include "Trajectories/*.jsonl" \
  --repo-type dataset \
  --local-dir .hf/skillgym
```

For archive contents, trajectory schemas, task labels, terminology, and loading examples, see the [**SkillGym Dataset Card**](https://huggingface.co/datasets/ecnu-icalk/SkillGym).

### Download SkillGym-Agent

```bash
hf download ecnu-icalk/SkillGym-Agent \
  --local-dir .hf/skillgym-agent
```

For Transformers loading, checkpoint metadata, intended use, and evaluation caveats, see the [**SkillGym-Agent Model Card**](https://huggingface.co/ecnu-icalk/SkillGym-Agent).

### Build New Skill-Grounded Environments

```bash
git clone https://github.com/ECNU-ICALK/SkillGym.git
cd SkillGym

npm --prefix task_builder ci
npm --prefix task_builder run check
```

Download the released skill library and task templates:

```bash
hf download ecnu-icalk/SkillGym \
  skill_library.tar.zst task_templates.tar.zst \
  --repo-type dataset \
  --local-dir .hf/skillgym

tar --zstd -xf .hf/skillgym/skill_library.tar.zst
tar --zstd -xf .hf/skillgym/task_templates.tar.zst
```

Then follow the [Task Builder guide](task_builder/README.md) for generation, validation, skill-effect testing, repair, and publishing. A full generation run additionally requires Harbor, a configured runtime such as E2B, Daytona, or Docker, and the relevant model/runtime credentials.

## Repository Structure

```text
SkillGym/
├── task_builder/   # Task construction, validation, repair, and publishing
├── assets/         # Paper, figures, and project branding
├── README.md       # Project overview
└── LICENSE
```

Large artifacts such as the skill library, task templates, executable tasks, and trajectories are hosted in the [SkillGym Dataset](https://huggingface.co/datasets/ecnu-icalk/SkillGym).

## Documentation

| Resource | Scope |
| --- | --- |
| [Task Builder guide](task_builder/README.md) | Installation, configuration, generation, validation, and output layout |
| [Task-generation pipeline](task_builder/docs/task-generation-pipeline.md) | Construction stages, repair semantics, acceptance gates, and outputs |
| [Dataset Card](https://huggingface.co/datasets/ecnu-icalk/SkillGym) | Released artifacts, schemas, labels, terminology, provenance, and data licensing |
| [Model Card](https://huggingface.co/ecnu-icalk/SkillGym-Agent) | Checkpoint loading, training summary, evaluation, intended use, and limitations |
| [Paper](assets/Internalizing_Large_Scale_Human_Written_Skills_into_LLMs_for_Real_World_Problem_Solving.pdf) | Full method, dataset analysis, experiments, ablations, and appendices |

## Reproducibility

This repository releases the **Task Builder**, documentation, and project materials. The companion Hugging Face repositories release the **data/trajectories** and **SkillGym-Agent checkpoint**. The current release does not include a standalone end-to-end training script or a single script that reproduces every external benchmark result.

The paper reports long-context full-parameter supervised fine-tuning with **ms-swift / Megatron** on **16 × NVIDIA H200 GPUs**. Use the linked Dataset Card and Model Card for artifact-specific metadata and usage details.

## Questions & Contributions

Questions, bug reports, and feature requests are welcome through [GitHub Issues](https://github.com/ECNU-ICALK/SkillGym/issues). Contributions to the Task Builder and documentation are welcome via pull requests.

For dataset- or checkpoint-specific questions, please include the relevant Hugging Face repository and revision when reporting an issue.

## Citation

The accompanying paper is currently under double-blind review. Until final publication metadata is available, please use:

```bibtex
@misc{skillgym2026,
  title = {Internalizing Large-Scale Human-Written Skills into LLMs for Real-World Problem Solving},
  year  = {2026},
  url   = {https://github.com/ECNU-ICALK/SkillGym}
}
```

## License

Repository-level code and materials are released under the [MIT License](LICENSE).

Dataset source skills, fixtures, and supporting assets may retain upstream notices or additional licensing terms. Preserve those notices when redistributing the corresponding materials; see the Dataset Card for artifact-specific details.
