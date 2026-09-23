# NoSQL Databases Template

这是面向 `nosql-databases` 类 skill 的模板。它综合参考 SkillsMP NoSQL 数据库类热门 skill 的共性能力：围绕键空间设计、访问模式与数据结构匹配、重复执行安全、运行态状态检查、以及沿既有入口完成结果交付，设计一个可运行、可验证的任务。

## 第一部分：任务设计参考

* **Skill 价值定位**：NoSQL 数据库类热门 skill 的共性价值，在于把“能把结果写出来”提升到“能把数据结构、访问路径、运行态状态和重复执行行为一起设计对”。这类任务适合让 solver 在键空间、对象表示、排序结构、过期策略和结果回写之间做成完整闭环。
* **Verifier 设计重点**：Verifier 应同时验证结果内容、运行态状态、重复执行一致性和对当前输入的响应，避免只看单次静态产物。对 NoSQL 数据库类任务，还应拦截改输入、绕开既有服务、手写答案、只写文件不写状态，以及重复执行后状态叠加等捷径。

## 第二部分：示例任务

### 📌 任务元数据

- 任务 ID：`nosql-databases__redis-bike-share-rebalancing-plan`
- 类别：`nosql-databases`
- 绑定 Skill：`redis-expert`
- 输入数据参考来源：
  - `environment/workspace/data/station_information.json`：任务内站点元数据；字段形态参考 Citi Bike GBFS station information  
    【https://gbfs.citibikenyc.com/gbfs/en/station_information.json】
  - `environment/workspace/data/station_status.json`：任务内站点可用车与可用桩状态；字段形态参考 Citi Bike GBFS station status  
    【https://gbfs.citibikenyc.com/gbfs/en/station_status.json】
  - `environment/workspace/data/system_regions.json`：任务内 region 标识与名称；直接来源于 Citi Bike GBFS system regions  
    【https://gbfs.citibikenyc.com/gbfs/en/system_regions.json】
  - `environment/workspace/data/system_information.json`：任务内网络级元数据；直接来源于 Citi Bike GBFS system information  
    【https://gbfs.citibikenyc.com/gbfs/en/system_information.json】

### 📊 验证与测试指标（Oracle & Verifier）

- Oracle：按正式流程独立运行并完成交付，结果可直接 100% 通过验证。
- Verifier策略：

主测试

| 测试点 | 验证内容 | 对应skill内化点 |
| :--- | :--- | :--- |
| 输出契约 | 检查 CSV / JSON 是否存在、可解析、列名与顶层键满足合同 | 先理解正式交付物，再组织结果 |
| 计划重算 | 从当前输入重算调度计划并核对行内容、排序和 move 数量 | 把访问模式映射到合适的排序与对象结构 |
| 汇总一致性 | 校验 summary totals、action counts、region 汇总与 CSV 行级结果一致 | 保持行级结果、汇总口径和业务动作闭环 |
| 运行态状态 | 检查 Redis manifest、站点对象、选中集合与过期时间 | 键空间设计、对象表示、运行态可检查性 |
| 重复执行 | 连续 rerun 后，输出和 Redis 键数量保持稳定 | 重复执行安全与状态刷新路径 |

防作弊测试

| 测试点 | 验证内容 |
| :--- | :--- |
| 输入完整性 | 公开来源输入文件不可修改 |
| 当前输入敏感性 | 在输入副本上改动站点状态后，计划结果必须跟着变化 |
| 服务路径约束 | 结果不能只落文件而跳过 Redis 状态写入 |

### ⚡ Skill 相关性评估

结论：强相关。这个任务的关键难点不在单次算出几行 CSV，而在于把站点对象、region 排名、选中计划、重复执行安全和键空间状态一起做对。skill 的主要价值，是把 Redis 数据结构选择、运行态索引、review key 命名和重复执行清理路径一起拉到同一个工作流里，从而明显降低“输出文件看起来对，但 Redis working state 不可审查”的风险。

基于最近 **3 次有效对比实验** 的当前 verifier 复核结果（对应 `v10 / v11 / v13`，均为真正跑到 task-level、存在完整 agent 轨迹；已排除启动失败类 trial）：

| 维度 | Without Skill | With Skill | 结果对比 |
| :--- | :--- | :--- | :--- |
| 通过率 | `0%` | `100%` | 3 条对照里，without Skill 都停在 Redis review state 契约，常见问题是 membership / ordered index 里放了 plan key、manifest alias 漏写，或 summary review key 不完整；with Skill 能稳定把 Redis 运行态一起做对 |
| Agent 执行耗时 | `365.8s` | `432.4s` | With Skill 在这 3 条样本里平均多花约 `18.2%` 时间做运行态检查与键空间收口，收益主要体现在通过率而非耗时压缩 |
| Tokens | `1.28M` | `1.48M` | With Skill 平均多用约 `16.3%` tokens，用在 Redis 结构核对、manifest 复查和重复执行校验；额外上下文换来了可验证通过 |

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
│   │   └── redis-expert/
│   └── workspace/
├── tests/
│   ├── test.sh
│   └── test_outputs.py
└── solution/
    ├── solve.sh
    └── fixed/
```
