<p align="center">
  <picture>
    <source
      media="(prefers-color-scheme: dark)"
      srcset="assets/brand-dark.png"
    >
    <source
      media="(prefers-color-scheme: light)"
      srcset="assets/brand-light.png"
    >
    <img
      src="assets/brand-light.png"
      alt="SkillGym"
      width="600"
    >
  </picture>
</p>

<div align="center">

<p>
  <strong>
    Internalizing Large-Scale Human-Written Skills into LLMs for Real-World Problem Solving
  </strong>
</p>

<p>
  <a href="assets/Internalizing_Large_Scale_Human_Written_Skills_into_LLMs_for_Real_World_Problem_Solving.pdf">
    <img src="https://img.shields.io/badge/Paper-PDF-B31B1B" alt="Paper">
  </a>
  <a href="https://huggingface.co/datasets/ecnu-icalk/SkillGym">
    <img src="https://img.shields.io/badge/🤗%20Dataset-SkillGym-FFD21E" alt="Dataset">
  </a>
  <a href="https://huggingface.co/ecnu-icalk/SkillGym-Agent">
    <img src="https://img.shields.io/badge/🤗%20Model-SkillGym--Agent-FFD21E" alt="Model">
  </a>
  <a href="task_builder/README.md">
    <img src="https://img.shields.io/badge/Code-Task%20Builder-4C78A8" alt="Task Builder">
  </a>
  <a href="LICENSE">
    <img src="https://img.shields.io/badge/License-MIT-2EA44F" alt="MIT License">
  </a>
</p>

<p>
  <a href="assets/Internalizing_Large_Scale_Human_Written_Skills_into_LLMs_for_Real_World_Problem_Solving.pdf">Paper</a>
  &nbsp;&nbsp;•&nbsp;&nbsp;
  <a href="https://huggingface.co/datasets/ecnu-icalk/SkillGym">Dataset</a>
  &nbsp;&nbsp;•&nbsp;&nbsp;
  <a href="https://huggingface.co/ecnu-icalk/SkillGym-Agent">Model</a>
  &nbsp;&nbsp;•&nbsp;&nbsp;
  <a href="task_builder/README.md">Task Builder</a>
  &nbsp;&nbsp;•&nbsp;&nbsp;
  <a href="#main-results">Results</a>
  &nbsp;&nbsp;•&nbsp;&nbsp;
  <a href="#quick-start">Quick Start</a>
</p>

<p>
  <em>
    From human-written skills to verified agent experience,
    and from verified experience to reusable model capability.
  </em>
</p>

</div>

<p align="center">
  <a href="assets/SkillGym.pdf">
    <img
      src="assets/skillgym_framework.jpg"
      alt="SkillGym framework"
      width="100%"
    >
  </a>
</p>

<p align="center">
  <sub>
    <em>
      SkillGym transforms human-written skills into executable and verifiable
      task environments, measures skill dependence through paired execution,
      and converts successful long-horizon trajectories into training experience.
    </em>
  </sub>
</p>


## Highlights

**SkillGym** is an end-to-end framework for studying whether knowledge initially
provided as external human-written skills can become reusable capability inside
a language-model agent.

It constructs executable environments from skills, validates task outcomes with
code-based verifiers, contrasts agent behavior **with and without the target skill**,
and collects successful long-horizon interactions for training.

<table>
  <tr>
    <td align="center" width="25%">
      <strong>◈ 2,756</strong><br>
      <sub>accepted environments</sub>
    </td>
    <td align="center" width="25%">
      <strong>⇄ 5,512</strong><br>
      <sub>paired task variants</sub>
    </td>
    <td align="center" width="25%">
      <strong>✓ 8,364</strong><br>
      <sub>successful trajectories</sub>
    </td>
    <td align="center" width="25%">
      <strong>▦ 12 / 63</strong><br>
      <sub>major / sub-categories</sub>
    </td>
  </tr>
</table>

<p align="center">
  <sub>
    Counts correspond to the current manuscript snapshot.
    Environments, paired variants, sampled trials, and successful trajectories
    are different units.
  </sub>
</p>

### Core contributions

- **Skill-grounded environment construction.** Human-written procedural knowledge
  is transformed into executable tasks with explicit runtime and verification
  specifications.
- **Paired skill-dependence evaluation.** Eligible tasks are executed both with
  and without the target skill, separating direct skill use from capability that
  persists after skill removal.
- **Verified long-horizon training experience.** Successful interactions are
  retained only after environment-level verification and used to train
  **SkillGym-Agent**.
- **Open resources.** We release the task-construction pipeline, dataset,
  trajectories, and trained checkpoint.

> [!NOTE]
> **Research question:** Can verified experience generated from human-written
> skills be internalized as transferable agent capability?


<a id="main-results"></a>

## Main Results

<p align="center">
  <a href="assets/skillgym_baseline.pdf">
    <img
      src="assets/skillgym_baseline.png"
      alt="SkillGym-Agent benchmark results"
      width="100%"
    >
  </a>
</p>

<p align="center">
  <sub>
    <em>
      General-agent benchmark results from the current manuscript.
      Click the figure to open the vector PDF.
    </em>
  </sub>
</p>

**SkillGym-Agent** is a full-parameter supervised fine-tuned
**Qwen3.5-35B-A3B** model trained on successful SkillGym trajectories.

Across both evaluated agent harnesses, SkillGym-Agent improves over the
corresponding base model on GDPval-AA v2, Terminal-Bench 2.1, and
SkillsBench v1.1.

<table>
  <tr>
    <td width="33%" valign="top">
      <strong>↗ General gains</strong><br><br>
      <sub>
        SkillGym-Agent improves across all reported benchmarks under both
        Codex and Claude Code.
      </sub>
    </td>
    <td width="33%" valign="top">
      <strong>◎ Skill-free transfer</strong><br><br>
      <sub>
        Without-skills performance rises from
        <strong>0.69 → 21.08</strong> under Codex and
        <strong>12.13 → 26.81</strong> under Claude Code.
      </sub>
    </td>
    <td width="34%" valign="top">
      <strong>＋ Complementarity</strong><br><br>
      <sub>
        Performance remains strongest when explicit skills are available,
        suggesting that internalized capability and external skill access
        are complementary.
      </sub>
    </td>
  </tr>
</table>

### Skill-free transfer

A central observation is that part of the performance improvement remains after
the inference-time skill is removed:

- Under **Claude Code**, SkillGym-Agent reaches **26.81% without skills**,
  compared with **23.34%** for the base model with skills.
- Under **Codex**, SkillGym-Agent reaches **21.08% without skills**,
  compared with **5.33%** for the base model with skills.

This pattern is consistent with part of the verified workflow experience
transferring beyond direct prompt following.

> [!IMPORTANT]
> The Codex base-model and SkillGym-Agent comparison uses different system-prompt
> settings, as documented in the evaluation notes below. The Codex difference
> therefore should not be attributed to fine-tuning alone.

<details>
<summary><strong>Detailed benchmark results</strong></summary>

<br>

#### Codex

| Model | GDPval-AA v2 ↑ | Terminal-Bench 2.1 ↑ | SkillsBench v1.1 ↑ | w/o Skills ↑ |
| --- | ---: | ---: | ---: | ---: |
| Qwen3.5-35B-A3B | 942 | 10.11 | 5.33 | 0.69 |
| **SkillGym-Agent** | **979** (+37) | **46.07** (+35.96) | **33.02** (+27.69) | **21.08** (+20.39) |

#### Claude Code

| Model | GDPval-AA v2 ↑ | Terminal-Bench 2.1 ↑ | SkillsBench v1.1 ↑ | w/o Skills ↑ |
| --- | ---: | ---: | ---: | ---: |
| Qwen3.5-35B-A3B | 974 | 39.33 | 23.34 | 12.13 |
| **SkillGym-Agent** | **1173** (+199) | **58.43** (+19.10) | **51.47** (+28.13) | **26.81** (+14.68) |

<sub>
Parenthesized values are absolute Elo or percentage-point gains over the
corresponding base model under the same harness.
</sub>

</details>


## How SkillGym Works

SkillGym follows a five-stage pipeline that transforms external procedural
knowledge into verified training experience.

<table>
  <tr>
    <td width="20%" align="center">
      <strong>① Ground</strong><br>
      <sub>Skills & templates</sub>
    </td>
    <td width="20%" align="center">
      <strong>② Build</strong><br>
      <sub>Executable tasks</sub>
    </td>
    <td width="20%" align="center">
      <strong>③ Verify</strong><br>
      <sub>Code-based checks</sub>
    </td>
    <td width="20%" align="center">
      <strong>④ Contrast</strong><br>
      <sub>With vs. without skill</sub>
    </td>
    <td width="20%" align="center">
      <strong>⑤ Learn</strong><br>
      <sub>Verified trajectories</sub>
    </td>
  </tr>
</table>

1. **Ground.** Human-written skills are paired with reusable task templates to
   define skill-grounded problem families.

2. **Build.** Templates are instantiated into executable environments with
   explicit files, dependencies, runtime requirements, and task specifications.

3. **Verify.** Generated environments and agent outputs are checked through
   code-based verifiers rather than model-based judgment alone.

4. **Contrast.** Each eligible task is executed both **with** and **without**
   its target skill.

5. **Learn.** Successful long-horizon trajectories are retained as verified
   training experience and used to train **SkillGym-Agent**.

> [!TIP]
> A task enters the strict **Skill-Dep** group when the `with_skill` execution
> succeeds while the paired `no_skill` execution produces a valid reward failure.
> Other verifier-passed environments are released separately as
> **Verifier-Passed** tasks.

For implementation details, repair semantics, validation stages, and output
layout, see the
[task-generation pipeline](task_builder/docs/task-generation-pipeline.md).


## Resources

| Resource | Description | Link |
| --- | --- | --- |
| **🤗 SkillGym Dataset** | Skills, task templates, executable environments, and verified trajectories | [Hugging Face](https://huggingface.co/datasets/ecnu-icalk/SkillGym) |
| **🤗 SkillGym-Agent** | Model trained on successful SkillGym trajectories | [Hugging Face](https://huggingface.co/ecnu-icalk/SkillGym-Agent) |
| **🛠 Task Builder** | Pipeline for constructing new skill-grounded environments | [Developer Guide](task_builder/README.md) |
| **📘 Pipeline Docs** | Full task-generation, repair, and validation workflow | [Documentation](task_builder/docs/task-generation-pipeline.md) |
| **📄 Paper** | Current manuscript and complete evaluation details | [PDF](assets/Internalizing_Large_Scale_Human_Written_Skills_into_LLMs_for_Real_World_Problem_Solving.pdf) |


<a id="quick-start"></a>

## Quick Start

### 1. Get the dataset

Install the Hugging Face CLI and download the released trajectories:

```bash
python -m pip install -U huggingface_hub

hf download ecnu-icalk/SkillGym \
  --include "Trajectories/*.jsonl" \
  --repo-type dataset \
  --local-dir .hf/skillgym
```

<details>
<summary><strong>Stream trajectories with 🤗 Datasets</strong></summary>

<br>

```bash
python -m pip install -U datasets
```

```python
from datasets import load_dataset

trajectories = load_dataset(
    "json",
    data_files={
        "train": (
            "hf://datasets/ecnu-icalk/SkillGym/"
            "Trajectories/"
            "skill_dependent_claude_code_deepseek_v4_pro.jsonl"
        )
    },
    split="train",
    streaming=True,
)

example = next(iter(trajectories))
print(example["session_id"])
```

</details>


### 2. Get SkillGym-Agent

```bash
hf download ecnu-icalk/SkillGym-Agent \
  --local-dir .hf/skillgym-agent
```

See the
[SkillGym-Agent Model Card](https://huggingface.co/ecnu-icalk/SkillGym-Agent)
for checkpoint details and usage information.


### 3. Set up the Task Builder

```bash
git clone https://github.com/ECNU-ICALK/SkillGym.git
cd SkillGym

npm --prefix task_builder ci
npm --prefix task_builder run check
```

<details>
<summary><strong>Run a minimal task-generation example</strong></summary>

<br>

Download the released skill library and task templates:

```bash
hf download ecnu-icalk/SkillGym \
  skill_library.tar.zst \
  task_templates.tar.zst \
  --repo-type dataset \
  --local-dir .hf/skillgym
```

Extract the archives:

```bash
tar --zstd -xf .hf/skillgym/skill_library.tar.zst
tar --zstd -xf .hf/skillgym/task_templates.tar.zst
```

Generate one small task family:

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

</details>

> [!NOTE]
> Full task generation additionally requires Harbor, a configured runtime such
> as **E2B**, **Daytona**, or **Docker**, and the relevant model/runtime
> credentials. Read the [Task Builder guide](task_builder/README.md) before
> scaling up.


## Technical Details

<details>
<summary><strong>Dataset and release details</strong></summary>

<br>

| Release signal | Value |
| --- | --- |
| Accepted environments | **2,756** |
| Skill-Dep / Verifier-Passed | **1,081 / 1,675** |
| Paired task variants | **5,512** |
| Successful trajectories | **8,364** from 48,152 trials |
| Trial-level success rate | **17.4%** |
| Deduplicated coverage | **2,302** unique tasks |
| Average successful trajectory | **49.0** tool calls · **63.4k** logged text tokens · **35.2** interaction steps |
| Longest observed trajectory | **350** tool calls · **342.9k** logged text tokens · **318** interaction steps |

### Released artifacts

| Artifact | Contents |
| --- | --- |
| `Tasks.tar.zst` | Published paired task environments |
| `skill_library.tar.zst` | Human-written skills and supporting assets |
| `task_templates.tar.zst` | Reusable seed-task templates and fixtures |
| `Trajectories/*.jsonl` | Trajectory collections organized by result type, harness, and teacher |
| `SkillGym-Agent` | Released trained checkpoint |

The large-artifact snapshot is associated with GitHub commit `6ebabba`.

For schema details, task layout, licensing notes, and intended use, see the
[Hugging Face Dataset Card](https://huggingface.co/datasets/ecnu-icalk/SkillGym).

</details>


<details>
<summary><strong>Teacher and harness ablation</strong></summary>

<br>

| Harness | Teacher setting | GDPval-AA v2 ↑ | Terminal-Bench 2.1 ↑ | SkillsBench v1.1 ↑ | w/o Skills ↑ |
| --- | --- | ---: | ---: | ---: | ---: |
| Codex | GPT-5.4 | 969 | 24.72 | 14.00 | 6.96 |
| Codex | Nex-N2-Pro | **1074** | 33.71 | 13.59 | 12.61 |
| Codex | GPT+Nex | 976 | 40.45 | 19.91 | 13.59 |
| Codex | All Teachers | 979 | **46.07** | **33.02** | **21.08** |
| Claude Code | DeepSeek V4 Pro | 1106 | 43.82 | 28.81 | 19.02 |
| Claude Code | GLM-5.2 | **1212** | 55.06 | 45.50 | 25.10 |
| Claude Code | DeepSeek+GLM | 1161 | 57.30 | 47.33 | **28.41** |
| Claude Code | All Teachers | 1173 | **58.43** | **51.47** | 26.81 |

<sub>
Best result within each harness and metric is bolded.
GDPval-AA v2 is reported as Elo; all other values are percentages.
</sub>

</details>


<details>
<summary><strong>Evaluation and reproducibility notes</strong></summary>

<br>

- **GDPval-AA v2** is reported as Elo.
- **Terminal-Bench 2.1** and **SkillsBench v1.1** are reported as task
  success rates (%).
- The manuscript reports long-context full-parameter SFT with
  ms-swift/Megatron on **16 NVIDIA H200 GPUs**.
- The repository releases the Task Builder, data, trajectories, and checkpoint,
  but does not currently include standalone training or complete
  benchmark-reproduction scripts.
- Claude Code uses the same standard system prompt for the base and trained
  models.
- In the Codex comparison, the base model uses the standard prompt while
  SkillGym-Agent uses the no-applypatch prompt. The Codex difference therefore
  should not be attributed to fine-tuning alone.
- Public reference scores may use different harnesses, inference budgets,
  runtime configurations, system prompts, and model versions.

See the
[manuscript](assets/Internalizing_Large_Scale_Human_Written_Skills_into_LLMs_for_Real_World_Problem_Solving.pdf)
for complete evaluation details.

</details>


## Citation

The accompanying paper is currently under double-blind review.

Until final publication metadata is available, please use the provisional
project citation:

```bibtex
@misc{skillgym,
  title = {
    SkillGym: Internalizing Large-Scale Human-Written Skills
    into LLMs for Real-World Problem Solving
  },
  year = {2026},
  note = {Under review at ICLR 2027},
  url = {https://github.com/ECNU-ICALK/SkillGym}
}
```


## License

Repository-level code and materials are released under the
[MIT License](LICENSE).

Dataset source skills, fixtures, and supporting assets may retain upstream
notices or additional licensing terms. Preserve those notices when
redistributing the corresponding materials.
