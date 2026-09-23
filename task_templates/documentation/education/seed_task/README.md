# Education Template

这是面向 `education` 类 skill 的模板。它综合参考 SkillsMP education 类热门
skill 的共性能力：围绕公开教育数据、课堂交付合同和可复跑分析入口，产出可
直接用于带教的 notebook、汇总表和课程结论文件。

## 第一部分：任务设计参考

* **Skill 价值定位**：education 类 skill 的常见价值，是把课程目标、学习者
  受众、公开数据和分析边界收束成一套可直接交付的教学材料。模板任务适合让
  agent 在数据处理、讲解组织、练习设置和结论收口之间做完整交付。
  数据证据的 lesson artifact、可复跑分析包等交付。目标应强调输入边界固定、
  输出件明确、可以顺序执行，并带有教学使用场景。
* **Verifier 设计重点**：Verifier 应覆盖正式交付件、从头执行能力、数据
  取值与结论一致性、教程结构完整性，以及输入包不可改动。验证
  重点落在完整教学工作流、证据绑定和复跑能力，同时对表层措辞保持较宽松。

## 第二部分：示例任务

### 📌 任务元数据

- 任务 ID：`education__global_education_cohort_notebook`
- 类别：`education`
- 绑定 Skill：`jupyter-notebook`
- 输入数据参考来源：
  - `environment/source_bundle/years_of_schooling.csv`：任务内受教育年限指标快照  
    【https://ourworldindata.org/grapher/years-of-schooling.csv?v=1&csvType=full&useColumnShortNames=false&level=all&metric_type=average_years_schooling&sex=both】
  - `environment/source_bundle/school_enrolment.csv`：任务内高中阶段毛入学率指标快照  
    【https://ourworldindata.org/grapher/school-enrolment.csv?v=1&csvType=full&useColumnShortNames=false&enrolment_type=gross_enrolment&level=upper_secondary&sex=both】
  - `environment/source_bundle/education_spending.csv`：任务内教育支出占 GDP 比重指标快照  
    【https://ourworldindata.org/grapher/education-spending.csv?v=1&csvType=full&useColumnShortNames=false&level=all&spending_type=gdp_share】

### 📊 验证与测试指标（Oracle & Verifier）

- Oracle：按正式流程独立运行并完成交付，结果可直接 100% 通过验证。
  JSON 和教学 notebook，再独立校验导出值、证据绑定、共同年份和 notebook
  可执行性。
- Verifier策略：

主测试

| 测试点 | 验证内容 | 对应skill内化点 |
| :--- | :--- | :--- |
| 必需交付件 | `ipynb`、`csv`、`json` 都存在且可解析 | notebook 交付收敛 |
| 指标表合同 | cohort 过滤、指标口径、年份窗口、排序、单位统一 | 数据清洗与对齐 |
| 结论证据一致性 | takeaway、evidence、latest common year 与导出表一致 | 教学结论落到数据 |
| notebook 可执行性 | 从上到下执行成功，包含开场 handoff、图表、练习和收尾板块 | 教程型 notebook 组织 |
| 重跑与泛化 | 删除导出件后 notebook 能再产出；改动源数据后结果会变化 | 可复跑工作流 |

防作弊测试

| 测试点 | 验证内容 |
| :--- | :--- |
| 输入不可变 | `source_bundle` 哈希不变 |
| 输出白名单 | `/root/output` 顶层只保留规定产物 |
| 源驱动校验 | 变异源数据后输出必须跟着变化 |

### ⚡ Skill 相关性评估

结论：中等相关。这个任务里，Skill 的主要价值在于把教程型 notebook 的开场、
分节、图表解释和收尾 handoff 组织得更稳；without_skill 常能完成数据处理与
导出，但更容易漏掉给教学助手使用的流程预览，偶发情况下 with_skill 也会在
板块衔接上失手。

基于最近 **4 次** 有效对比实验：

| 维度 | Without Skill | With Skill | 结果对比 |
| :--- | :--- | :--- | :--- |
| 通过率 | `0%` | `50%` | 近 4 次有效对照里，without Skill 4 次都保留了至少 1 个教学工作流级失败；with Skill 有 2 次完整通过，另外 2 次分别卡在开场流程预览和图表讲解衔接 |
| Agent 执行耗时 | `452.0s` | `376.8s` | With Skill 的平均 Agent 耗时更短，较 without Skill 下降约 `16.6%` |
| Tokens | `764,513` | `890,920` | With Skill 为了组织教学 handoff，平均 token 开销约为 without Skill 的 `1.17x` |

## 📁 标准目录结构说明

```text
seed_task/
├── instruction.md
├── task.toml
├── PLAN.json
├── README.md
├── environment/
│   ├── Dockerfile
│   ├── source_bundle/
│   └── skills/
├── tests/
└── solution/
```
