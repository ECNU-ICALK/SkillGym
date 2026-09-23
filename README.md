<div align="center">

<h1>🧠 SkillGym</h1>

<p><strong>Internalizing Large-Scale Human-Written Skills into LLMs for Real-World Problem Solving</strong></p>

<p><em>Turn human-written workflows into executable, verifiable agent experience — and train LLM agents to internalize reusable real-world capabilities.</em></p>

<p>
  <a href="https://huggingface.co/datasets/ecnu-icalk/SkillGym"><img src="https://img.shields.io/badge/🤗%20Dataset-SkillGym-FFD21E" alt="Hugging Face Dataset"></a>
  <a href="https://huggingface.co/ecnu-icalk/SkillGym-Agent"><img src="https://img.shields.io/badge/🤗%20Model-SkillGym--Agent-FFD21E" alt="Hugging Face Model"></a>
  <a href="task_builder/README.md"><img src="https://img.shields.io/badge/Task%20Builder-Developer%20Guide-4C78A8" alt="Task Builder"></a>
  <a href="assets/Internalizing_Large_Scale_Human_Written_Skills_into_LLMs_for_Real_World_Problem_Solving.pdf"><img src="https://img.shields.io/badge/Paper-PDF-B31B1B" alt="Paper PDF"></a>
  <a href="LICENSE"><img src="https://img.shields.io/badge/License-MIT-2EA44F" alt="MIT License"></a>
</p>

<p>
  <a href="https://huggingface.co/datasets/ecnu-icalk/SkillGym"><strong>Dataset</strong></a>
  &nbsp;·&nbsp;
  <a href="https://huggingface.co/ecnu-icalk/SkillGym-Agent"><strong>Model</strong></a>
  &nbsp;·&nbsp;
  <a href="task_builder/README.md"><strong>Task Builder</strong></a>
  &nbsp;·&nbsp;
  <a href="task_builder/docs/task-generation-pipeline.md"><strong>Pipeline</strong></a>
  &nbsp;·&nbsp;
  <a href="assets/Internalizing_Large_Scale_Human_Written_Skills_into_LLMs_for_Real_World_Problem_Solving.pdf"><strong>Paper</strong></a>
  &nbsp;·&nbsp;
  <a href="#quick-start"><strong>Quick Start</strong></a>
</p>

</div>

---

## TL;DR

**SkillGym** studies whether LLM agents can acquire **reusable procedural abilities** from **human-written skills**. It turns skill documents into **executable task environments**, validates outcomes with **code-based verifiers**, measures skill dependence through **with-skill / without-skill paired execution**, and collects successful **long-horizon trajectories** for agent training.

> **Core question:** Can verified experience generated from human-written skills become reusable capability inside the model itself?

## Highlights

<table>
  <tr>
    <td align="center"><strong>🏗️ 2,756</strong><br><sub>accepted environments</sub></td>
    <td align="center"><strong>🧪 5,512</strong><br><sub>with-skill / no-skill variants</sub></td>
    <td align="center"><strong>🧵 8,364</strong><br><sub>successful trajectories</sub></td>
    <td align="center"><strong>🗂️ 12 / 63</strong><br><sub>major / sub-categories</sub></td>
  </tr>
</table>

<p><sub>Counts correspond to the current manuscript snapshot. Environments, paired variants, sampled trials, and successful trajectories are different units.</sub></p>

### Project components

| Component | What it is | Start here |
| --- | --- | --- |
| **Dataset** | Skills, task templates, executable environments, and trajectories | [Hugging Face · SkillGym Dataset](https://huggingface.co/datasets/ecnu-icalk/SkillGym) |
| **Model** | Released checkpoint trained on successful SkillGym trajectories | [Hugging Face · SkillGym-Agent](https://huggingface.co/ecnu-icalk/SkillGym-Agent) |
| **Task Builder** | The construction pipeline for new skill-grounded environments | [Task Builder Guide](task_builder/README.md) |

> [!TIP]
> **Want to use the released data or model?** Start from Hugging Face.  
> **Want to create new skill-grounded environments?** Start from the [Task Builder](task_builder/README.md).

## Overview

<p align="center">
  <a href="assets/SkillGym.pdf">
    <img src="assets/skillgym_framework.jpg" alt="SkillGym framework: skill-aware task construction, validation, paired skill-dependence evaluation, and trajectory collection." width="100%">
  </a>
</p>

<p align="center"><em>SkillGym converts human-written skills into executable, verifiable environments and then samples successful long-horizon trajectories across multiple harness-model configurations.</em></p>

### How SkillGym works

| Stage | What happens |
| --- | --- |
| **1 · Ground** | Organize reusable skill cards and category-specific task templates |
| **2 · Build** | Instantiate objectives, inputs, runtime requirements, and verification specifications |
| **3 · Verify** | Run static checks, Harbor execution, oracle validation, and code-based verifiers |
| **4 · Contrast** | Execute paired tasks with and without the target skill |
| **5 · Learn** | Collect successful long-horizon trajectories for training and analysis |

A task enters the strict **Skill-Dep** group when the <code>with_skill</code> execution succeeds while the paired <code>no_skill</code> execution produces a valid reward failure. Other valid verifier-passed tasks are released separately as **Verifier-Passed** fallback environments.

For the full construction pipeline, repair semantics, and output layout, see [task_builder/docs/task-generation-pipeline.md](task_builder/docs/task-generation-pipeline.md).

## Results

### General-agent benchmark overview

<p align="center">
  <a href="assets/skillgym_baseline.pdf">
    <img src="assets/skillgym_baseline.png" alt="SkillGym-Agent benchmark overview" width="100%">
  </a>
</p>

<p align="center"><em>General-agent benchmark results from the current manuscript. Click the figure to open the PDF version.</em></p>

### Controlled same-backbone comparison

**SkillGym-Agent** is a full-parameter supervised fine-tuned Qwen3.5-35B-A3B model trained on successful SkillGym trajectories.

| Harness | Model | GDPval-AA v2 ↑ | Terminal-Bench 2.1 ↑ | SkillsBench v1.1 ↑ | Without skills ↑ |
| --- | --- | ---: | ---: | ---: | ---: |
| Codex | Qwen3.5-35B-A3B (base) | 942 | 10.11 | 5.33 | 0.69 |
| Codex | **SkillGym-Agent** | **979 (+37)** | **46.07 (+35.96)** | **33.02 (+27.69)** | **21.08 (+20.39)** |
| Claude Code | Qwen3.5-35B-A3B (base) | 974 | 39.33 | 23.34 | 12.13 |
| Claude Code | **SkillGym-Agent** | **1173 (+199)** | **58.43 (+19.10)** | **51.47 (+28.13)** | **26.81 (+14.68)** |

Parenthesized values are absolute Elo or percentage-point gains over the same-harness base model.

### Key takeaway: skill-free transfer

The most informative signal is what remains **without an inference-time skill**:

- Under **Claude Code**, SkillGym-Agent without skills reaches **26.81%**, versus **23.34%** for the base model *with* skills.
- Under **Codex**, SkillGym-Agent without skills reaches **21.08%**, versus **5.33%** for the base model *with* skills.

These results suggest that verified workflow experience can transfer beyond direct prompt following. At the same time, SkillGym-Agent performs best when external skills remain available, indicating that **internalized capability and explicit skills are complementary**.

<details>
<summary><strong>Teacher and harness ablation</strong></summary>

<br>

| Harness | Teacher setting | GDPval-AA v2 | Terminal-Bench 2.1 | SkillsBench v1.1 | Without skills |
| --- | --- | ---: | ---: | ---: | ---: |
| Codex | GPT-5.4 | 969 | 24.72 | 14.00 | 6.96 |
| Codex | Nex-N2-Pro | 1074 | 33.71 | 13.59 | 12.61 |
| Codex | GPT+Nex | 976 | 40.45 | 19.91 | 13.59 |
| Codex | **All Teachers** | **979** | **46.07** | **33.02** | **21.08** |
| Claude Code | DeepSeek V4 Pro | 1106 | 43.82 | 28.81 | 19.02 |
| Claude Code | GLM-5.2 | **1212** | 55.06 | 45.50 | 25.10 |
| Claude Code | DeepSeek+GLM | 1161 | 57.30 | 47.33 | **28.41** |
| Claude Code | **All Teachers** | 1173 | **58.43** | **51.47** | 26.81 |

</details>

## Releases

Large artifacts live in the companion [Hugging Face dataset](https://huggingface.co/datasets/ecnu-icalk/SkillGym), keeping this GitHub repository focused on construction code, documentation, and lightweight figures.

### Release summary

| Release signal | Value |
| --- | --- |
| Accepted environments | **2,756** |
| Skill-Dep / Verifier-Passed | **1,081 / 1,675** |
| Successful trajectories | **8,364** from 48,152 trials |
| Trial-level success rate | **17.4%** |
| Deduplicated coverage | **2,302** unique tasks |
| Average successful trajectory | **49.0** tool calls · **63.4k** logged text tokens · **35.2** interaction steps |
| Longest observed trajectory | **350** tool calls · **342.9k** logged text tokens · **318** interaction steps |

### Available artifacts

| Artifact | What it contains | Get it |
| --- | --- | --- |
| <code>Tasks.tar.zst</code> | Published paired task environments | [HF Dataset](https://huggingface.co/datasets/ecnu-icalk/SkillGym/blob/main/Tasks.tar.zst) |
| <code>skill_library.tar.zst</code> | Human-written skills and supporting assets | [HF Dataset](https://huggingface.co/datasets/ecnu-icalk/SkillGym/blob/main/skill_library.tar.zst) |
| <code>task_templates.tar.zst</code> | Reusable seed task templates and fixtures | [HF Dataset](https://huggingface.co/datasets/ecnu-icalk/SkillGym/blob/main/task_templates.tar.zst) |
| <code>Trajectories/*.jsonl</code> | Eight trajectory collections by result type, harness, and teacher | [HF Dataset](https://huggingface.co/datasets/ecnu-icalk/SkillGym/tree/main/Trajectories) |
| <code>SkillGym-Agent</code> | Released trained checkpoint | [HF Model](https://huggingface.co/ecnu-icalk/SkillGym-Agent) |

The large-artifact snapshot is associated with GitHub commit <code>6ebabba</code>; the GitHub codebase may evolve independently from that snapshot.

For schema details, task layout, licensing notes, and intended use, see the full [Hugging Face Dataset Card](https://huggingface.co/datasets/ecnu-icalk/SkillGym).

<a id="quick-start"></a>
## Quick Start

Choose the path that matches what you want to do.

### 1. Use the released trajectories

~~~bash
python -m pip install -U huggingface_hub

hf download ecnu-icalk/SkillGym   --include "Trajectories/*.jsonl"   --repo-type dataset   --local-dir .hf/skillgym
~~~

Stream one trajectory file directly:

~~~python
from datasets import load_dataset

trajectories = load_dataset(
    "json",
    data_files={
        "train": (
            "hf://datasets/ecnu-icalk/SkillGym/"
            "Trajectories/skill_dependent_claude_code_deepseek_v4_pro.jsonl"
        )
    },
    split="train",
    streaming=True,
)

print(next(iter(trajectories))["session_id"])
~~~

### 2. Use SkillGym-Agent

~~~bash
python -m pip install -U huggingface_hub

hf download ecnu-icalk/SkillGym-Agent   --local-dir .hf/skillgym-agent
~~~

→ [Open SkillGym-Agent on Hugging Face](https://huggingface.co/ecnu-icalk/SkillGym-Agent)

### 3. Build a new task family

~~~bash
git clone https://github.com/ECNU-ICALK/SkillGym.git
cd SkillGym

npm --prefix task_builder ci
npm --prefix task_builder run check

python -m pip install -U huggingface_hub
hf download ecnu-icalk/SkillGym   skill_library.tar.zst task_templates.tar.zst   --repo-type dataset   --local-dir .hf/skillgym

tar --zstd -xf .hf/skillgym/skill_library.tar.zst
tar --zstd -xf .hf/skillgym/task_templates.tar.zst
~~~

Generate one small task family:

~~~bash
npm --prefix task_builder run generate-family --   --template-root task_templates   --template development/frontend/seed_task   --skill-dir skill_library/development/frontend/skills/tailwind-design-system   --skill-mode per-skill   --task-count 1   --output-root /tmp/skillgym-output   --concurrency 1
~~~

> [!IMPORTANT]
> Full generation additionally requires Harbor, a configured runtime such as E2B, Daytona, or Docker, and the relevant model/runtime credentials. Runs can take hours and may invoke paid services. See the [Task Builder guide](task_builder/README.md) before scaling up.

<details>
<summary><strong>Evaluation details and caveats</strong></summary>

<br>

> [!NOTE]
> **GDPval-AA v2** is reported as Elo. **Terminal-Bench 2.1** and **SkillsBench v1.1** are reported as task success rates (%).

> [!IMPORTANT]
> The latest manuscript reports long-context full-parameter SFT with ms-swift/Megatron on 16 NVIDIA H200 GPUs. The repository releases the Task Builder, data, trajectories, and checkpoint, but does not currently include standalone training or full benchmark-reproduction scripts.

> [!CAUTION]
> Claude Code uses the same standard system prompt for the base and trained models. In the Codex comparison, the base model uses the standard prompt while SkillGym-Agent uses the no-applypatch prompt, so the Codex score difference should not be attributed to fine-tuning alone.

Public reference scores may use different harnesses, inference budgets, runtime configurations, and model versions. They provide context rather than strictly controlled head-to-head comparisons.

See the [manuscript](assets/Internalizing_Large_Scale_Human_Written_Skills_into_LLMs_for_Real_World_Problem_Solving.pdf) for complete tables and evaluation details.

</details>

## Documentation

| I want to… | Start here |
| --- | --- |
| Download environments or trajectories | [Hugging Face Dataset](https://huggingface.co/datasets/ecnu-icalk/SkillGym) |
| Download the trained checkpoint | [SkillGym-Agent](https://huggingface.co/ecnu-icalk/SkillGym-Agent) |
| Build new environments | [Task Builder](task_builder/README.md) |
| Understand the complete construction flow | [Task-generation pipeline](task_builder/docs/task-generation-pipeline.md) |
| Understand data migration and snapshot layout | [Migration notes](docs/migration.md) |
| Read the paper | [Manuscript PDF](assets/Internalizing_Large_Scale_Human_Written_Skills_into_LLMs_for_Real_World_Problem_Solving.pdf) |

## Citation

The accompanying paper is currently under double-blind review. Until final publication metadata is available, use the provisional project citation:

~~~bibtex
@misc{skillgym,
  title = {SkillGym: Internalizing Human Skills into LLMs for Real-World Problem Solving},
  year  = {2026},
  note  = {Under review at ICLR 2027},
  url   = {https://github.com/ECNU-ICALK/SkillGym}
}
~~~

Please use the final paper citation once the review process is complete.

## License

Repository-level code and materials are released under the [MIT License](LICENSE).

The dataset contains source skills, fixtures, and supporting assets that may retain upstream notices or additional licensing terms. Preserve those notices when redistributing the corresponding materials.
