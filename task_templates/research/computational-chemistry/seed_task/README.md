# Computational-Chemistry Template

这是面向 `computational-chemistry` 类 skill 的模板。它综合参考 SkillsMP 这一类热门 skill 的共性能力：分子数据整理、SMILES 处理、性质建模、实验工作区管理、候选方案排序、预测产物生成和可审计交付。

## 第一部分：任务设计参考

* **Skill 价值定位**：这类 skill 的核心价值，是把分子数据、建模步骤、候选方案筛选和结果交付串成可复核的工作流。模板任务应让 skill 在项目组织、当前数据口径、实验比较、保留策略和交付说明上降低遗漏率。
* **Verifier 设计重点**：Verifier 应重算输入去重与排除、模型资格、排序依据、预测结果和保留约束，并确认输出来自当前任务内的数据与工作区状态。重点应覆盖输入不可变、输出 schema、当前 run 的产生链路、模型留存状态和交付说明的一致性。

## 第二部分：示例任务

### 📌 任务元数据

- 任务 ID：`computational-chemistry__aqsol-release-refresh`
- 类别：`computational-chemistry`
- 绑定 Skill：`cli-anything-unimol-tools`

- 输入数据参考来源：
  - `environment/data/train.csv`：训练集；设计形态参考 Delaney ESOL 分子溶解度数据  
    【https://deepchemdata.s3-us-west-1.amazonaws.com/datasets/delaney-processed.csv】
  - `environment/data/valid.csv`：验证集；设计形态参考 Delaney ESOL 分子溶解度数据  
    【https://deepchemdata.s3-us-west-1.amazonaws.com/datasets/delaney-processed.csv】
  - `environment/data/test.csv`：测试集；设计形态参考 Delaney ESOL 分子溶解度数据  
    【https://deepchemdata.s3-us-west-1.amazonaws.com/datasets/delaney-processed.csv】
  - `environment/data/holdout.csv`：盲集；设计形态参考 Delaney ESOL 分子溶解度数据  
    【https://deepchemdata.s3-us-west-1.amazonaws.com/datasets/delaney-processed.csv】
  - `environment/workbench/unimol_tools_cli/`：本地工作流接口设计参考 Uni-Mol Tools quickstart  
    【https://unimol-tools.readthedocs.io/en/latest/quickstart.html】

### 📊 验证与测试指标（Oracle & Verifier）

- Oracle：按正式流程独立运行并完成交付，结果可直接 100% 通过验证。

- Verifier 策略：

主测试

| 测试点 | 验证内容 | 对应 skill 内化点 |
| :--- | :--- | :--- |
| 输出文件集合与 schema | 校验 6 个交付文件、字段合同、数值字段和排序 | 结构化研究交付 |
| 排除行重算 | 从原始 split 动态重算无效行与重复行 | 分子数据清洗与台账 |
| 模型资格与最终选择 | 按当前规则重算 eligible / rejected / selected | 当前 run 选择与对比 |
| 预测重算 | 从保留模型工件重算 scored / holdout 预测 | 本地推理与结果复核 |
| 工作区保留约束 | 校验最终保留模型数量和 selected run 留存状态 | 存储管理与结果留存 |
| 方法说明 | 校验说明文件覆盖排除、选择、保留和输出组织 | 研究说明与交付口径 |

防作弊测试

| 测试点 | 验证内容 |
| :--- | :--- |
| 输入 hash | 阻止修改任务内数据、规则和基线快照 |
| 审计链路 | 要求当前会话在工作区里产生 train、rank、predict 事件 |
| 工件复算 | 从模型工件重算预测与指标，拦截硬编码结果 |

### ⚡ Skill 相关性评估

结论：强相关。这个任务里，Skill 的核心价值是把本地项目切换、当前 family 训练、模型排序、存储复核、保留处理和预测导出压成一条稳定工作流，从而让 release 包始终落在同一套 workspace 控制面上。当前 verifier 也直接检查这条链路是否成立，因此只做表面产物拼接的解法很难通过。

基于最近 **3** 次有效对比实验（均为完整 task-level 运行，已排除启动失败类 trial）：

| 维度 | Without Skill | With Skill | 结果对比 |
| :--- | :--- | :--- | :--- |
| 通过率 | `0%` | `100%` | 近 3 次有效对照里，without Skill 常见失败点包括：把存储复核放在错误时点、输出与审计结构偏离 workspace 契约、以及排除行原因标签不稳定。 |
| Agent 执行耗时 | `659.9s` | `354.1s` | With Skill 的诊断与收敛更快，平均 Agent 耗时降低约 `46%`。 |
| Tokens | `1.12M` | `0.61M` | Without Skill 的上下文与试错开销约为 With Skill 的 `1.83x`。 |

## 📁 标准目录结构说明

```text
seed_task/
├── instruction.md
├── task.toml
├── PLAN.json
├── environment/
│   ├── Dockerfile
│   ├── data/
│   ├── skills/
│   └── workbench/
├── tests/
├── solution/
└── README.md
```
