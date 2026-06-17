# Finance-Investment Template

这是面向 `finance-investment` 类 skill 的模板。它综合参考 SkillsMP finance-investment 类热门 skill 的共性能力：组合风险度量、回测与偏差控制、财务建模、投资研究、策略评估、风险阈值监控与可审计报告生成。

## 第一部分：任务设计参考

* **Skill 价值定位**：finance-investment 类 skill 的核心价值，是把金融分析中容易混淆的口径标准化，并把多步骤计算沉淀成可复用 workflow。模板任务应让 skill 在收益、风险、回归、压力测试、阈值判断等环节降低试错成本，而不是替 Agent 提供最终答案。
* **Task 目标形态**：任务应要求 Agent 基于真实或冻结的金融数据，产出可审计、可复算、机器可读的投资分析结果。目标形态适合设计成多源数据对齐、指标计算、模型解释、政策阈值判断和结构化报告生成，不适合做静态问答、主观投资建议或单一公式填空。
* **Verifier 设计重点**：Verifier 应重算关键金融结果，验证数据口径、单位转换、时间窗口、统计定义和输出结构，而不是绑定某个实现文件。重点应覆盖输入不可变、数值有限、下行风险方向、基准相对指标、因子回归、回测/压力测试参数和风险阈值 breach 的一致性。

## 第二部分：示例任务

### 📌 任务元数据

- 任务 ID：`finance-investment__arkk-factor-risk-review`
- 类别：`finance-investment`
- 难度：`hard`
- 绑定 Skill：`risk-metrics-calculation`
- 输入数据参考来源：
  - `environment/data/daily_prices.csv`：任务内 ETF 价格数据；价格参考 Yahoo Finance Historical Market Data  
    https://finance.yahoo.com/
  - `environment/data/F-F_Research_Data_5_Factors_2x3_daily.csv`：任务内 Fama-French 5 因子数据；字段与口径参考 Kenneth R. French Data Library  
    https://mba.tuck.dartmouth.edu/pages/faculty/ken.french/data_library.html
  - `environment/data/F-F_Momentum_Factor_daily.csv`：任务内动量因子数据；字段与口径参考 Kenneth R. French Data Library  
    https://mba.tuck.dartmouth.edu/pages/faculty/ken.french/data_library.html
  - `environment/data/portfolio_policy.yaml`：任务内本地风险阈值配置文件，无单独公开数据链接

### 📊 验证与测试指标（Oracle & Verifier）

- Oracle：按正式流程独立运行并完成交付，结果可直接 100% 通过验证。

- Verifier 策略：

主测试

| 测试点 | 验证内容 | 对应 skill 要求掌握的部分 |
| :--- | :--- | :--- |
| 输出契约 | 检查输出 JSON schema、字段类型、有限值约束，以及完整 stress grid 是否齐全 | 机器可读金融报告与可审计输出 |
| 风险指标重算 | 重算 ARKK/QQQ 日收益对齐、累计收益、波动、Sharpe、Sortino、回撤、VaR/CVaR | 组合绩效与下行风险指标 |
| 主动风险重算 | 重算 QQQ-relative active return、tracking error、information ratio、beta、downside beta | 基准相对风险与主动风险分析 |
| 因子回归校验 | 重算 Fama-French 5 因子加 momentum 回归，并检查 RF 对齐、百分比转小数和 HAC t-stat | 因子模型、单位口径和稳健统计 |
| 尾部风险与压力测试 | 校验 moving-block bootstrap 与 deterministic stress harness 的结果与口径 | 可复现尾部风险与压力测试设计 |
| 限额与防作弊收口 | 校验 policy_breaches 与输入文件 hash guardrail | 风险限额监控、输入不可变和反占位输出 |

防作弊测试

| 测试点 | 验证内容 |
| :--- | :--- |
| 输入不可变 | 校验原始价格、因子和政策文件 hash 不变，防止改数据过题。 |
| 风险方向 | 检查 VaR 与 CVaR 必须保持负向下尾定义，避免符号反转。 |
| 因子单位 | 检查 French 因子确实从百分比转成小数，而不是直接拿原值回归。 |
| 下行窗口 | 检查 downside beta 只使用 QQQ 为负收益的日期。 |
| 输出完整性 | 检查 stress grid 完整且所有数值有限，防止占位输出或删减难点。 |

### ⚡ Skill 相关性评估

结论：强相关。这个任务里，Skill 的核心价值是把风险指标口径、因子回归口径和 deterministic stress grid 标准化；without Skill 仍能算出部分常规指标，但在 Sortino、bootstrap 参数、stress grid 完整性和 policy breach 命名上持续掉分。

基于最近 **3** 次有效对比实验（均为真正跑到 task-level、存在完整 agent 轨迹；已排除启动失败类 trial）：

| 维度 | Without Skill | With Skill | 结果对比 |
| :--- | :--- | :--- | :--- |
| 通过率 | `0%` | `100%` | 近 3 次有效对照里，without Skill 均至少在 bootstrap/stress-grid、Sortino 或 policy verifier 上失败；with Skill 三次全通过。 |
| Agent 执行耗时 | `338.0s` | `180.1s` | With Skill 的诊断与收敛更快，平均 Agent 耗时降低约 `47%`。 |
| Tokens | `0.282M` | `0.255M` | Without Skill 的上下文与试错开销约为 With Skill 的 `1.11x`。 |

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
│   └── skills/
├── tests/
└── solution/
```
