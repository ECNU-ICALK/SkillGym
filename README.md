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
  <strong>SkillGym: Internalizing Human Skills into LLMs for Real-World Problem Solving</strong>
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
    From human-written skills to executable environments, verified interaction
    experience, and reusable procedural competence.
  </em>
</p>

</div>

<p align="center">
  <a href="assets/SkillGym.pdf">
    <img
      src="assets/skillgym_framework.jpg"
      alt="Overview of the SkillGym construction framework"
      width="100%"
    >
  </a>
</p>

<p align="center">
  <sub>
    <em>
      SkillGym organizes human-written skills into reusable task templates,
      instantiates Docker-based environments with code-based verifiers,
      assesses empirical skill dependence under a reference agent configuration,
      and samples successful long-horizon trajectories across multiple
      harness-model combinations.
    </em>
  </sub>
</p>


## Overview

Human-written agent skills encode rich workflows, examples, scripts, and execution
constraints, but they are usually supplied as external instructions at inference time.
**SkillGym** studies a different use of these artifacts: transforming them into
executable, verifiable training environments from which agents can learn through
interaction and outcome feedback.

The framework connects four components:

- **human-written procedural knowledge**, represented through structured skill cards;
- **reusable task templates**, which specify task structure and verification requirements;
- **executable environments and code-based verifiers**, which evaluate task outcomes;
- **verified interaction trajectories**, which support supervised fine-tuning, while
  the environments and verifiers can support reinforcement learning with outcome-based rewards.

> [!NOTE]
> **Research question:** Can human-written agent skills be transformed into executable
> training environments in which LLMs acquire procedural competence through practice
> and feedback?


## Highlights

<table>
  <tr>
    <td align="center" width="25%">
      <sub><strong>ACCEPTED ENVIRONMENTS</strong></sub><br>
      <strong>2,756</strong><br>
      <sub>executable and verifier-passed</sub>
    </td>
    <td align="center" width="25%">
      <sub><strong>SKILL-DEP.</strong></sub><br>
      <strong>1,081</strong><br>
      <sub>39.2% of accepted environments</sub>
    </td>
    <td align="center" width="25%">
      <sub><strong>SUCCESSFUL TRAJECTORIES</strong></sub><br>
      <strong>8,364</strong><br>
      <sub>from 48,152 sampled trials</sub>
    </td>
    <td align="center" width="25%">
      <sub><strong>TAXONOMY</strong></sub><br>
      <strong>12 / 63</strong><br>
      <sub>major / sub-categories</sub>
    </td>
  </tr>
</table>

<p align="center">
  <sub>
    Accepted environments cover all 63 sub-categories; the successful-trajectory
    corpus covers 62 of 63 sub-categories and 2,302 unique tasks after deduplication.
  </sub>
</p>

### Main contributions

- **Skill-to-task construction.** SkillGym turns reusable human-written workflows
  into concrete task environments with input assets, execution interfaces, runtime
  specifications, and task-specific outcome verifiers.
- **Two-level acceptance.** Environments are first checked for executable correctness
  and then assessed for empirical skill dependence through contrastive executions
  with and without the target skill.
- **Verified long-horizon experience.** The released successful trajectories average
  **49.0 tool calls**, **63.4k logged text tokens**, and **35.2 interaction steps**.
- **Skill-derived model training.** Long-context, full-parameter supervised fine-tuning
  on collected trajectories yields the 35B **SkillGym-Agent**, with improvements that
  persist when inference-time skills are removed.


<a id="main-results"></a>

## Main Results

<p align="center">
  <a href="assets/skillgym_baseline.pdf">
    <img
      src="assets/skillgym_baseline.png"
      alt="SkillGym-Agent results on general-agent benchmarks"
      width="100%"
    >
  </a>
</p>

<p align="center">
  <sub>
    <em>
      General-agent benchmark results from the current manuscript. Click the figure
      to open the vector PDF. Public-reference scores provide context but may use
      different harnesses, inference budgets, runtime environments, and evaluation settings.
    </em>
  </sub>
</p>

**SkillGym-Agent** is a Qwen3.5-35B-A3B model obtained through long-context,
full-parameter supervised fine-tuning on collected SkillGym trajectories. The reported
checkpoint is trained with supervised fine-tuning; reinforcement learning in the
released environments is left to future work.

<table>
  <tr>
    <td align="center" width="33%">
      <sub><strong>CLAUDE CODE GAINS</strong></sub><br>
      <strong>+199 Elo</strong><br>
      <sub>GDPval-AA v2</sub><br><br>
      <strong>+19.10 pp</strong><br>
      <sub>Terminal-Bench 2.1</sub><br><br>
      <strong>+28.13 / +14.68 pp</strong><br>
      <sub>SkillsBench w/ / w/o Skills</sub>
    </td>
    <td align="center" width="33%">
      <sub><strong>CODEX GAINS</strong></sub><br>
      <strong>+37 Elo</strong><br>
      <sub>GDPval-AA v2</sub><br><br>
      <strong>+35.96 pp</strong><br>
      <sub>Terminal-Bench 2.1</sub><br><br>
      <strong>+27.69 / +20.39 pp</strong><br>
      <sub>SkillsBench w/ / w/o Skills</sub>
    </td>
    <td align="center" width="34%">
      <sub><strong>WITHOUT INFERENCE-TIME SKILLS</strong></sub><br>
      <strong>26.81% &gt; 23.34%</strong><br>
      <sub>SkillGym-Agent w/o Skills vs. base w/ Skills<br>under Claude Code</sub><br><br>
      <strong>21.08% &gt; 5.33%</strong><br>
      <sub>SkillGym-Agent w/o Skills vs. base w/ Skills<br>under Codex</sub>
    </td>
  </tr>
</table>

Under Claude Code, SkillGym-Agent improves over its same-backbone base on all four
reported metrics and outperforms all evaluated comparable-scale baselines. On
skill-assisted SkillsBench v1.1, it reaches **51.47%**. Performance remains lower
without the external skill package than with it, suggesting that learned procedural
competence and inference-time procedural guidance remain complementary.

> [!IMPORTANT]
> The Claude Code base and SkillGym-Agent use the same standard system prompt.
> In the Codex comparison, the base uses the standard prompt while SkillGym-Agent
> uses the no-applypatch prompt. The Codex performance difference therefore cannot
> be attributed solely to fine-tuning.

<details>
<summary><strong>Same-backbone benchmark results</strong></summary>

<br>

| Harness | Model | GDPval-AA v2<br>(Elo) ↑ | Terminal-Bench 2.1<br>(Success rate, %) ↑ | SkillsBench v1.1<br>(w/ Skills, %) ↑ | SkillsBench v1.1<br>(w/o Skills, %) ↑ |
| --- | --- | ---: | ---: | ---: | ---: |
| Codex | Qwen3.5-35B-A3B (Base) | 942 | 10.11 | 5.33 | 0.69 |
| Codex | **SkillGym-Agent (Ours)** | **979** (+37) | **46.07** (+35.96) | **33.02** (+27.69) | **21.08** (+20.39) |
| Claude Code | Qwen3.5-35B-A3B (Base) | 974 | 39.33 | 23.34 | 12.13 |
| Claude Code | **SkillGym-Agent (Ours)** | **1173** (+199) | **58.43** (+19.10) | **51.47** (+28.13) | **26.81** (+14.68) |

<sub>
GDPval-AA v2 is reported as Elo. Terminal-Bench 2.1 and both SkillsBench v1.1
conditions are reported as task success rates. Parenthesized values are absolute
improvements over the corresponding Qwen3.5-35B-A3B base evaluated under the same
harness: Elo points for GDPval-AA v2 and percentage points for the success-rate metrics.
</sub>

</details>

### Performance without inference-time skills

When the SkillsBench skill packages are removed at inference time, SkillGym-Agent
retains substantial improvements over its base model. It also exceeds the
skill-assisted base under both harnesses:

- **Claude Code:** 26.81% without skills vs. 23.34% for the base with skills.
- **Codex:** 21.08% without skills vs. 5.33% for the base with skills.

These results are consistent with skill-derived execution experience supporting
reusable procedural competence beyond direct access to external instructions. They
should be interpreted together with the Codex system-prompt caveat above.


## How SkillGym Works

The manuscript organizes SkillGym into three construction stages:

<table>
  <tr>
    <td align="center" width="33%">
      <sub><strong>STAGE A</strong></sub><br>
      <strong>Skill-Aware Template Construction</strong><br><br>
      <sub>
        Organize human-written skills into a taxonomy and structured skill cards;
        design reusable, category-specific task templates and verifier requirements.
      </sub>
    </td>
    <td align="center" width="34%">
      <sub><strong>STAGE B</strong></sub><br>
      <strong>Environment Construction &amp; Validation</strong><br><br>
      <sub>
        Instantiate Docker-based tasks, validate feasibility and verifier behavior,
        assess empirical skill dependence, and refine failures.
      </sub>
    </td>
    <td align="center" width="33%">
      <sub><strong>STAGE C</strong></sub><br>
      <strong>Multi-Harness Trajectory Sampling</strong><br><br>
      <sub>
        Run multiple harness-model configurations and retain interaction traces with
        task-specific verifier outcomes.
      </sub>
    </td>
  </tr>
</table>

### Two-level environment acceptance

An environment must first pass design, structure, end-to-end execution, and verifier
checks. A reference agent is then evaluated both with and without the target skill:

- **Skill-Dep.**: feasibility checks pass, the reference agent succeeds with the skill,
  and the paired execution without the skill fails: `(with_skill, no_skill) = (1, 0)`.
- **Verifier-Passed**: feasibility and outcome-verification checks pass, but the task
  does not satisfy the additional `(1, 0)` contrastive criterion.
- **Discarded**: executable correctness or verification checks fail.

> [!CAUTION]
> The **Skill-Dep.** label provides empirical evidence of dependence under the
> reference agent configuration used during construction. It does not prove that the
> skill is necessary for every model, harness, or future agent configuration.

For implementation details, failure-driven refinement, validation stages, and output
layout, see the
[task-generation pipeline](task_builder/docs/task-generation-pipeline.md).


## Resources

| Resource | What it contains | Access |
| --- | --- | --- |
| **🤗 SkillGym Dataset** | Skill cards, reusable task templates, executable environments, verifiers, and trajectory records | [Hugging Face](https://huggingface.co/datasets/ecnu-icalk/SkillGym) |
| **🤗 SkillGym-Agent** | Qwen3.5-35B-A3B checkpoint trained on successful SkillGym trajectories | [Hugging Face](https://huggingface.co/ecnu-icalk/SkillGym-Agent) |
| **🛠 Task Builder** | Pipeline for constructing and validating new skill-derived environments | [Developer Guide](task_builder/README.md) |
| **📘 Pipeline Documentation** | Task generation, repair semantics, validation, and output organization | [Documentation](task_builder/docs/task-generation-pipeline.md) |
| **📄 Manuscript** | Method, dataset analysis, experiments, ablations, and appendices | [PDF](assets/Internalizing_Large_Scale_Human_Written_Skills_into_LLMs_for_Real_World_Problem_Solving.pdf) |


<a id="quick-start"></a>

## Quick Start

### 1. Download the trajectory data

```bash
python -m pip install -U huggingface_hub

hf download ecnu-icalk/SkillGym \
  --include "Trajectories/*.jsonl" \
  --repo-type dataset \
  --local-dir .hf/skillgym
```

<details>
<summary><strong>Stream a trajectory collection with 🤗 Datasets</strong></summary>

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


### 2. Download SkillGym-Agent

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
> Full task generation additionally requires Harbor, a configured runtime such as
> **E2B**, **Daytona**, or **Docker**, and the relevant model/runtime credentials.
> Read the [Task Builder guide](task_builder/README.md) before scaling up.


## Technical Details

<details>
<summary><strong>Dataset and trajectory summary</strong></summary>

<br>

| Release statistic | Value |
| --- | --- |
| Accepted environments | **2,756** |
| Skill-Dep. / Verifier-Passed | **1,081 / 1,675** |
| Successful trajectories | **8,364** from 48,152 sampled trials |
| Successful trajectories from Skill-Dep. / Verifier-Passed tasks | **3,722 / 4,642** |
| Overall sampled-trial success rate | **17.4%** |
| Deduplicated task coverage | **2,302** unique tasks |
| Successful-trajectory taxonomy coverage | **12** major categories and **62 / 63** sub-categories |
| Explicit target-skill invocation | **3,077 trajectories (36.8%)** |
| Average successful trajectory | **49.0** tool calls · **63.4k** logged text tokens · **35.2** interaction steps |
| Corpus-wide maxima | **350** tool calls · **342.9k** logged text tokens · **318** interaction steps |

<p>
  <sub>
    Tool-call, token, and interaction-step maxima are corpus-wide maxima for their
    respective measures and need not come from the same trajectory. Logged or saved-text
    token counts do not represent API usage or single-request context length.
  </sub>
</p>

### Released artifacts

| Artifact | Contents |
| --- | --- |
| `Tasks.tar.zst` | Published skill-derived task environments and verifiers |
| `skill_library.tar.zst` | Human-written skills and supporting assets |
| `task_templates.tar.zst` | Reusable seed-task templates and fixtures |
| `Trajectories/*.jsonl` | Trajectory collections organized by result type, harness, and teacher |
| `SkillGym-Agent` | Released trained checkpoint |

The large-artifact snapshot is associated with GitHub commit `6ebabba`.
For schema details, task layout, licensing notes, and intended use, see the
[Hugging Face Dataset Card](https://huggingface.co/datasets/ecnu-icalk/SkillGym).

</details>


<details>
<summary><strong>Teacher-setting and harness ablation</strong></summary>

<br>

| Evaluation harness | Teacher setting | GDPval-AA v2<br>(Elo) ↑ | Terminal-Bench 2.1<br>(Success rate, %) ↑ | SkillsBench v1.1<br>(w/ Skills, %) ↑ | SkillsBench v1.1<br>(w/o Skills, %) ↑ |
| --- | --- | ---: | ---: | ---: | ---: |
| Codex | Base | 942 | 10.11 | 5.33 | 0.69 |
| Codex | GPT-5.4 | 969 (+27) | 24.72 (+14.61) | 14.00 (+8.67) | 6.96 (+6.27) |
| Codex | Nex-N2-Pro | **1074** (+132) | 33.71 (+23.60) | 13.59 (+8.26) | 12.61 (+11.92) |
| Codex | GPT+Nex | 976 (+34) | 40.45 (+30.34) | 19.91 (+14.58) | 13.59 (+12.90) |
| Codex | **All Teachers** | 979 (+37) | **46.07** (+35.96) | **33.02** (+27.69) | **21.08** (+20.39) |
| Claude Code | Base | 974 | 39.33 | 23.34 | 12.13 |
| Claude Code | DeepSeek V4 Pro | 1106 (+132) | 43.82 (+4.49) | 28.81 (+5.47) | 19.02 (+6.89) |
| Claude Code | GLM-5.2 | **1212** (+238) | 55.06 (+15.73) | 45.50 (+22.16) | 25.10 (+12.97) |
| Claude Code | DeepSeek+GLM | 1161 (+187) | 57.30 (+17.97) | 47.33 (+23.99) | **28.41** (+16.28) |
| Claude Code | **All Teachers** | 1173 (+199) | **58.43** (+19.10) | **51.47** (+28.13) | 26.81 (+14.68) |

<sub>
Best result within each evaluation harness and metric is bolded. Parenthesized
values are absolute improvements over the corresponding base. The **All Teachers**
setting pools trajectories collected under both Codex and Claude Code; differences
therefore reflect changes in teacher composition, harness diversity, and data volume
rather than an isolated single factor.
</sub>

</details>


<details>
<summary><strong>Benchmark scope and evaluation notes</strong></summary>

<br>

| Benchmark | Reported metric | Evaluated setting |
| --- | --- | --- |
| **GDPval-AA v2** | Elo from blind pairwise comparisons | Evaluation pipeline based on NVIDIA NeMo Gym |
| **Terminal-Bench 2.1** | Task success rate (%) | Official Harbor implementation; full set of 89 tasks |
| **SkillsBench v1.1** | Task success rate (%) | All 87 tasks under both **w/ Skills** and **w/o Skills** conditions |

- Terminal-Bench 2.1 and SkillsBench v1.1 preserve the official benchmark
  environment configurations while running in self-hosted sandbox infrastructure
  built on OpenSandbox.
- Claude Code uses `temperature=0.6`, `top_p=0.95`, and `top_k=20`.
  Codex retains its default sampling parameters.
- Both harnesses use `max_tokens=65536` and a context window of 262,144 tokens.
- Under Claude Code, the base and SkillGym-Agent use the same standard system prompt.
- Under Codex, the base uses the standard prompt and SkillGym-Agent uses the
  no-applypatch prompt; this same-backbone result is therefore not a pure
  fine-tuning-only comparison.
- Public-reference scores may differ in harness, inference budget, runtime,
  checkpoint, and evaluation configuration, and should not be read as strictly
  controlled head-to-head comparisons.
- An em dash in the manuscript's public-reference table means that no verifiable
  result was identified for the exact model-benchmark-evaluation setting; it does
  not indicate zero performance.

See the
[manuscript](assets/Internalizing_Large_Scale_Human_Written_Skills_into_LLMs_for_Real_World_Problem_Solving.pdf)
for complete evaluation details.

</details>


## Citation

The accompanying paper is currently under double-blind review. Until final
publication metadata is available, please use the provisional project citation:

```bibtex
@misc{skillgym,
  title = {SkillGym: Internalizing Human Skills into LLMs for Real-World Problem Solving},
  year  = {2026},
  note  = {Under review at ICLR 2027},
  url   = {https://github.com/ECNU-ICALK/SkillGym}
}
```


## License

Repository-level code and materials are released under the
[MIT License](LICENSE).

Dataset source skills, fixtures, and supporting assets may retain upstream notices
or additional licensing terms. Preserve those notices when redistributing the
corresponding materials.
