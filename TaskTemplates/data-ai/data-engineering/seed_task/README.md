# Data Engineering Template

这是面向 `data-engineering` 类 skill 的模板。它综合参考 SkillsMP data-engineering 类热门 skill 的共性能力：真实数据装载、Schema drift 识别、SQL 聚合口径校准、分层 ETL 修复、结果回算验证，以及沿真实引擎链路完成 rerun 和回归确认。

## 第一部分：任务设计参考

* **Skill 价值定位**：data-engineering 类热门 skill 的核心价值，是把“能跑出一个文件”提升为“能沿真实数据链路修好装载、清洗、聚合和复算闭环”。模板任务应让 skill 标准化数据输入检查、字段漂移诊断、业务口径核对、SQL/引擎层验证和 rerun 复核，而不是把任务退化成静态脚本拼接或结果硬编码。
* **Verifier 设计重点**：Verifier 应验证 solver 是否真的经过真实运行链路、是否重建了要求的中间与最终产物、是否满足业务口径而不是只贴表面结果。重点应覆盖多输入参与、关键表内容精确性、月度/分区排名逻辑、JSON 输出契约、幂等 rerun、防止跳过真实引擎、防止静态答案和防止删功能规避。

## 第二部分：示例任务

### 📌 任务元数据

- 任务 ID：`data-engineering__clickhouse-tlc-route-metrics`
- 类别：`data-engineering`
- 难度：`hard`
- 绑定 Skill：`clickhouse-io`
- 输入数据参考来源：
  - `environment/workspace/data/yellow_tripdata_2023-01.parquet`：任务内 January 2023 行程数据子集；设计形态参考 NYC TLC Yellow Taxi Trip Records  
    【https://d37ci6vzurychx.cloudfront.net/trip-data/yellow_tripdata_2023-01.parquet】
  - `environment/workspace/data/yellow_tripdata_2023-02.parquet`：任务内 February 2023 行程数据子集；设计形态参考 NYC TLC Yellow Taxi Trip Records  
    【https://d37ci6vzurychx.cloudfront.net/trip-data/yellow_tripdata_2023-02.parquet】
  - `environment/workspace/data/taxi_zone_lookup.csv`：任务内 zone lookup 维表；数据直接来源于 NYC TLC zone lookup  
    【https://d37ci6vzurychx.cloudfront.net/misc/taxi_zone_lookup.csv】
  - `environment/workspace/data/trip_record_user_guide.pdf`：任务内字段说明与提交口径参考；数据直接来源于 NYC TLC  
    【https://www.nyc.gov/assets/tlc/downloads/pdf/trip_record_user_guide.pdf】
  - `environment/workspace/data/data_dictionary_trip_records_yellow.pdf`：任务内 Yellow Taxi 字段字典；数据直接来源于 NYC TLC  
    【https://www.nyc.gov/assets/tlc/downloads/pdf/data_dictionary_trip_records_yellow.pdf】

### 📊 验证与测试指标（Oracle & Verifier）

- Oracle：按正式流程独立运行并完成交付，结果可直接 100% 通过验证。
- Verifier 策略：

主测试
| 测试点 | 验证内容 | 对应 skill 内化点 |
| :--- | :--- | :--- |
| 运行入口 | 校验 `./run_pipeline.sh` 能完整重建链路并产出 `summary.json` | 从真实执行入口排查，而不是绕开 pipeline |
| 输出契约 | 校验 `summary.json` 字段、月份顺序、原始行数、有效行数和结果行数 | 结构化交付合同与回算意识 |
| 日级聚合表 | 精确比对 `analytics.daily_borough_metrics` 内容 | 清洗口径、维表映射和 ClickHouse 聚合正确性 |
| 月级路线榜 | 精确比对 `analytics.top_zone_routes` 内容，要求每月各取前 20 | 窗口函数、分区排名和业务排序口径 |
| 幂等重跑 | 删除输出后 rerun，校验两个月都入库且结果表仍可查询 | rerun 复核、真实装载和非缓存输出 |

防作弊测试
| 测试点 | 验证内容 |
| :--- | :--- |
| 真实链路约束 | 禁止把 ClickHouse 替换成 pandas、SQLite 或静态导出结果 |
| 缓存与单月规避 | rerun 后必须从当前数据重建，且 `analytics.trips_raw` 必须同时包含 `2023-01` 和 `2023-02` |

### ⚡ Skill 相关性评估

结论：强相关。这个任务里，Skill 的核心价值是把 ClickHouse 装载诊断、字段漂移识别、清洗口径约束和月度排名验证标准化，从而明显降低“表面修通但业务口径仍错”的概率；without Skill 更容易停在真实修了一部分链路、但关键清洗或验证动作仍走偏的错误路径上。

基于最近 **3** 次有效对比实验（均为真正跑到 task-level、存在完整 agent 轨迹；已排除启动失败类 trial）：

| 维度 | Without Skill | With Skill | 结果对比 |
| :--- | :--- | :--- | :--- |
| 通过率 | `33.3%` | `66.7%` | 近 3 次有效对照里，without Skill 有 2 次在清洗口径上过严，误删了本应保留的 zone lookup 映射行；with Skill 更稳定识别字段漂移、`N/A` 映射保留和按月分区排名要求。 |
| Agent 执行耗时 | `515.5s` | `543.2s` | With Skill 的平均执行耗时略高约 `5.4%`，但换来了更高的任务通过率。 |
| Tokens | `1.54M` | `1.72M` | With Skill 的平均 token 开销约为 Without Skill 的 `1.12x`，主要用于更显式的 ClickHouse 装载诊断、口径核对和 rerun 校验。 |

## 📁 标准目录结构说明

```text
seed_task/
├── instruction.md
├── task.toml
├── PLAN.json
├── README.md
├── environment/
│   ├── Dockerfile
│   ├── workspace/
│   └── skills/
│       ├── clickhouse-io/
│       └── clickhouse-io-codex/
├── tests/
│   ├── test.sh
│   └── test_outputs.py
└── solution/
    └── solve.sh
```
