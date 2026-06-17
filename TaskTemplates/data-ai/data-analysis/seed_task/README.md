# Data Analysis Template

这是面向 `data-analysis` 类 skill 的模板。它综合参考 SkillsMP data-analysis 类热门 skill 的共性能力：读取本地数据快照、梳理 SQL 提取口径、完成 pandas 聚合与统计比较，并把结论沉淀为可复跑交付物。

## 第一部分：任务设计参考

* **Skill 价值定位**：data-analysis 类热门 skill 的共同价值，在于帮助 Agent 先识别数据结构、口径和异常，再把 SQL 提取、pandas 整理、统计比较和结论解释连成一条完整路径。高质量模板应让 skill 在“如何从源数据稳定走到结论”上提供帮助，避免任务退化成静态答案生成。
* **Verifier 设计重点**：Verifier 应优先验证 solver 是否沿数据链路完成清洗、聚合、统计和结果回写，并检查多份交付物之间的一致性。对于绑定了工作流型 skill 的任务，还应验证 solver 是否保留了可复用的 SQL 提取逻辑与解释性说明。

## 第二部分：示例任务

### 📌 任务元数据
- 任务 ID：`data-analysis__airport-partner-zone-opportunity`
- 类别：`data-analysis`
- 绑定 Skill：`data-analyst`
- 输入数据参考来源：
  - `environment/data/trips/airport_partner_ops.db`：任务内 SQLite staging 数据；设计形态参考 NYC TLC Yellow Taxi Trip Records 与 zone lookup  
    【https://d37ci6vzurychx.cloudfront.net/trip-data/yellow_tripdata_2023-01.parquet】
    【https://d37ci6vzurychx.cloudfront.net/trip-data/yellow_tripdata_2023-02.parquet】
    【https://d37ci6vzurychx.cloudfront.net/misc/taxi_zone_lookup.csv】
  - `environment/data/reference/trip_record_user_guide.pdf`：任务内字段说明参考；数据直接来源于 NYC TLC  
    【https://www.nyc.gov/assets/tlc/downloads/pdf/trip_record_user_guide.pdf】
  - `environment/data/reference/data_dictionary_trip_records_yellow.pdf`：任务内 Yellow Taxi 字段字典；数据直接来源于 NYC TLC  
    【https://www.nyc.gov/assets/tlc/downloads/pdf/data_dictionary_trip_records_yellow.pdf】
  - `environment/data/weather/airport_daily_weather.json`：任务内机场日级天气数据；数据直接来源于 NOAA Daily Summaries API  
    【https://www.ncei.noaa.gov/access/services/data/v1?dataset=daily-summaries&stations=USW00094789,USW00014732,USW00014734&startDate=2023-01-01&endDate=2023-02-07&dataTypes=AWND,PRCP,SNOW,SNWD,TMAX,TMIN&includeAttributes=false&includeStationName=true&includeStationLocation=1&units=metric&format=json】

### 📊 验证与测试指标（Oracle & Verifier）
- Oracle：按正式流程独立运行并完成交付，结果可直接 100% 通过验证。
- Verifier 策略：

主测试
| 测试点 | 验证内容 | 对应 skill 内化点 |
| :--- | :--- | :--- |
| 运行入口 | 验证指定的执行脚本可以完整生成所有要求产生的结果文件 | 重整分析工作流入口 |
| 数据库读写 | 验证程序能够读取数据库源头信息及条件要求进行获取过滤 | 连接检索功能开发 |
| 阶段数据汇总 | 比对目标产出的统计表格内分组及关键指标是否准确 | 聚合计算及结果校准 |
| 混合条件检验 | 验证在引入更多参考维度后产生对比结构的精确度及变化趋势说明 | 多维度数据比较 |
| 最终输出表现 | 检查最终名录表格里的结论对象是否遵守排序说明与指标要求条件 | 排序筛选与指标规范运用 |
| 结果说明交付 | 验证书面的解释文档或留存文件能跟之前测得的具体数字相一致 | 整理输出产物和过程说明 |

防作弊测试
| 测试点 | 验证内容 |
| :--- | :--- |
| 对应变更测试 | 修改源端参考业务条件后重复运行流程时，最终结果表格需产生变化 |
| 静态值检验 | 验证内容不包含写死的具体最终文本或者通过其他渠道获得的成品内容 |

### ⚡ Skill 相关性评估

结论：中等偏强相关。这个任务里，Skill 的核心价值仍然落在 SQLite 提取、schema drift 识别、pandas 整理、统计比较和 query pack 留存的联动上；不过从对照结果看，skill 更稳定地帮助代理走到完整分析链路，但并不能把所有 trial 都收敛到同一业务结论。

基于最近 **3** 次有效对比实验（均为真正跑到 task-level、存在完整 agent 轨迹；已排除 build cancelled 类 trial）：

| 维度 | Without Skill | With Skill | 结果对比 |
| :--- | :--- | :--- | :--- |
| 通过率 | `0%` | `33%` | 3 组有效对照里，without skill 没有一次完整通过；with skill 有 1 次完整通过，说明 skill 对收敛有帮助，但稳定性仍需继续提升 |
| Agent 执行耗时 | `629.5s` | `611.1s` | With skill 的平均 Agent 耗时降低约 `2.9%` |
| Tokens | `733.3k` | `696.7k` | With skill 的平均 token 开销降低约 `5.0%` |

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
│   ├── skills/
│   └── workspace/
├── tests/
│   ├── reference_metrics.py
│   ├── test.sh
│   └── test_outputs.py
└── solution/
    ├── fixed/
    │   └── run_airport_partner_analysis.py
    └── solve.sh
```
