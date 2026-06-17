# Lab Tools Template

这是面向 `lab-tools` 类 skill 的模板。它综合参考 SkillsMP lab-tools 类热门 skill 的共性能力：围绕公开实验或筛选数据包、可复跑 notebook 入口、结构化检查点和书面 handoff，产出可直接复核的分析交付。

## 第一部分：任务设计参考

* **Skill 价值定位**：`lab-tools` 热门 skill 的共性价值，通常在于把公开数据包上的实验、检查、复跑和书面 handoff 组织成一条低歧义工作流。它们不只产出一个最终文件，还会把中间证据、比较视角和复核入口一起交出来，方便后续人接手与追溯。
* **Verifier 设计重点**：verifier 应同时校验最终结论和中间推理痕迹，避免任务被“脚本包一层 notebook”轻易绕过。重点通常包括：结果可重算、关键中间表与审计文件可对账、重跑可再生、输入或合同变动会带来相应输出变化。

## 第二部分：示例任务

### 📌 任务元数据

- 任务 ID：`lab-tools__egfr_bioactivity_review_notebook`
- 类别：`lab-tools`
- 绑定 Skill：`jupyter-notebook`
- 输入数据参考来源：
  - `environment/data/egfr_activity_snapshot.json`：任务内 EGFR 活性记录快照；设计形态参考 ChEMBL activity endpoint  
    【https://www.ebi.ac.uk/chembl/api/data/activity.json?target_chembl_id=CHEMBL203&limit=300】
  - `environment/data/egfr_assay_snapshot.json`：任务内 assay 元数据快照；设计形态参考 ChEMBL assay endpoint  
    【https://www.ebi.ac.uk/chembl/api/data/assay.json】
  - `environment/data/egfr_target_snapshot.json`：任务内 target 元数据快照；数据直接来源于 ChEMBL target endpoint  
    【https://www.ebi.ac.uk/chembl/api/data/target/CHEMBL203.json】
  - `environment/data/egfr_molecule_snapshot.json`：任务内 molecule 元数据快照；设计形态参考 ChEMBL molecule endpoint  
    【https://www.ebi.ac.uk/chembl/api/data/molecule.json】
  - `environment/data/legacy_shortlist.csv`：任务内历史导出；为任务内对照输入，无单独公开链接
  - `environment/data/screening_contract.json`：任务内筛选合同；为任务原创业务输入，无单独公开链接

### 📊 验证与测试指标（Oracle & Verifier）

- Oracle：按正式流程独立运行并完成交付，结果可直接 100% 通过验证。
- Verifier策略：

主测试
| 测试点 | 验证内容 | 对应skill内化点 |
| :--- | :--- | :--- |
| Baseline 结果对账 | `candidate_panel.csv`、`qc_summary.json` 与 oracle 重算完全一致 | 从公开数据包中稳定重建核心分析结果 |
| 中间分析产物对账 | `scenario_comparison.csv`、`candidate_trace.json`、`filter_audit.csv` 与 oracle 重算一致 | 把实验比较、候选来源和过滤路径显式化 |
| Notebook 工作流校验 | notebook 可执行、含计划/结果/后续节点、并以分步代码单元串起 profile、audit、scenario sweep、export、review | 使用 notebook 作为主要分析界面，而不是只交最终文件 |
| 复跑再生 | 删除导出物后重跑 notebook，全部交付物会再生 | 可复跑 handoff |

防作弊测试
| 测试点 | 验证内容 |
| :--- | :--- |
| 历史导出干扰 | 最终 panel 不能退化成 `legacy_shortlist.csv` |
| 数据变异敏感性 | 改动 activity snapshot 后，panel、QC 与 scenario 结果要跟着变化 |
| 合同变异敏感性 | 改动 `screening_contract.json` 后，scenario comparison 与 baseline panel 要跟着变化 |
| 输入与 skill 完整性 | 数据包与绑定 skill 文件哈希不能变化 |

### ⚡ Skill 相关性评估

结论：强相关。这个任务把 notebook 类 skill 的常见高价值动作拆成了可量化检查点：计划、分步分析、scenario sweep、candidate provenance、filter audit 和复跑验证。最终 verifier 不只看答案，还看 solver 是否把 notebook 当成实验与交付的主工作台。

基于最近 **3** 次有效对比实验（均为真正跑到 task-level、存在完整 agent 轨迹；已排除启动失败类 trial）：

| 维度 | Without Skill | With Skill | 结果对比 |
| :--- | :--- | :--- | :--- |
| 通过率 | `0%` | `100%` | 近 3 次有效对照里，without Skill 都留下了至少一项 verifier 失败；失败主要落在 candidate trace、filter audit 说明和合同变异重跑鲁棒性上。 |
| Agent 执行耗时 | `516.6s` | `503.6s` | With Skill 在最近 3 次有效对照里平均 Agent 执行耗时略低，约快 `2.5%`，同时更稳定地完成 notebook、scenario sweep 和审计交付。 |
| Tokens | `930,692` | `1,494,635` | With Skill 在这个题上投入了更多上下文与导出证据，用更完整的 notebook handoff 换取稳定通过；without Skill 的 token 更少，但更容易提前收敛到不完整解。 |

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
