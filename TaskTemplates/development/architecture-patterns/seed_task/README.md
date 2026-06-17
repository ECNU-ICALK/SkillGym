# Architecture Patterns Template

这是面向 Architecture Patterns 类 skill 的模板。它综合参考 SkillsMP Architecture Patterns 类热门 skill 的共性能力：在已有系统中补一项新能力、沿既有入口和契约接入、保持领域逻辑与交付方式解耦，并通过完整运行链路验证行为，避免停留在表面拼接。

## 第一部分：任务设计参考

* **Skill 价值定位**：Architecture Patterns 类热门 skill 的核心价值，在于让新增能力沿现有系统边界落地，保持接口、数据映射、运行入口和交付结果之间的清晰职责分离。对于 `api-connector-builder` 这类 skill，关键点是先识别仓库里已有集成模式，再把新能力按同一风格接完整。
* **Verifier 设计重点**：Verifier 应优先验证 solver 是否沿现有链路完成了能力接入，是否让 HTTP 与批量导出走同一业务口径，是否能在 alternate fixture 上保持泛化能力，以及是否保留了既有入口和完整运行方式。重点不在格式细节，而在于确认 solver 没有绕过系统边界、没有只修可见样例、也没有把任务退化成静态结果生成。

## 第二部分：示例任务

### 📌 任务元数据

- 任务 ID：`architecture-patterns__mta-schedule-provider-gateway`
- 类别：`architecture-patterns`
- 绑定 Skill：`api-connector-builder`
- 输入数据参考来源：
  - `environment/workspace/data/gtfs/agency.txt`：任务内机构元数据；直接来源于 MTA static GTFS subway feed  
    【https://www.mta.info/developers】
  - `environment/workspace/data/gtfs/routes.txt`：任务内线路主数据；直接来源于 MTA static GTFS subway feed  
    【https://www.mta.info/developers】
  - `environment/workspace/data/gtfs/stops.txt`：任务内站点与父子站台关系；直接来源于 MTA static GTFS subway feed  
    【https://www.mta.info/developers】
  - `environment/workspace/data/gtfs/trips.txt`：任务内班次主数据；直接来源于 MTA static GTFS subway feed  
    【https://www.mta.info/developers】
  - `environment/workspace/data/gtfs/stop_times.txt`：任务内停靠时序；直接来源于 MTA static GTFS subway feed  
    【https://www.mta.info/developers】
  - `environment/workspace/data/gtfs/calendar.txt`：任务内服务日历；直接来源于 MTA static GTFS subway feed  
    【https://www.mta.info/developers】
  - `environment/workspace/data/gtfs/calendar_dates.txt`：任务内服务例外日历；直接来源于 MTA static GTFS subway feed  
    【https://www.mta.info/developers】
  - `environment/workspace/data/delivery_contract.yaml`：任务内字段合同；设计语义参考 GTFS Schedule Reference  
    【https://gtfs.org/】

### 📊 验证与测试指标（Oracle & Verifier）

- Oracle：按正式流程独立运行并完成交付，结果可直接 100% 通过验证。
- Verifier 策略：

主测试

| 测试点 | 验证内容 | 对应 skill 内化点 |
| :--- | :--- | :--- |
| 基础结构齐备 | 页面入口、依赖程序与关键脚本能够顺利启动 | 任务初始环境整合配置 |
| 过程与流转检验 | 在页面中对目标核心场景进行操作，相关反馈流程应完整并生效 | 功能环节串联度测试 |
| 相同输入复现 | 在同样基础环境下多次运行或重试，可得出相同结构的数据响应 | 实现结果稳定性保障 |
| 多变体动态适配 | 当替换输入基础数据时，系统需提供正确的衍生显示及相关逻辑应对 | 灵活性与输入参数探索 |
| 输出一致性校验 | 核对业务面板展现或汇总内容的说明能否对得上要求数据范围 | 分析处理数据的呈现准度 |
| 结构交付合规 | 最终保存下来的生成文档或者资源内容格式齐整 | 最终发布过程追溯 |

防作弊测试

| 测试点 | 验证内容 |
| :--- | :--- |
| 限定参数核实 | 限制篡改依赖目录或源信息进行取巧完成 |
| 源文件定值扫描 | 发现直接在项目中输出预期静态内容以作答的问题现象 |

### ⚡ Skill 相关性评估

结论：强相关。这个任务里，Skill 的核心价值是把“先找现有 provider 接入形态、再检查共享 loader / registry 作用域、最后统一校验 HTTP / export / local toolchain”这条工作流压实；without skill 时，solver 更容易只把主查询链路补通，漏掉多 data-root 同进程场景下的共享缓存边界。

基于最近 **3 次**有效对照实验（均为跑到 task-level、存在完整 trial 结果；已排除 build/startup 失败类 trial）：

| 维度 | Without Skill | With Skill | 结果对比 |
| :--- | :--- | :--- | :--- |
| 通过率 | `0%` | `100%` | without Skill 的 3 次 trial 都留下了 action-level 漏项，集中表现为只补可见查询链路、漏掉 compare-root / same-process dual-root，或误删既有 provider catalog；with Skill 3 次均完整通过 |
| Agent 执行耗时 | `326.6s` | `324.7s` | 两侧耗时接近，差异主要体现在收敛质量；with Skill 略快约 `0.6%` |
| Tokens | `0.72M` | `0.72M` | token 规模接近；with Skill 平均 token 更低，约为 without Skill 的 `0.99x` |

## 📁 标准目录结构说明

```text
seed_task/
├── instruction.md
├── task.toml
├── PLAN.json
├── README.md
├── environment/
│   ├── Dockerfile
│   ├── skills/
│   └── workspace/
├── tests/
└── solution/
```
