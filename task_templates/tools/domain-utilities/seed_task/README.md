# Domain-Utilities Template

这是面向 `domain-utilities` 类 skill 的模板。它综合参考 SkillsMP `domain-utilities` 类热门 skill 的共性能力：领域约束识别、候选项批量核对、状态归一、排序取舍和备选输出。

## 第一部分：任务设计参考

* **Skill 价值定位**：`domain-utilities` 类热门 skill 的关键价值，在于帮助 Agent 先理解具体业务语境，再把候选项的批量核对、约束过滤和排序决策串成稳定流程。对 `domain-name-brainstormer` 这类 skill 来说，重点是减少拍脑袋式命名和零散检查，把动作收敛到“候选生成或读取、跨后缀核对、保留备选、给出推荐”的可复算路径。
* **Verifier 设计重点**：Verifier 应优先检查 solver 是否完成了全量核对、是否遵守约束和排序规则、以及最终推荐与备选之间是否自洽。除了输出内容，还要覆盖输入不可改写、结果可重跑、候选来源受限和交付范围收敛。

## 第二部分：示例任务

### 📌 任务元数据
- 任务 ID：`domain-utilities__developer-workflow-domain-shortlist`
- 类别：`domain-utilities`
- 绑定 Skill：`domain-name-brainstormer`
- 输入数据参考来源：
  - `environment/data/market_examples.csv`：任务内相关品牌与域名样本；设计形态参考公开产品官网  
    `https://linear.app/`
  - `environment/data/market_examples.csv`：任务内相关品牌与域名样本；设计形态参考公开产品官网  
    `https://plane.so/`
  - `environment/data/market_examples.csv`：任务内相关品牌与域名样本；设计形态参考公开产品官网  
    `https://height.app/`
  - `environment/data/market_examples.csv`：任务内相关品牌与域名样本；设计形态参考公开产品官网  
    `https://clickup.com/`
  - `environment/data/market_examples.csv`：任务内相关品牌与域名样本；设计形态参考公开产品官网  
    `https://asana.com/`
  - `environment/data/market_examples.csv`：任务内相关品牌与域名样本；设计形态参考公开产品官网  
    `https://www.notion.so/`
  - `environment/data/availability_snapshot.csv`：任务内域名状态快照；状态采样直接来源于  
    `https://rdap.verisign.com/com/v1/domain/<domain>`
  - `environment/data/availability_snapshot.csv`：任务内域名状态快照；状态采样直接来源于  
    `https://rdap.identitydigital.services/rdap/domain/<domain>`
  - `environment/data/availability_snapshot.csv`：任务内域名状态快照；状态采样直接来源于  
    `https://rdap.radix.host/rdap/domain/<domain>`
  - `environment/data/availability_snapshot.csv`：任务内域名状态快照；状态采样直接来源于  
    `https://rdap.centralnic.com/xyz/domain/<domain>`

### 📊 验证与测试指标（Oracle & Verifier）
- Oracle：按正式流程独立运行并完成交付，结果可直接 100% 通过验证。
- Verifier策略：

主测试
| 测试点 | 验证内容 | 对应skill内化点 |
| :--- | :--- | :--- |
| 全量核对 | 校验 `availability_audit.csv` 是否覆盖所有 base name 与允许后缀组合，并与状态快照一致 | 跨多个后缀做系统化核对 |
| 排序与唯一性 | 校验 shortlist、runner-up 和 taken 列表是否遵守分数、tie-break 和 base name 唯一性 | 推荐、备选和替代方案管理 |
| 输出合同 | 校验 JSON、CSV 的结构、字段、数量、排序和取值范围 | 按业务合同交付结构化结果 |
| 重跑稳定性 | 复跑后输出仍与 oracle 一致 | 可重复执行的领域工作流 |

防作弊测试
| 测试点 | 验证内容 |
| :--- | :--- |
| 输入完整性 | brief、候选池、状态快照和策略文件不可修改 |
| 技能可用性 | shipped skill 在 with-skill 运行时可读，并作为只读命名流程参考 |
| 候选来源约束 | 所有 shortlisted 和 runner-up 域名都必须来自任务内 snapshot |

### ⚡ Skill 相关性评估

结论：强相关。这个任务里，Skill 的核心价值在于把“读取 brief、核对全部 base name 与允许后缀、按既定评分合同排序、保留 shortlist 与 runner-up”收敛成可重复流程；without skill 的轨迹则稳定偏向自推评分公式，导致 audit 与最终顺位一起走偏。

基于最近 **3 次** 有效对比实验（均为最终模板、真正跑到 task-level，已排除启动失败类 trial）：

| 维度 | Without Skill | With Skill | 结果对比 |
| :--- | :--- | :--- | :--- |
| 通过率 | `0%` | `100%` | 近 3 次有效对照里，without Skill 都未通过；失败点稳定落在 `availability_audit.csv` 评分重算与 `runner_ups` / shortlist 顺位偏差，而非格式问题 |
| Agent 执行耗时 | `276.7s` | `100.6s` | With Skill 的核对与收敛更快，按 `agent_execution` 口径统计，平均耗时降低约 `63.6%` |
| Tokens | `222.1k` | `165.8k` | Without Skill 的上下文与试错开销约为 With Skill 的 `1.34x` |

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
