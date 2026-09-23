# Divination-Mysticism Template

这是面向 `divination-mysticism` 类 skill 的模板。它综合参考 SkillsMP `divination-mysticism` 类热门 skill 的共性能力：围绕公开历法资料、容器内本地工具链和结构化约束，把带有文化语境的候选事项整理成可交付、可复核的排期结果。

## 第一部分：任务设计参考

* **Skill 价值定位**：这一类 skill 的价值，通常体现在帮助 solver 把抽象的节俗、历法或象征性规则，落成一条能执行的资料读取、日期判定和结果整理流程。对 calendar / almanac 子类来说，skill 的重点是降低数据定位、规则套用和证据留存的成本。
* **Verifier 设计重点**：Verifier 应优先验证 solver 是否完成了关键动作链，而不只看最后文件名。重点应覆盖历法数据读取、候选日期重算、约束收敛、证据文件存在性，以及拦截手写日期、绕过本地工具链、修改输入或借用题外结论等捷径。

## 第二部分：示例任务

### 📌 任务元数据

- 任务 ID：`divination-mysticism__observance-slate-2026`
- 类别：`divination-mysticism`
- 绑定 Skill：`ccal`
- 输入数据参考来源：
  - `environment/skills/ccal/SKILL.md`：绑定 skill 原文  
    <https://raw.githubusercontent.com/x-cmd/x-cmd/main/mod/ccal/SKILL.md>
  - `environment/x-cmd-root-data/ccal/data/ccal-data-v0.0.6.tar.xz`：容器内历法 archive  
    <https://codeberg.org/x-cmd/ccal-data/releases/download/v0.0.6/ccal-data.tar.xz>
  - `environment/data/reference/hko_conversion.htm`：公开换算参考入口  
    <https://www.hko.gov.hk/en/gts/time/conversion.htm>
  - `environment/data/reference/hko_conversion_text.htm`：公开文字版换算入口  
    <https://www.hko.gov.hk/en/gts/time/conversion1_text.htm>
  - `environment/data/reference/hko_2026e.pdf`：2026 年公开历书参考  
    <https://www.hko.gov.hk/en/gts/time/calendar/pdf/files/2026e.pdf>

### 📊 验证与测试指标（Oracle & Verifier）

- Oracle：按正式流程独立运行并完成交付，结果可直接 100% 通过验证。
- Verifier策略：

主测试

| 测试点 | 验证内容 | 对应skill内化点 |
| :--- | :--- | :--- |
| 输出合同 | 检查 4 个正式产物与 `evidence/` 目录是否齐全且结构可解析 | 先理解交付物，再组织结果 |
| 日期重算 | 用同一份 archive 重算全部候选的 2026 日期与 weekday | 读取历法数据并完成换算 |
| 选型重算 | 按 ops 和 policy 重新计算唯一有效排期组合 | 把日期解析结果继续推进到业务决策 |
| 证据一致性 | 检查 selected、resolution、audit、report 和 evidence 之间是否一致 | 保留支撑材料并形成交付闭环 |

防作弊测试

| 测试点 | 验证内容 |
| :--- | :--- |
| canonical workflow | `/var/log/ccal/access.log` 必须证明 solver 走过 `x zuz cat` archive 读取链路，并覆盖足够多的 2026 月份数据 |
| 环境保护 | `/root/environment/data`、`/root/.x-cmd.root/data` 和 `/usr/local/bin/x` 的文件不可修改 |

### ⚡ Skill 相关性评估

结论：强相关。这个任务里，Skill 的核心价值是把 `ccal` archive 的定位方式、`x zuz cat` 的月度读取链路和证据整理动作标准化。对照实验里，without_skill 虽然多次能做出表面上看起来完整的排期文件，但持续绕开 canonical archive workflow，最终稳定落在 guardrail 失败上。

基于最近 **3** 次有效对照实验（均跑到 task-level，并拿到了完整 verifier 结果）：

| 维度 | Without Skill | With Skill | 结果对比 |
| :--- | :--- | :--- | :--- |
| 通过率 | `0%` | `100%` | 3 次有效对照里，without Skill 都未通过；主要原因是没有走 `x zuz cat` archive workflow，`/var/log/ccal/access.log` 为空，至少保留了 action-level guardrail 失败。 |
| Agent 执行耗时 | `462.1s` | `490.6s` | Without Skill 平均耗时略短约 `6%`，但它收敛到的是无效 shortcut；With Skill 则稳定完成完整 workflow 并通过全部测试。 |
| Tokens | `1.09M` | `1.05M` | Without Skill 的输入+输出 token 约为 With Skill 的 `1.03x`，上下文开销没有换来可结算通过。 |

## 📁 标准目录结构说明

```text
seed_task/
├── instruction.md
├── task.toml
├── PLAN.json
├── README.md
├── environment/
│   ├── Dockerfile
│   ├── bin/
│   ├── data/
│   ├── skills/
│   └── x-cmd-root-data/
├── tests/
│   ├── test.sh
│   ├── test_helpers.py
│   ├── test_outputs.py
│   └── test_guardrails.py
└── solution/
    ├── fixed/
    └── solve.sh
```
