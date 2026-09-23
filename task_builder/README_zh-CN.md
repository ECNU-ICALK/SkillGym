<p align="center">
  <picture>
    <source media="(prefers-color-scheme: dark)" srcset="../assets/brand-dark.png">
    <source media="(prefers-color-scheme: light)" srcset="../assets/brand-light.png">
    <img src="../assets/brand-light.png" alt="SkillGym" width="420">
  </picture>
</p>

<h1 align="center">SkillGym Task Builder</h1>

<p align="center">
  <strong>将可复用技能与任务模板构建为可执行 Harbor 环境的开发者指南。</strong>
</p>

<p align="center">
  <a href="README.md">English</a> · <strong>简体中文</strong>
</p>

<p align="center">
  <a href="../README_zh-CN.md">项目概览</a>
  &nbsp;·&nbsp;
  <a href="docs/task-generation-pipeline.md">完整流程</a>
  &nbsp;·&nbsp;
  <a href="https://huggingface.co/datasets/ecnu-icalk/SkillGym">数据集</a>
  &nbsp;·&nbsp;
  <a href="../docs/migration.md">数据布局</a>
</p>

<p align="center">
  <a href="#what-this-component-does">组件概览</a> ·
  <a href="#before-you-run-it">运行准备</a> ·
  <a href="#quick-start">快速开始</a> ·
  <a href="#pipeline-and-acceptance-gates">构建流程</a> ·
  <a href="#output-layout">输出结构</a> ·
  <a href="#source-map">源码索引</a> ·
  <a href="#configuration">配置</a> ·
  <a href="#checks-and-tests">检查与测试</a>
</p>

<a id="what-this-component-does"></a>

> [!NOTE]
> Builder 使用 Codex 完成规划、任务编写、审查和修复，随后通过 Harbor 对每个候选任务进行验证，并执行有技能 / 无技能对比。

## 该组件做什么

| 阶段 | 职责 | 主要入口 |
| --- | --- | --- |
| 发现 | 在选定范围中查找模板与技能 | `inventory` |
| 编写 | 请求 Codex 规划并编写 Harbor 任务草稿 | `generate-family` |
| 审查 | 在执行前对任务草稿进行基于 Codex 的阻断式审查 | `src/codex.ts`, `src/prompts.ts` |
| 验证 | 运行静态检查与 Harbor 运行时验证 | `src/validate.ts` |
| 测量技能效果 | 比较同一任务在有目标技能和无目标技能情况下的表现 | `src/skill_effect.ts` |
| 修复 | 利用报告的问题与运行时证据修复失败草稿，然后重新进入审查与验证流程 | `src/cli.ts`, `src/codex.ts` |
| 发布 | 复制通过验收的变体并归档相关证据 | `src/materialize.ts`, `src/trace_archive.ts` |

> [!IMPORTANT]
> Builder 是一个任务构建流水线，不是 benchmark runner，也不是完整的 SFT 复现脚本。

<a id="before-you-run-it"></a>

## 运行前准备

本地仓库应包含：

```text
SkillGym/
├── skill_library/<major>/<minor>/skills/<skill>/
├── task_templates/<major>/<minor>/seed_task/
└── task_builder/
```

从 [SkillGym Hugging Face 数据集](https://huggingface.co/datasets/ecnu-icalk/SkillGym) 下载技能库与模板归档文件，然后在仓库根目录解压：

```bash
hf download ecnu-icalk/SkillGym \
  skill_library.tar.zst task_templates.tar.zst \
  --repo-type dataset --local-dir .hf/skillgym

tar --zstd -xf .hf/skillgym/skill_library.tar.zst
tar --zstd -xf .hf/skillgym/task_templates.tar.zst
```

安装锁定版本的 JavaScript 依赖：

```bash
npm --prefix task_builder ci
```

完整生成流程还需要 Harbor CLI、已配置的运行时环境（例如 e2b、Daytona 或 Docker），以及 [`.env.example`](../.env.example) 中列出的凭证。模型与沙箱服务可能产生费用。

<a id="quick-start"></a>

## 快速开始

### 查看可用单元

```bash
npm --prefix task_builder run inventory
```

### 生成一个任务族

请从仓库根目录运行：

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

上面的命令有意保持为最小配置。对于长时间运行的生产任务，请显式调整修复预算与超时预算：

| 选项 | 含义 |
| --- | --- |
| `--skill-mode all|per-skill` | 将全部技能一起使用，或按单个技能创建单元 |
| `--task-count` | 每个单元请求生成的任务数量 |
| `--concurrency` | 同时运行的活跃单元数量 |
| `--limit` | 限制发现到的单元数量 |
| `--scope-slug` | 将输出限制到指定 scope |
| `--task-attempt-timeout-hours` | 单次任务尝试的最长时间 |
| `--max-task-restarts` | 任务级重启次数 |
| `--max-pre-runtime-repair-rounds` | 运行时执行前允许的修复轮数 |
| `--max-runtime-repair-rounds` | 运行时失败后允许的修复轮数 |
| `--max-skill-effect-repair-rounds` | 技能效果对比后允许的修复轮数 |

> [!TIP]
> 一次运行可能持续数小时。建议先使用一个单元、并发设为 `1`，检查输出后再逐步扩大规模。

<a id="pipeline-and-acceptance-gates"></a>

## 流程与验收门槛

每个候选任务依次经历以下阶段：

1. **发现（Discovery）**：加载一个模板以及一个或多个技能。
2. **规划与编写（Planning and authoring）**：请求 Codex 创建任务计划与 Harbor 任务草稿。
3. **阻断式审查（Blocking review）**：在执行前检查当前任务草稿。
4. **验证（Validation）**：执行静态检查和 Harbor 运行时验证。
5. **技能效果验证（Skill-effect validation）**：比较 `with_skill` 与 `no_skill` 两次运行。
6. 如果某个门槛失败，Codex 会根据报告的问题与可用运行时证据修复草稿，随后任务重新进入审查和验证阶段。
7. 通过验收的任务变体会与其相关证据一起发布。

严格的技能效果门槛要求：有技能运行通过，同时无技能运行产生有效的 reward failure。当完整的有技能 / 无技能配对结果已经存在，但未满足严格门槛时，该候选任务可能会被写入 `oracle_fallback_success/`。

<a id="output-layout"></a>

## 输出结构

```text
outputs/
├── raw/                         # Workspaces, drafts, repairs, and runtime logs
├── final/
│   ├── pf_success/              # Strict with-skill / no-skill acceptance
│   └── oracle_fallback_success/ # Oracle passed; contrastive evidence incomplete
├── trace_archive/               # Paired runtime evidence and trajectories
└── manifest.jsonl               # Append-only event log and run summaries
```

已发布的任务变体包含任务计划、用户指令、元数据、环境、解决方案和测试。Materializer 只会将获批准的条目复制到 `final/`；原始 workspace 会继续保留，用于调试与修复分析。

<a id="source-map"></a>

## 源码索引

| 文件 | 职责 |
| --- | --- |
| [`src/cli.ts`](src/cli.ts) | CLI 参数解析、单元加载、流程编排、预算与发布 |
| [`src/discovery.ts`](src/discovery.ts) | 模板与技能发现；all / per-skill 模式 |
| [`src/codex.ts`](src/codex.ts) | Codex SDK threads、结构化输出、重试与修复轮次 |
| [`src/prompts.ts`](src/prompts.ts) | Planner、writer、reviewer 与 repair 指令 |
| [`src/schema.ts`](src/schema.ts) | Zod schemas 与 structured-output schemas |
| [`src/validate.ts`](src/validate.ts) | 静态检查、Harbor preflight、运行时验证与 reward 解析 |
| [`src/skill_effect.ts`](src/skill_effect.ts) | 有技能 / 无技能构造与评测 |
| [`src/materialize.ts`](src/materialize.ts) | 对已接受任务文件进行安全复制 |
| [`src/published.ts`](src/published.ts) | 断点续跑支持与已发布 ordinal 检测 |
| [`src/workspace.ts`](src/workspace.ts) | 创建任务族和任务尝试 workspace |
| [`src/trace_archive.ts`](src/trace_archive.ts) | 配对运行时证据与轨迹归档 |
| [`src/manifest.ts`](src/manifest.ts) | 追加式 manifest 与运行摘要 |

<a id="configuration"></a>

## 配置

仅当本地尚不存在 `.env` 时复制示例文件：

```bash
[ -f .env ] || cp .env.example .env
```

随后填写你的环境所需的 provider 凭证与运行时设置。示例文件记录了支持的变量，其中包括：

- `OPENAI_API_KEY`
- `OPENAI_BASE_URL`
- `E2B_API_KEY`
- `CODEX_TASK_BUILDER_RUNTIME_ENV`

Builder 不会自动配置模型访问权限或沙箱环境。开始长时间运行之前，请先确认这些服务可用。

<a id="checks-and-tests"></a>

## 检查与测试

从仓库根目录运行类型检查和针对性测试：

```bash
npm --prefix task_builder run check
npm --prefix task_builder run test:codex
npm --prefix task_builder run test:prompts
npm --prefix task_builder run test:validate
npm --prefix task_builder run test:skill-effect
node --import tsx task_builder/tests/harbor_metrics.test.ts
node --import tsx task_builder/tests/repo_paths.test.ts
```

CI workflow 会运行类型检查以及 `tests/*.test.ts` 文件。它不会启动会产生费用的端到端生成任务。

## 延伸阅读

- [任务生成流水线](docs/task-generation-pipeline.md) — 详细阶段、产物与修复语义。
- [仓库概览](../README_zh-CN.md) — 发布内容、HF 下载方式与论文背景。
- [数据迁移说明](../docs/migration.md) — 归档布局与路径行为。
- [Task Builder 源码](src/) 和 [测试](tests/) — 实现与回归测试覆盖。
