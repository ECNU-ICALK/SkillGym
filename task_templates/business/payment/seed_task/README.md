# Payment Template

这是面向 `payment` 类 skill 的模板。它综合参考 SkillsMP payment 类热门 skill 的共性能力：票据识别、供应商归一化、付款批次审查、重复单据判定、当前状态核验、归档路径整理，以及把多来源付款事实收口成可审计交付物。

## 第一部分：任务设计参考

* **Skill 价值定位**：payment 类热门 skill 的核心价值，是把分散在票据目录、供应商主数据、付款状态 service 和批次规则里的事实，组织成一条稳定的应付账款处理链路。模板任务应让 skill 在目录遍历、字段提取、供应商统一、重复判定、付款状态核验和交付物收口这些环节降低试错成本。
* **Verifier 设计重点**：Verifier 应优先验证 solver 是否完成了完整业务链路和关键动作，并检查单据台账、批次纳入结果、重复判定、service 访问和归档副本是否一致。重点应覆盖嵌套目录遍历、容器内 AP review service 优先级、快照规避、分页与明细抓取、路径命名规则、输入不可改和输出副本完整性。

## 第二部分：示例任务

### 📌 任务元数据

- 任务 ID：`payment__invoice_batch_review`
- 类别：`payment`
- 绑定 Skill：`invoice-organizer`
- 输入数据参考来源：
  - `environment/data/inbox/cloud/aws/statement-2014-08.pdf`：任务内票据样本；直接来源于  
    https://raw.githubusercontent.com/invoice-x/invoice2data/master/tests/compare/AmazonWebServices.pdf
  - `environment/data/inbox/facilities/azure/q1-office-renewal.pdf`：任务内票据样本；直接来源于  
    https://raw.githubusercontent.com/invoice-x/invoice2data/master/tests/compare/AzureInterior.pdf
  - `environment/data/inbox/retail/flipkart/card-accessory-bill.pdf`：任务内票据样本；直接来源于  
    https://raw.githubusercontent.com/invoice-x/invoice2data/master/tests/compare/FlipkartInvoice.pdf
  - `environment/data/inbox/legal/netpresse-publication-invoice.pdf`：任务内票据样本；直接来源于  
    https://raw.githubusercontent.com/invoice-x/invoice2data/master/tests/compare/NetpresseInvoice.pdf
  - `environment/data/inbox/infra/qualityhosting/mail-hosting-may.pdf`：任务内票据样本；直接来源于  
    https://raw.githubusercontent.com/invoice-x/invoice2data/master/tests/compare/QualityHosting.pdf
  - `environment/data/inbox/telco/free/fiber-july.pdf`：任务内票据样本；直接来源于  
    https://raw.githubusercontent.com/invoice-x/invoice2data/master/tests/compare/free_fiber.pdf
  - `environment/data/inbox/office/coolblue/hardware-order.pdf`：任务内票据样本；直接来源于  
    https://raw.githubusercontent.com/invoice-x/invoice2data/master/tests/compare/coolblue1.pdf
  - `environment/data/inbox/fuel/orlen/mobile-pay.txt`：任务内票据文本样本；直接来源于  
    https://raw.githubusercontent.com/invoice-x/invoice2data/master/tests/compare/Orlen.txt
  - `environment/data/inbox/misc/reimports/aws-statement-duplicate.pdf`：任务内重复导入样本；内容设计形态参考  
    https://raw.githubusercontent.com/invoice-x/invoice2data/master/tests/compare/AmazonWebServices.pdf
  - `environment/data/vendor_master.csv`：任务内供应商主数据；为模板整理后的本地业务输入，无单独公开数据链接
  - `environment/data/settlement_snapshot.csv`：任务内较早导出的付款状态快照；为模板整理后的本地业务输入，无单独公开数据链接
  - `environment/data/batch_context.json`：任务内批次上下文与 service 入口；为模板整理后的本地业务输入，无单独公开数据链接
  - `environment/data/filing_policy.yaml`：任务内命名、归档和重复判定规则；为模板整理后的本地业务输入，无单独公开数据链接

### 📊 验证与测试指标（Oracle & Verifier）

- Oracle：按正式流程独立运行并完成交付，结果可直接 100% 通过验证。
- Verifier策略：

主测试

| 测试点 | 验证内容 | 对应skill内化点 |
| :--- | :--- | :--- |
| 输出规范 | 检查 `invoice_register.csv`、`payment_batch.json` 和 `batch_review.md` 等报表文件是否存在、能否被解析，且包含必备的列名与核心数据结构 | 掌握业务系统对接标准，输出规范的结构化结果 |
| 目录解析与明细核算 | 完整遍历并读取所有文件夹中的单据，重新计算并严格核对供应商名称、单据编号、日期、金额、币种及费用类别 | 掌握“文件扫描 -> 信息提取 -> 数据标准化 -> 生成台账”的完整闭环 |
| 当前状态与归集判定 | 结合 AP 审核系统和业务规则，重新核对并判断付款状态（`payment_status`）、是否允许编入批次（`eligible_for_batch`）、排除原因及备注 | 掌握核验付款状态、判定纳入资格与人工复核流程的汇总 |
| 重复项处理与归档路径 | 检查在处理重复单据时的保留项与剔除项是否正确，最终的文件归档路径和命名是否严格遵守了业务规则（policy） | 掌握识别重复机制、执行规范命名与整理归档文件的能力 |
| 批次汇总一致性 | 核对应付单据、暂缓付款单据、币种总计金额等宏观统计数据，是否与之前的明细表数据完全咬合一致 | 掌握全局数据汇总，确保生成逻辑严密、可审计的报表 |
| 批次说明逻辑 | 检查批次说明文档是否准确写明了单据总数、符合付款条件的数量、不可处理项、需人工复核项、重复项及总体币种金额汇总 | 提升向业务运营方清晰汇报工作成果的表达能力 |

防作弊测试

| 测试点 | 验证内容 |
| :--- | :--- |
| 调用链路校验 | 操作日志必须证明：程序完整读取了各项配置，翻阅了全部单据记录，并真实调用系统获取了每份单据的审核详情，不可跳步 |
| 静态数据拦截 | 严禁直接抄写过期的 `settlement_snapshot.csv` 快照数据交差；仅存在于实时系统中的最新动态变更必须在最终结果中体现 |
| 数据与环境完整性 | 确保原始 `/root/data/` 目录及后台服务文件绝对不能被篡改；测试结束后，系统服务必须仍在正常运行 |
| 输出副本完整性 | 最终明细表里的每一条记录，都必须有一份对应的整理后的文件副本，且确保文件内容（哈希值）没有被任何形式的修改 |
| 路径与扩展名约束 | 最终整理出的文件存放路径必须严格遵守 `filing_policy.yaml` 规则的要求，并且不能修改文件原本的扩展后缀名 |

### ⚡ Skill 相关性评估

结论：相关性较强。这个任务里，Skill 的核心价值是把票据目录扫描、字段提取、供应商归一化、重复组处理、状态核验和批次收口串成一条工作流，从而降低在多语言票据、分页 review service 和整理副本联动上的试错成本。without Skill 仍然可解，但更容易停在发票号抽取、批次纳入和归档路径联动错误这类行动级失败上。

基于最近 **3** 次有效对比实验（均为真正跑到 task-level、存在完整 agent 轨迹；已排除启动失败类 trial）：

| 维度 | Without Skill | With Skill | 结果对比 |
| :--- | :--- | :--- | :--- |
| 通过率 | `0%` | `33.3%` | 近 3 次有效对照里，without Skill 为 `0/3`；with Skill 为 `1/3`。without Skill 主要败在多语言发票号抽取，以及随后的批次清单与整理副本联动错误。 |
| Agent 执行耗时 | `527.8s` | `444.7s` | With Skill 的平均 Agent 耗时降低约 `15.8%`。 |
| Tokens | `889855` | `777221` | Without Skill 的平均 token 开销约为 With Skill 的 `1.14x`。 |

## 📁 标准目录结构说明

```text
模板任务：
├── instruction.md          # 任务说明（仅包含症状、业务约束和禁止事项）
├── task.toml               # 任务元数据（标签、技能要求、运行入口）
├── PLAN.json               # 任务构建过程的结构化元信息
├── README.md               # 模板说明、任务设计参考、示例任务和实验结果
├── environment/            # 运行环境
│   ├── Dockerfile          # 单容器镜像定义；在同一容器内启动 AP review service 与隐藏下游服务
│   ├── data/               # 任务输入数据、规则文件和批次上下文
│   ├── hidden-service-src/ # 本地 AP review service 实现与数据
│   └── skills/             # 任务绑定的 payment skill 定义与辅助脚本
├── tests/                  # Verifier 与 Guardrail 测试集
└── solution/               # 官方参考修复代码及 solve.sh
```
