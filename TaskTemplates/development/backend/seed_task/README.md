# Backend Template

这是面向 Backend 类 skill 的模板。它综合参考 SkillsMP Backend 类热门 skill 的共性能力：生产级 REST API 设计、资源命名与版本化、查询参数契约、幂等写入、安全重试、错误语义分层，以及认证与限流等跨切面治理。

## 第一部分：任务设计参考

* **Skill 价值定位**：Backend 类热门 skill 的核心价值，不是单纯把接口“跑通”，而是把服务从“能返回东西”提升到“可被合作方稳定集成”。它要求 solver 同时理解资源模型、状态码语义、分页与筛选顺序、错误对象契约、幂等重试和流量保护，而不是只修一两个 happy path。
* **Verifier 设计重点**：Verifier 应优先验证真实 HTTP 行为是否恢复稳定，包括认证/鉴权分层、过滤排序分页的计算顺序、创建接口的幂等重试语义、状态冲突处理、限流头与 `429` 行为，以及对变体数据的泛化能力。防作弊点应覆盖硬编码订单 ID、只修固定分页切片、加平行接口绕过原链路、伪造重复请求回放和只在单一数据排列下成立的实现。

## 第二部分：示例任务

### 📌 任务元数据

- 任务 ID：`partner-order-refund-api-contract`
- 类别：Backend
- 绑定 Skill：`api-design`
- 输入数据参考来源：
  - `environment/workspace/data/orders_snapshot.json`：任务内订单字段与业务语义；设计形态参考 Shopify Order resource  
    https://shopify.dev/docs/api/admin-rest/latest/resources/order
  - `environment/workspace/data/customers_snapshot.json`：任务内客户与地址字段；设计形态参考 Shopify Customer resource  
    https://shopify.dev/docs/api/admin-rest/latest/resources/customer
  - `environment/workspace/data/refund_requests.json`：任务内退款对象与生命周期；设计形态参考 Shopify Refund resource  
    https://shopify.dev/docs/api/admin-rest/latest/resources/refund
  - `environment/workspace/data/refund_requests.json`：创建类请求的安全重试语义参考 Stripe Idempotent Requests  
    https://docs.stripe.com/api/idempotent_requests
  - `environment/workspace/data/refund_requests.json`：退款状态与对象语义参考 Stripe Refund object  
    https://docs.stripe.com/api/refunds/object

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

结论：强相关。这个任务里，Skill 的核心价值是把“API 看起来能用”和“API 能被稳定集成”之间的差距标准化，尤其体现在资源命名、统一错误语义、过滤排序分页顺序、幂等重试和限流头这些跨切面问题上。without Skill 理论上可解，但更容易停留在只修单点 bug 的层面，漏掉重复写入保护、状态冲突分层或 alternate fixture 下的稳定性。

基于最近 **3 次有效 with_skill trial 与 3 次有效 without_skill trial**（均为真正跑到 task-level、存在完整 agent 轨迹；已排除启动失败类 trial）：

| 维度 | Without Skill | With Skill | 结果对比 |
| :--- | :--- | :--- | :--- |
| 通过率 | `0/3` | `1/3` | without Skill 最近 3 次都至少保留 1 个 verifier 失败，且失败集中在退款状态冲突、缺失 `Idempotency-Key` 或缺失资源机器码等行动级契约；with Skill 最近 3 次里，2 次仅差单个 machine-readable error code alias，1 次已 `9/9` 全过。 |
| Agent 执行耗时 | `422.8s` | `514.4s` | with Skill 近期均值比 without 高约 `21.7%`；主因是两次 near-pass 在统一错误语义上额外消耗了诊断与校验回合。最新成功样本耗时 `410.5s`。 |
| Tokens | `1.01M` | `1.30M` | with Skill 近期均值比 without 高约 `28.4%`；主因同上。最新成功样本 token 为 `860.7k`。 |

## 📁 标准目录结构说明

```text
模板任务：
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
