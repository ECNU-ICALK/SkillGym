<p align="center">
  <picture>
    <source media="(prefers-color-scheme: dark)" srcset="assets/brand-dark.png">
    <source media="(prefers-color-scheme: light)" srcset="assets/brand-light.png">
    <img src="assets/brand-light.png" alt="SkillGym" width="560">
  </picture>
</p>

<div align="center">

<strong>将大规模人类编写技能内化到 LLM，用于真实世界问题求解</strong>

[![Paper](https://img.shields.io/badge/Paper-PDF-B31B1B)](assets/Internalizing_Large_Scale_Human_Written_Skills_into_LLMs_for_Real_World_Problem_Solving.pdf)
[![Dataset](https://img.shields.io/badge/🤗%20Dataset-SkillGym-FFD21E)](https://huggingface.co/datasets/ecnu-icalk/SkillGym)
[![Model](https://img.shields.io/badge/🤗%20Model-SkillGym--Agent-FFD21E)](https://huggingface.co/ecnu-icalk/SkillGym-Agent)
[![License](https://img.shields.io/badge/License-MIT-2EA44F)](LICENSE)

[English](README.md) · **简体中文**

<p align="center">
  <a href="#framework-and-contributions">框架与贡献</a> ·
  <a href="#dataset-at-a-glance">数据集</a> ·
  <a href="#main-results">实验结果</a> ·
  <a href="#quick-start">快速开始</a> ·
  <a href="#project-resources">项目资源</a> ·
  <a href="#release--reproducibility">发布与复现</a> ·
  <a href="#citation">引用</a>
</p>

</div>

**SkillGym** 将人类编写的技能转化为可执行、由验证器支撑的训练环境与经过验证的长程智能体轨迹，用于研究：外部提供的程序性知识，能否通过经验学习进一步转化为 LLM 智能体内部可复用的能力。

> **核心问题：** 由人类编写技能生成并经过验证的经验，能否进一步内化为模型内部可复用的程序性能力？

<p align="center">
  <a href="assets/skillgym_baseline.pdf">
    <img
      src="assets/skillgym_baseline.png"
      alt="SkillGym-Agent 在通用智能体基准上的表现"
      width="95%"
    >
  </a>
</p>

> **核心结论。** 在当前报告的评测中，SkillGym-Agent 在 Codex 与 Claude Code 两种 harness 下，均在 GDPval-AA v2、Terminal-Bench 2.1 与 SkillsBench v1.1 上高于同骨干基础模型。即使移除推理阶段的外部技能，SkillGym-Agent 的表现也仍超过带技能的基础模型，表明经过验证的工作流经验有一部分能够迁移为不依赖直接技能访问的模型能力。

<a id="framework-and-contributions"></a>

## 框架与贡献

SkillGym 将技能内化具体化为一条从 **人类编写的程序性知识** 出发，经过 **可执行环境构建** 与 **验证后的交互经验采样**，最终形成 **可复用智能体能力** 的完整路径。

<p align="center">
  <a href="assets/SkillGym.pdf">
    <img
      src="assets/skillgym_framework.jpg"
      alt="SkillGym 框架：从人类编写技能到可执行环境、验证轨迹与智能体训练"
      width="100%"
    >
  </a>
</p>

<p align="center">
  <sub><em>技能感知任务构建 → 环境验证 → 验证轨迹采样 → 能力内化</em></sub>
</p>

- **可执行技能落地。** SkillGym 将人类编写的智能体技能转化为具体任务环境，并显式定义输入、资源、运行时需求以及任务级验证器。
- **对比式技能依赖验证。** 通过成对的有技能 / 无技能执行，在参考构建设置下识别真正依赖目标程序性知识的任务。
- **验证驱动的长程经验。** 已接受环境支持跨多种 harness–model 配置进行多样化轨迹采样，并保留成功执行作为训练与分析数据。
- **超越直接技能访问的技能内化。** SkillGym-Agent 用于研究：从经过验证、由技能生成的经验中学习，是否能够形成即使在推理阶段无法访问外部技能时仍可复用的能力。

<a id="dataset-at-a-glance"></a>

## 数据集概览

<table>
  <tr>
    <td align="center" width="25%">
      <sub><strong>已接受环境</strong></sub><br>
      <strong>2,756</strong><br>
      <sub>可执行且通过验证</sub>
    </td>
    <td align="center" width="25%">
      <sub><strong>技能依赖环境</strong></sub><br>
      <strong>1,081</strong><br>
      <sub>占已接受环境的 39.2%</sub>
    </td>
    <td align="center" width="25%">
      <sub><strong>成功轨迹</strong></sub><br>
      <strong>8,364</strong><br>
      <sub>经过验证的长程执行</sub>
    </td>
    <td align="center" width="25%">
      <sub><strong>分类体系</strong></sub><br>
      <strong>12 / 63</strong><br>
      <sub>大类 / 子类</sub>
    </td>
  </tr>
</table>

<details>
<summary><strong>任务标签说明</strong></summary>

<br>

**Skill-Dep.** 表示在参考构建设置下满足更严格对比条件的环境；**Verifier-Passed** 表示环境本身能够正确执行并通过验证器检查，但未满足额外的 Skill-Dep. 条件。这些标签描述的是任务构建阶段的性质，并不保证后续任意模型或 harness 都会呈现完全相同的成功 / 失败行为。

</details>

<a id="main-results"></a>

## 主要实验结果

**GDPval-AA v2** 使用 Elo；**Terminal-Bench 2.1** 与 **SkillsBench v1.1** 使用任务成功率（%）。所有指标均为越高越好。

| Harness | 模型 | GDPval-AA v2<br>(Elo) ↑ | Terminal-Bench 2.1<br>(%) ↑ | SkillsBench v1.1<br>有技能 (%) ↑ | SkillsBench v1.1<br>无技能 (%) ↑ |
| --- | --- | ---: | ---: | ---: | ---: |
| Codex | Qwen3.5-35B-A3B | 942 | 10.11 | 5.33 | 0.69 |
| Codex | **SkillGym-Agent** | **979** | **46.07** | **33.02** | **21.08** |
| Claude Code | Qwen3.5-35B-A3B | 974 | 39.33 | 23.34 | 12.13 |
| Claude Code | **SkillGym-Agent** | **1173** | **58.43** | **51.47** | **26.81** |

公开发布的 **SkillGym-Agent** checkpoint 对应论文中的 **All Teachers** 设置，并使用发布的多 teacher–harness 配置所收集的全部 **8,364 条成功轨迹**进行训练。

在提供外部技能时，SkillGym-Agent 的表现仍然最高，**说明内化能力与显式技能之间更可能是互补关系，而非完全替代关系**。

<details>
<summary><strong>评测设置与说明</strong></summary>

<br>

| 基准 | 指标 | 评测设置 |
| --- | --- | --- |
| **GDPval-AA v2** | Elo | 通过盲测成对比较进行通用智能体评测 |
| **Terminal-Bench 2.1** | 成功率 (%) | 完整 89 个任务 |
| **SkillsBench v1.1** | 成功率 (%) | 全部 87 个任务，并同时评测 **有技能** 与 **无技能** 条件 |

- 在 **Claude Code** 下，基础模型和训练后模型使用相同的标准 system prompt。
- 在 **Codex** 下，基础模型使用标准 prompt，而 SkillGym-Agent 使用 `no-applypatch` prompt，因此 Codex 下的性能差异不能被视为纯粹由微调造成。
- Benchmark 结果依赖具体的 harness、prompt、运行环境、推理预算、checkpoint 与 benchmark 版本。
- 更完整的 teacher / harness 消融与评测配置请参阅[论文](assets/Internalizing_Large_Scale_Human_Written_Skills_into_LLMs_for_Real_World_Problem_Solving.pdf)。

</details>

<a id="quick-start"></a>

## 快速开始

### 使用发布数据

```bash
python -m pip install -U huggingface_hub

hf download ecnu-icalk/SkillGym \
  --include "Trajectories/*.jsonl" \
  --repo-type dataset \
  --local-dir .hf/skillgym
```

有关归档内容、轨迹 schema、任务标签、术语和加载示例，请参阅 [**SkillGym Dataset Card**](https://huggingface.co/datasets/ecnu-icalk/SkillGym)。

### 下载 SkillGym-Agent

```bash
hf download ecnu-icalk/SkillGym-Agent \
  --local-dir .hf/skillgym-agent
```

有关 Transformers 加载方式、checkpoint 元信息、预期用途与评测注意事项，请参阅 [**SkillGym-Agent Model Card**](https://huggingface.co/ecnu-icalk/SkillGym-Agent)。

### 构建新的技能驱动环境

```bash
git clone https://github.com/ECNU-ICALK/SkillGym.git
cd SkillGym

npm --prefix task_builder ci
npm --prefix task_builder run check
```

下载发布的技能库与任务模板：

```bash
hf download ecnu-icalk/SkillGym \
  skill_library.tar.zst task_templates.tar.zst \
  --repo-type dataset \
  --local-dir .hf/skillgym

tar --zstd -xf .hf/skillgym/skill_library.tar.zst
tar --zstd -xf .hf/skillgym/task_templates.tar.zst
```

随后请参阅 [Task Builder 指南](task_builder/README.md)，完成任务生成、验证、技能效果测试、修复和发布。完整生成流程还需要 Harbor、已配置的运行环境（如 E2B、Daytona 或 Docker），以及相应的模型 / 运行时凭证。

<a id="project-resources"></a>

## 项目资源

| 资源 | 内容 | 链接 |
| --- | --- | --- |
| **代码** | Task Builder、构建流程、文档、图表与项目材料 | [GitHub](https://github.com/ECNU-ICALK/SkillGym) |
| **数据集** | 技能库、任务模板、可执行环境与轨迹集合 | [Hugging Face](https://huggingface.co/datasets/ecnu-icalk/SkillGym) |
| **模型** | SkillGym-Agent，基于 Qwen3.5-35B-A3B 的发布 checkpoint | [Hugging Face](https://huggingface.co/ecnu-icalk/SkillGym-Agent) |
| **论文** | 完整方法、数据分析、实验、消融与附录 | [PDF](assets/Internalizing_Large_Scale_Human_Written_Skills_into_LLMs_for_Real_World_Problem_Solving.pdf) |

代码、数据集与模型仓库采用独立版本管理。大规模数据资产 snapshot 对应 GitHub commit `6ebabba`。

<a id="release--reproducibility"></a>

## 发布与复现

当前发布内容包括 **Task Builder**、配套的 **SkillGym 数据集与轨迹**，以及 **SkillGym-Agent checkpoint**。当前版本暂未包含独立的端到端训练代码，也未提供能够一次性复现全部外部 benchmark 的单一脚本。

论文报告的训练设置为：使用 **ms-swift / Megatron** 进行长上下文全参数监督微调，并使用 **16 × NVIDIA H200 GPU**。为了确保实验可追溯，建议记录实际使用的 GitHub commit 与 Hugging Face revision。

## 问题与贡献

欢迎通过 [GitHub Issues](https://github.com/ECNU-ICALK/SkillGym/issues) 提交问题、Bug 报告与功能建议，也欢迎通过 Pull Request 贡献 Task Builder 与项目文档。

若问题与数据集或 checkpoint 相关，请在 Issue 中附上对应的 Hugging Face 仓库与 revision。

<a id="citation"></a>

## 引用

配套论文目前处于双盲评审阶段。在正式出版信息确定前，可暂时使用以下引用：

```bibtex
@misc{skillgym2026,
  title = {Internalizing Large-Scale Human-Written Skills into LLMs for Real-World Problem Solving},
  year  = {2026},
  url   = {https://github.com/ECNU-ICALK/SkillGym}
}
```

## 许可证

仓库级代码与材料采用 [MIT License](LICENSE)。

数据集中来源技能、fixtures 与配套资产可能保留其上游声明或附加许可证条款。重新分发相应材料时，请保留这些声明；具体信息请参阅 Dataset Card。
