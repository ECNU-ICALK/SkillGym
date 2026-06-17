# SQL Databases Template

这是面向 `sql-databases` 类 skill 的模板。模板围绕本地 PostgreSQL 分析、schema drift 统一、索引设计、可复跑 SQL 交付物和合同驱动的排行榜构建，提供一个可运行、可验证、且不依赖外部账号的高难任务。

## 第一部分：任务设计参考

* **Skill 价值定位**：`sql-databases` 类 skill 的核心价值，在于帮助 Agent 先识别 schema、统一多源字段、建立可复用 SQL 层，再完成聚合、排序、索引和结果交付。题面不应直接泄露工作流，而应把“如何稳定走通数据库链路”的压力留给 skill 与 solver。
* **Verifier 设计重点**：Verifier 需要优先验证 solver 是否真的经过 PostgreSQL 链路完成 schema 识别、过滤、聚合、排序和结果回写，并验证交付物之间的一致性。对 `sql-databases` 类任务，还应明确拦截“只生成结果文件、不保留可执行 SQL”的作弊路径。

## 第二部分：示例任务

### 任务元数据
- 任务 ID：`sql-databases__airport-zone-rolling-mart`
- 类别：`sql-databases`
- 绑定 Skill：`postgres-patterns`
- 主输出：`/root/output/airport_zone_snapshot_leaderboard.tsv`
- 任务目标：构建机场相关 Manhattan zone 的滚动需求 mart，输出日级面板、滚动快照排行榜、可复跑 SQL query pack 和简短 benchmark 报告。
- 输入数据参考来源：
  - `environment/data/dispatch_batch_a.csv`：任务内 Batch A 行程数据；字段形态参考 NYC TLC Yellow Taxi Trip Records  
    【https://d37ci6vzurychx.cloudfront.net/trip-data/yellow_tripdata_2023-01.parquet】
  - `environment/data/dispatch_batch_b.csv`：任务内 Batch B 行程数据；字段形态参考 NYC TLC Yellow Taxi Trip Records  
    【https://d37ci6vzurychx.cloudfront.net/trip-data/yellow_tripdata_2023-01.parquet】
  - `environment/data/dispatch_batch_c.csv`：任务内 Batch C 行程数据；字段形态参考 NYC TLC Yellow Taxi Trip Records  
    【https://d37ci6vzurychx.cloudfront.net/trip-data/yellow_tripdata_2023-02.parquet】
  - `environment/data/dispatch_batch_d.csv`：任务内 Batch D 行程数据；字段形态参考 NYC TLC Yellow Taxi Trip Records  
    【https://d37ci6vzurychx.cloudfront.net/trip-data/yellow_tripdata_2023-02.parquet】
  - `environment/data/taxi_zone_lookup.csv`：任务内区域维表；直接来源于 NYC TLC taxi zone lookup  
    【https://d37ci6vzurychx.cloudfront.net/misc/taxi_zone_lookup.csv】
  - `environment/data/reference/trip_record_user_guide.pdf`：任务内字段说明参考；数据直接来源于 NYC TLC  
    【https://www.nyc.gov/assets/tlc/downloads/pdf/trip_record_user_guide.pdf】
  - `environment/data/reference/data_dictionary_trip_records_yellow.pdf`：任务内 Yellow Taxi 字段字典；数据直接来源于 NYC TLC  
    【https://www.nyc.gov/assets/tlc/downloads/pdf/data_dictionary_trip_records_yellow.pdf】

### 验证与测试指标（Oracle & Verifier）
- Oracle：按正式流程独立运行并完成交付，结果可直接 100% 通过验证。
- Verifier 策略：

主测试
| 测试点 | 验证内容 | 对应 skill 内化点 |
| :--- | :--- | :--- |
| 输出契约 | 校验四份交付物存在、可解析，并满足字段合同与列顺序要求 | 先理解正式交付物，再组织结构化输出 |
| PostgreSQL 分析结果 | 依据输入批次和合同独立重算 `airport_zone_daily_mart.csv` 与 `airport_zone_snapshot_leaderboard.tsv` | schema 探查、查询组织、聚合与排序 |
| query pack 可执行性 | 执行 `query_pack.sql`，并核对其重建出的 `analysis.*` 对象与结果文件一致 | 保留可复用 SQL，而不是一次性脚本 |
| benchmark 报告追溯性 | 校验 `benchmark_report.md` 能回链到最终排行榜结果，并覆盖所有上榜 zone | 结果解释与业务交付 |
| 索引护栏 | 验证关键索引存在，且报告中解释索引策略 | 索引与性能意识 |

防作弊测试
| 测试点 | 验证内容 |
| :--- | :--- |
| 合同变更重跑 | 修改 `analysis_contract.json` 后 rerun，排行榜必须变化 |
| 静态答案拦截 | 禁止硬编码答案、跳过 PostgreSQL 链路、或只写死输出文件 |
| 重复运行稳定性 | 相同输入重复执行时输出必须稳定一致 |

### Skill 相关性评估

最终采用的对照样本，只统计 **fresh current-template** 运行，并要求 with/without 唯一差异是 `environment/skills` 是否存在。上一版曾误把 `currentfix13/14` 的“双边都能过”切片当成可定稿结果；在用户澄清“`without skill` 通过率要压到 0”后，这组切片已被明确废弃。

纠正后的验收目标现已满足。

当前接受的实验切片为：

- `sql-databases-currentfix21-with-20260509`
- `sql-databases-currentfix22-with-20260509`
- `sql-databases-currentfix23-with-20260509`
- `sql-databases-currentfix21-without-20260509`
- `sql-databases-currentfix22-without-20260509`
- `sql-databases-currentfix23-without-20260509`

本轮有效隔离条件：

- 仅统计真正跑到 task-level、存在完整 agent 轨迹、且 verifier 产出 reward 的 fresh current-template trial。
- 只在同一模板版本上对比 `environment/skills` 是否存在这一处差异。
- 忽略纯基础设施异常，例如 `RemoteProtocolError`。
- `currentfix21/22/23` 运行前，task runtime 副本都从同一 `seed_task/` 新鲜复制；`without` 仅移除 `environment/skills/`。

结果摘要：

- `with skill`：`3/3 = 100%` 通过
- `without skill`：`0/3 = 0%` 通过
- `without` 三次失败都是真实 task-level 失败，不是基础设施错误：
  - `currentfix21 without`：失败于 `test_index_guardrails_exist_and_are_reported`
  - `currentfix22 without`：失败于 `test_snapshot_leaderboard_matches_oracle` 与 `test_index_guardrails_exist_and_are_reported`
  - `currentfix23 without`：失败于 `test_snapshot_leaderboard_matches_oracle`
- `with` 的平均执行耗时更短，且总 token 显著更低：
  - 平均耗时：`10m07s` vs `11m51s`，约降低 `14.7%`
  - 平均总 token：`508,484` vs `875,889`，约降低 `41.9%`

| 维度 | Without Skill | With Skill | 结果对比 |
| :--- | :--- | :--- | :--- |
| 通过率 | `0/3 = 0%` | `3/3 = 100%` | with skill `+100` pct-pts |
| Agent 执行耗时 | 平均 `11m51s` | 平均 `10m07s` | with skill 平均快 `1m44s` |
| Tokens | 平均 `875,889` | 平均 `508,484` | with skill 平均少 `367,406` tokens |

## 第三部分：实验记录

- 原未完成实验记录位于 `e2b_jobs/sql-databases-oracle-withalias-20260508/`，其日志显示停在 E2B 模板创建阶段，未产出 `result.json`。
- 续跑作业 `e2b_jobs/sql-databases-oracle-withalias-retry-20260508/` 已在 2026-05-08 完成，reward 为 `1.0`。
- 当前模板目录 `seed_task/` 的 oracle 验证作业 `e2b_jobs/sql-databases-template-current-oracle-20260508/` 已在 2026-05-08 完成，reward 为 `1.0`。
- `currentfix13` 与 `currentfix14` 两对 passing pairs 已被确认不满足最终验收目标，因为 `without skill` 仍可通过。
- 2026-05-09 继续收紧模板后，task-specific schema/rolling/index playbook 被移入 `environment/skills/postgres-patterns/references/`，工作区提示物降级为高层占位说明，减少了无 skill 运行时的显式工作流泄露。
- `sql-databases-currentfix21-with-20260509`：通过，reward `1.0`
- `sql-databases-currentfix22-with-20260509`：通过，reward `1.0`
- `sql-databases-currentfix23-with-20260509`：通过，reward `1.0`
- `sql-databases-currentfix21-without-20260509`：失败，reward `0.0`，原因是索引护栏未满足
- `sql-databases-currentfix22-without-20260509`：失败，reward `0.0`，原因是排行榜行域漂移并同时未满足索引护栏
- `sql-databases-currentfix23-without-20260509`：失败，reward `0.0`，原因是 `2023-02-07 / morning_departures / EWR` 分区把 zone `161` 排到 zone `230` 之前，导致排行榜与 oracle 不一致

## 标准目录结构说明

```text
seed_task/
├── instruction.md
├── task.toml
├── PLAN.json
├── README.md
├── environment/
│   ├── Dockerfile
│   ├── data/
│   ├── skills/
│   └── workspace/
├── tests/
│   ├── test.sh
│   ├── reference_metrics.py
│   └── test_outputs.py
└── solution/
    ├── fixed/
    └── solve.sh
```
