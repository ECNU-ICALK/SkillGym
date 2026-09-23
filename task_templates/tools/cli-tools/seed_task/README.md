# CLI-Tools Template

这是面向 `cli-tools` 类 skill 的模板。它综合参考 SkillsMP `cli-tools` 类热门 skill 的共性能力：命令发现、仓库内标准入口复用、分阶段打包、CLI smoke 校验和发布物复核。

## 第一部分：任务设计参考

* **Skill 价值定位**：`cli-tools` 类热门 skill 的关键价值，在于帮助 Agent 先识别仓库已经提供的命令面，再沿着这些入口完成构建、打包、校验和交付。对 `discovering-make-commands` 这类 skill 来说，重点是把动作收敛到仓库既有的 `make` 工作流，避免直接跳到临时脚本或单步输出。
* **Verifier 设计重点**：Verifier 应优先检查 solver 是否沿项目内的命令入口完成分阶段打包和 smoke 校验，并验证 manifest、checksum、命令目录和发布物之间是否互相一致。除了输出内容，还要覆盖重跑稳定性、输入不可改写、打包产物来源和命令目录对齐。

## 第二部分：示例任务

### 📌 任务元数据
- 任务 ID：`cli-tools__airdesk-release-pack`
- 类别：`cli-tools`
- 绑定 Skill：`discovering-make-commands`
- 输入数据参考来源：
  - `environment/data/ourairports/countries.csv`：任务内国家参考数据；数据直接来源于  
    `https://raw.githubusercontent.com/davidmegginson/ourairports-data/main/countries.csv`
  - `environment/data/ourairports/regions.csv`：任务内地区参考数据；数据直接来源于  
    `https://raw.githubusercontent.com/davidmegginson/ourairports-data/main/regions.csv`
  - `environment/data/ourairports/airports.csv`：任务内机场目录快照；数据直接来源于  
    `https://raw.githubusercontent.com/davidmegginson/ourairports-data/main/airports.csv`
  - `environment/data/ourairports/runways.csv`：任务内跑道元数据；数据直接来源于  
    `https://raw.githubusercontent.com/davidmegginson/ourairports-data/main/runways.csv`
  - `environment/data/ourairports/airport-frequencies.csv`：任务内机场频率元数据；数据直接来源于  
    `https://raw.githubusercontent.com/davidmegginson/ourairports-data/main/airport-frequencies.csv`

### 📊 验证与测试指标（Oracle & Verifier）
- Oracle：按正式流程独立运行并完成交付，结果可直接 100% 通过验证。
- Verifier策略：

主测试
| 测试点 | 验证内容 | 对应skill内化点 |
| :--- | :--- | :--- |
| 发布输出契约 | 校验 manifest、checksum、smoke 期望和 Markdown 的结构、字段与 contract 口径 | 沿项目交付链写出完整产物 |
| 打包产物 | 校验发布目录中存在可解包、可执行的 CLI 发布物 | 通过项目打包入口产出完整发布物 |
| smoke 场景 | 校验 contract 中定义的全部命令场景都通过，并由打包产物执行 | 命令发现、CLI 校验、入口复用 |
| 命令目录 | 校验 `command_catalog.md` 与项目命令面一致 | 先识别仓库命令，再组织交付 |
| 重跑稳定性 | 同一输入下按记录的最终 make target 复跑后输出仍保持一致 | 可重复执行的 CLI 工作流 |

防作弊测试
| 测试点 | 验证内容 |
| :--- | :--- |
| 输入完整性 | 机场数据和 contract 不可修改 |
| 产物来源 | 交付中的 CLI 包必须来自工作区项目，不能用外部脚本替代 |
| smoke 期望来源 | smoke 期望必须由输入数据推导，不能手写固定答案 |

### ⚡ Skill 相关性评估

结论：强相关。这个任务里，Skill 的核心价值落在先列出仓库已有 make 命令、再按阶段完成初始化、校验、打包和最终交付。对照结果显示 without skill 更容易跳到局部命令或直接终态 target，遗漏 `python-init` 这类前置动作；with skill 更容易收敛到仓库提供的阶段化工作流。

基于最近 **3 次** 有效对比实验（均为真正跑到 task-level、存在完整 agent 轨迹；已排除 build canceled 类 trial）：

| 维度 | Without Skill | With Skill | 结果对比 |
| :--- | :--- | :--- | :--- |
| 通过率 | `0%` | `66.7%` | 近 3 次有效对照里，without skill 都在 workflow verifier 上保留失败项；with skill 有 2 次成功完成初始化与发布链，1 次因跳过 `make python-init` 而失败 |
| Agent 执行耗时 | `179.7s` | `147.7s` | With Skill 的命令发现和收敛更快，平均 Agent 耗时降低约 `17.8%` |
| Tokens | `398.7k` | `362.3k` | Without Skill 的上下文与试错开销约为 With Skill 的 `1.10x` |

## 📁 标准目录结构说明

```text
seed_task/
├── instruction.md
├── task.toml
├── PLAN.json
├── README.md
├── environment/
│   ├── Dockerfile
│   ├── data/
│   ├── repo/
│   └── skills/
├── tests/
└── solution/
```
