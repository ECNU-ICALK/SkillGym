# Database Tools Template

这是面向 database-tools 类 skill 的模板。它综合参考 SkillsMP 数据库工具热门 skill 的共性能力：围绕本地数据库重建、分层迁移、可回放 SQL 交付和稳定导出展开。模板重点放在让求解器把 migration bundle 当作长期可复用交付物，同时避免把它写成一次性脚本。

## 第一部分：任务设计参考
* **Skill 价值定位**：这类 skill 的共性价值，在于把数据库任务从“先跑出一份答案”提升到“留下可重复执行、顺序明确、层次清楚的迁移与导出流程”。对数据库工具模板来说，关键在于后续环境仍能继续完成重建、回放和复查。
* **Verifier 设计重点**：这类任务的 verifier 应同时验证交付文件、数据库内关系、迁移回放能力和重复运行稳定性。除了看最终导出是否对，还要验证 migration 顺序、索引与重建路径是否真的支撑后续使用，避免只在一次运行里凑出结果。

## 第二部分：示例任务
### 📌 任务元数据
- 任务 ID：`database-tools__rapid-transit-schema-release`
- 类别：`database-tools`
- 绑定 Skill：`database-migrations`
- 输入数据参考来源：
  - `environment/data/gtfs/agency.txt`：任务内机构与时区元数据，直接来源于 MBTA GTFS 静态数据包  
    【https://cdn.mbta.com/MBTA_GTFS.zip】
  - `environment/data/gtfs/routes.txt`、`stops.txt`、`trips.txt`、`stop_times.txt`、`calendar.txt`、`calendar_dates.txt`：任务内线路、站点、班次、时刻与服务日历数据，直接来源于 MBTA GTFS 静态数据包  
    【https://cdn.mbta.com/MBTA_GTFS.zip】
  - `environment/data/reference/feed_info.txt`：任务内 feed 版本与时间范围元数据，直接来源于 MBTA GTFS 静态数据包  
    【https://cdn.mbta.com/MBTA_GTFS.zip】
  - `environment/data/reference/gtfs_field_notes.md`：任务内字段说明形态参考 GTFS Schedule Reference  
    【https://gtfs.org/documentation/schedule/reference/】

### 📊 验证与测试指标（Oracle & Verifier）
- Oracle：按正式流程独立运行并完成交付，结果可直接 100% 通过验证。
- Verifier 策略：

主测试

| 测试点 | 验证内容 | 对应 skill 内化点 |
| --- | --- | --- |
| 输出文件合同 | CSV、TSV、SQL、说明文件都存在且列结构正确 | 交付物完整性 |
| 指标结果对账 | panel 与 leaderboard 和独立重算结果一致 | 数据迁移后结果可核对 |
| 迁移回放 | fresh raw load 后仅重放 migration 也能重建下游关系 | 顺序化迁移、可回放 SQL |
| 重复运行稳定 | 同一输入重复执行仍输出一致 | 幂等重建流程 |
| 索引守护 | raw、core、mart 的关键索引都落在数据库里 | 迁移纪律与运行保障 |

防作弊测试

| 测试点 | 验证内容 |
| --- | --- |
| 合同扰动 | 改动 `release_contract.json` 后，导出内容必须变化 |
| 样例硬编码防护 | 结果必须来自已加载数据与 SQL 关系，不能只靠预写答案 |

### ⚡ Skill 相关性评估
结论：强相关。这个任务里，Skill 的核心价值是把 raw/core/mart 三层迁移、索引补齐和 replay 路径当成同一个交付合同来处理。无 skill 解法有时也能做出完整结果，但更容易在迁移守护项上漏掉关键索引，因此完成率明显不如 with skill 稳定。

基于最近 **3 次** 有效对比实验（均为真正跑到 task-level、存在完整 agent 轨迹；已排除 build cancelled 一类 trial）：

| 维度 | Without Skill | With Skill | 结果对比 |
| :--- | :--- | :--- | :--- |
| 通过率 | `33.3%` | `100%` | 近 3 次有效对照里，without Skill 有 2 次停在 `test_index_guardrails_exist`；with Skill 3 次都通过 |
| Agent 执行耗时 | `544.9s` | `660.3s` | With Skill 会投入更多时间补齐 replay 与索引纪律；without Skill 更快结束，但常留下 verifier 失败 |
| Tokens | `0.68M` | `0.89M` | With Skill 为了完成分层迁移与回放检查，平均上下文消耗更高；without Skill 更省，但稳定性更差 |

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
│   ├── workspace/
│   └── skills/
├── tests/
│   ├── reference_metrics.py
│   ├── test_outputs.py
│   └── test.sh
└── solution/
    ├── fixed/
    └── solve.sh
```
