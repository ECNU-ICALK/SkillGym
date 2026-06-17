# Business-Apps Template

这是面向 `business-apps` 类 skill 的模板。它综合参考 SkillsMP `business-apps` 类热门 skill 的共性能力：业务系统事实核对、旧导出与当前状态对齐、动作分流、运营节奏控制、收入风险识别，以及把多来源业务事实沉淀成结构化交付物。

## 第一部分：任务设计参考

* **Skill 价值定位**：`business-apps` 类热门 skill 的共同价值，是把 CRM、billing、ops policy、action queue 这类分散事实组织成稳定的运营决策流程。高质量 skill 不应直接给出答案，而应帮助 solver 更快识别权威事实源、数据漂移位置、动作优先级和交付物的收口方式。
* **Verifier 设计重点**：Verifier 应优先验证 solver 是否完成了当前业务链路和关键动作，而不是只卡格式细节。重点应覆盖权威服务访问、分页完整性、细项子资源核对、动作唯一性、汇总一致性，以及对旧导出依赖、跳过 live chain、硬编码结果和篡改环境的防护。

## 第二部分：示例任务

### 📌 任务元数据

- 任务 ID：`business-apps__renewal-action-queue`
- 类别：`business-apps`
- 绑定 Skill：`billing-automation`
- 输入数据参考来源：
  - `environment/data/crm_export.csv`：任务内续费 cohort 与 CRM 字段快照；字段语义参考 Stripe Subscription object  
    https://docs.stripe.com/api/subscriptions/object
  - `environment/data/invoice_snapshot.ndjson`：任务内 invoice 与 dunning 状态快照；字段语义参考 Stripe Invoice object  
    https://docs.stripe.com/api/invoices/object
  - `environment/data/action_policy.yaml`：任务内动作分流规则与阈值；语义参考 Chargebee Dunning v2  
    https://www.chargebee.com/docs/payments/2.0/dunning/dunning-v2
  - `environment/data/contact_directory.csv`：任务内账户负责人和升级联系信息；为本模板自定义的本地运营输入，无单独公开来源

### 📊 验证与测试指标（Oracle & Verifier）

- Oracle：按正式流程独立运行并完成交付，结果可直接 100% 通过验证。
- Verifier策略：

主测试

| 测试点 | 验证内容 | 对应skill内化点 |
| :--- | :--- | :--- |
| 输出规范 | 检查 CSV / JSON / Markdown 文件是否存在、格式是否可解析，并满足必需字段与枚举值的定义要求 | 深入理解交付标准，构建标准化的结构化输出 |
| 业务逻辑重演 | 基于当前服务与策略，重新核算每个账户的操作类型、触发原因及后续处理步骤 | 遵循权威数据源、确保动作唯一性、落实业务规则 |
| 数据汇总一致性 | 校验操作计数、账户总数、年度经常性收入（ARR）总额及流程受阻账户列表，确保其与明细数据的结果保持闭环一致 | 保证明细判断与全局汇总结果的一致性收口 |
| 业务摘要逻辑 | 检查摘要是否准确提取了受阻账户、大额扩容账户、高优先级催收账户及相关的路由逻辑说明 | 提升面向业务运营方的结构化汇报能力 |

防作弊测试

| 测试点 | 验证内容 |
| :--- | :--- |
| 调用链路校验 | 求解程序必须在验证前完整查询配置清单、全量分页数据以及每个账户的详情、续约预览与催收事实 |
| 环境完整性 | 确保 `/root/data` 目录、系统隐藏服务及安装后的文件哈希值保持不变，严禁非法篡改 |
| 动态数据覆盖 | 确保在处理过程中，未遗漏较早备份数据中缺失、仅在实时链路中存在的增量账户 |
| 服务运行状态 | 在验证过程结束时，需确认本地 `revops` 服务依然保持健康的运行状态 |

### ⚡ Skill 相关性评估

结论：相关。这个任务里，Skill 的核心价值是把 manifest 拉取、分页 cohort、逐账户 detail / renewal preview / dunning 扩展，以及唯一动作分流整理成一条更稳定的工作链路。当前剩余失败主要集中在 `workflow_blocked_account_ids` 的口径热点，但 with Skill 组仍明显优于 without Skill 组。

基于最近 **3** 次有效对比实验（均为真正跑到 task-level、存在完整 agent 轨迹；已排除启动失败类 trial）：

| 维度 | Without Skill | With Skill | 结果对比 |
| :--- | :--- | :--- | :--- |
| 通过率 | `0%` | `33%` | 近 3 次有效对照里，without Skill 不如 with Skill 原因：without Skill 主要败在多信号账户的动作优先级和 `workflow_blocked_account_ids` 汇总口径，尤其容易把 `ACC-105` 误判进阻塞名单，或把它从 `update_expansion_quote` 误判成采购升级动作。 |
| Agent 执行耗时 | `250.2s` | `178.5s` | With Skill 的平均 Agent 耗时降低约 `28.6%`，分流收敛更快。 |
| Tokens | `0.72M` | `0.31M` | Without Skill 的上下文与试错开销约为 With Skill 的 `2.36x`。 |

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
│   ├── hidden-service-src/
│   └── skills/
├── tests/
└── solution/
```
