# Ecommerce Template

这是面向 `ecommerce` 类 skill 的模板。它综合参考 SkillsMP ecommerce 类热门 skill 的共性能力：真实店铺运营链路理解、订单与商品事实收集、SKU / variant 对齐、库存与履约排查、物流状态核验，以及把多来源业务事实沉淀成可审计交付物。

## 第一部分：任务设计参考

* **Skill 价值定位**：ecommerce 类热门 skill 的核心价值，是把订单、商品、库存、物流、支付和运营工具里的碎片化事实，组织成稳定的业务执行路径。它不应该直接泄露答案，而应帮助 solver 更快识别应该检查哪些系统、如何对齐实体，以及如何把结果整理成运营团队可执行的动作清单。
* **Task 目标形态**：任务应落在真实风格的电商运营场景里，例如订单排障、履约对账、库存冲突处理、SKU / listing 映射校验或物流异常复核。题面应主要交代业务症状、交付合同和禁止事项，把诊断步骤尽量留给 skill 和 solver 自己识别，而不是把完整工作流写成“照做题”。
* **Verifier 设计重点**：Verifier 应优先验证 solver 是否完成了真实业务链路和关键动作，而不是只卡格式细节。它应重算多来源事实、检查 live 数据优先级、验证实体对齐和结果一致性，并通过防作弊测试拦截 stale export 依赖、跳过分页、替换真实链路、篡改输入或硬编码答案等捷径。

## 第二部分：示例任务

### 📌 任务元数据

- 任务 ID：`ecommerce__fulfillment-exception-reconciliation`
- 类别：`ecommerce`
- 难度：`hard`
- 绑定 Skill：`commerce-fulfillment-recon`
- 输入数据参考来源：
  - `environment/data/catalog_export.csv`：任务内商品数据；字段形态参考 Shopify 商品 / 变体 / fulfillment service  
    https://shopify.dev/docs/api/admin-graphql  
    https://shopify.dev/docs/api/admin-graphql/latest/objects/ProductVariant
  - `environment/data/order_snapshot.ndjson`：任务内订单快照；字段形态参考 Shopify 订单与订单状态  
    https://shopify.dev/docs/api/admin-graphql/latest/objects/Order
  - `environment/data/carrier_status_codes.csv`：任务内物流状态映射；语义参考 Shippo Tracking API 的 tracking status / event  
    https://docs.goshippo.com/docs/tracking/tracking/
  - `environment/data/merchant_manifest.json`：任务内本地配置文件，用于声明 live 服务地址与 reconciliation window，无单独公开数据链接

### 📊 验证与测试指标（Oracle & Verifier）

- Oracle：按正式流程独立运行并完成交付，结果可直接 100% 通过验证。
- Verifier策略：主测试重算异常行和汇总口径，防作弊测试验证 live 服务访问、分页、stale snapshot 规避、输入不可篡改和服务健康度。

主测试

| 测试点 | 验证内容 | 对应skill内化点 |
| :--- | :--- | :--- |
| 输出契约 | 检查 CSV / JSON 是否存在、可解析，并包含必需字段和顶层键 | 先理解正式交付物，再组织结构化输出 |
| live 异常重算 | 从 commerce admin、warehouse、carrier 服务重新计算异常行，并核对 issue、severity、expected_action | 按正确顺序访问真实链路，并把多来源事实对齐到同一 line item |
| 汇总一致性 | 校验 summary totals、issue_counts、orders_with_exceptions 与 CSV 行级结果一致 | 保证行级结论、汇总指标和业务动作口径一致 |
| 证据语义 | 检查 evidence JSON 能回链到订单 / line item / SKU，并包含对应问题类型的最小审计事实 | 输出可审计证据，而不是只给表面标签 |

防作弊测试

| 测试点 | 验证内容 |
| :--- | :--- |
| 真实链路与分页 | 访问日志必须证明 solver 查询了 live orders、variants、warehouse、carrier，并实际跟进了 GraphQL 分页 |
| 数据与环境完整性 | `/root/data/` 和隐藏服务哈希不得变化，服务在 verifier 结束时仍健康，且 live-only 订单不能被 stale snapshot 漏掉 |

### ⚡ Skill 相关性评估

结论：强相关。这个任务里，Skill 的核心价值是把 Shopify-like GraphQL、库存预留、物流状态和 SKU / variant 对齐这几条高成本诊断路径标准化，同时把题面刻意弱化掉的工作流细节补回来。without Skill 仍然理论可解，但更容易在动作选择、汇总口径闭环和多来源证据收口上出现行动级失败。

基于最近 **3** 次有效对比实验（均为真正跑到 task-level、存在完整 agent 轨迹；已排除启动失败类 trial）：

| 维度 | Without Skill | With Skill | 结果对比 |
| :--- | :--- | :--- | :--- |
| 通过率 | `0/3 (0%)` | `2/3 (66.7%)` | without Skill 的 3 次有效 trial 都留下了 verifier 失败；with Skill 有 2 次完整通过，1 次只差 warehouse source summary 收口 |
| Agent 执行耗时 | `276.7s` | `254.7s` | With Skill 的平均 Agent 耗时更低，约下降 `8.0%` |
| Tokens | `634.1k` | `701.6k` | 本组实验里 without Skill 的 token 更低，但主要因为其更早停在不完整的动作/汇总输出上；with Skill 为了完成 live reconciliation 与证据闭环，平均 token 更高但通过率显著更好 |

## 📁 标准目录结构说明

```text
模板任务：
├── instruction.md          # 任务说明（症状、业务约束、输出合同、禁止事项、reference data）
├── task.toml               # 任务元数据（标签、技能要求、超时、环境资源）
├── PLAN.json               # 任务构建元信息（设计理由、环境取舍、verifier 重点、实验口径）
├── README.md               # 模板说明、实验结果与目录结构
├── environment/            # 单容器运行环境
│   ├── Dockerfile          # 同容器内启动 commerce admin、warehouse、carrier 等真实风格链路
│   ├── data/               # 冻结输入数据
│   ├── hidden-service-src/ # 隐藏服务实现
│   └── skills/             # 仅 with_skill 环境保留的绑定 skill
├── tests/                  # Verifier 主测试与防作弊测试
└── solution/               # 官方参考解与 solve.sh
```
