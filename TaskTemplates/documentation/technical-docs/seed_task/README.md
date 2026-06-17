# Technical Docs Template

这是面向 `technical-docs` 类 skill 的模板。它综合参考 SkillsMP
technical-docs 类热门 skill 的共性能力：围绕公开代码与测试输入补齐缺失
文档页，按既定站点格式交付结构化 API 说明，并保留可重跑的生成入口。

## 第一部分：任务设计参考

* **Skill 价值定位**：technical-docs 类 skill 的核心价值，是把源码、测试、
  现有文档风格和交付合同收束成可发布的说明页。模板任务适合让 agent 在
  API coverage、行为说明、示例组织和站点格式之间做完整收尾。
  API 说明重建、参数与行为梳理等交付。目标应强调单页交付、固定输入边界、
  正式构建入口和结构化 manifest。
* **Verifier 设计重点**：Verifier 应覆盖正式生成入口、合同约束、示例与
  API 项覆盖、来源依据和可重跑能力。重点应放在是否完成整页交付，并检查
  页面与 manifest 能否把关键行为说明追溯回当前 bundle 中的源码、测试和
  release snapshot。

## 第二部分：示例任务

### 📌 任务元数据

- 任务 ID：`technical_docs__pqueue_api_reference_page`
- 类别：`technical-docs`
- 绑定 Skill：`write-api-reference`
- 输入数据参考来源：
  - `environment/reference_bundle/upstream/package.json`：任务内包元数据  
    【https://raw.githubusercontent.com/sindresorhus/p-queue/v8.1.1/package.json】
  - `environment/reference_bundle/upstream/source/index.ts`：任务内主实现  
    【https://raw.githubusercontent.com/sindresorhus/p-queue/v8.1.1/source/index.ts】
  - `environment/reference_bundle/upstream/source/options.ts`：任务内选项类型  
    【https://raw.githubusercontent.com/sindresorhus/p-queue/v8.1.1/source/options.ts】
  - `environment/reference_bundle/upstream/test/test.ts`：任务内行为测试  
    【https://raw.githubusercontent.com/sindresorhus/p-queue/v8.1.1/test/test.ts】
  - `environment/reference_bundle/upstream/readme.md`：任务内 README 快照  
    【https://raw.githubusercontent.com/sindresorhus/p-queue/v8.1.1/readme.md】
  - `environment/reference_bundle/upstream/release_v8.1.1.html`：任务内版本页快照  
    【https://github.com/sindresorhus/p-queue/releases/tag/v8.1.1】
  - `environment/reference_bundle/site_examples/*.mdx`：页面形态参考自 Next.js
    API 文档示例页  
    【https://raw.githubusercontent.com/vercel/next.js/canary/docs/01-app/03-api-reference/04-functions/cookies.mdx】
    【https://raw.githubusercontent.com/vercel/next.js/canary/docs/01-app/03-api-reference/03-file-conventions/page.mdx】
    【https://raw.githubusercontent.com/vercel/next.js/canary/docs/01-app/03-api-reference/02-components/link.mdx】
    【https://raw.githubusercontent.com/vercel/next.js/canary/docs/01-app/03-api-reference/01-directives/use-client.mdx】
    【https://raw.githubusercontent.com/vercel/next.js/canary/docs/01-app/03-api-reference/04-functions/fetch.mdx】

### 📊 验证与测试指标（Oracle & Verifier）

- Oracle：按正式流程独立运行并完成交付，结果可直接 100% 通过验证。
  生成 API 页面与 manifest，再独立核对合同中的 API 项、示例、版本说明、
  源输入引用以及源码/测试证据是否齐全。
- Verifier策略：

主测试

| 测试点 | 验证内容 | 对应skill内化点 |
| :--- | :--- | :--- |
| 正式产物生成 | build 入口生成 MDX 页面与 manifest | 文档交付入口收敛 |
| 合同覆盖 | 必需 API 项、章节、表格、示例、版本说明齐全 | API reference 结构化交付 |
| 行为依据 | timeout、AbortSignal、priority、idle/empty 等说明落到页面 | 读源码与测试提炼行为 |
| 证据回填 | `id` 自增起点、`sizeBy` 计数、timeout 变更与 release highlight 能在页面和 manifest 中回填 | 从实现、测试和 release snapshot 提取关键证据 |
| manifest 对齐 | 页面内容与 manifest 中的 API 项、示例、版本说明一致 | 结构化审阅清单 |
| alternate fixture 泛化 | 替代输入下输出会随合同与版本数据变化 | 可重跑工作流 |

防作弊测试

| 测试点 | 验证内容 |
| :--- | :--- |
| 输入不可变 | `/environment/reference_bundle` 哈希不变 |
| Skill 可用性 | 运行时可发现 `write-api-reference`，帮助补齐 API 参考页结构与用例说明 |
| 输出白名单 | `/environment/output` 顶层只保留规定产物 |
| 残留清理 | 输出中不允许出现占位词或 verifier 痕迹 |

### ⚡ Skill 相关性评估

结论：强相关。这个任务里，Skill 的核心价值是把单页 API 文档的结构、
示例摆放、行为说明和版本说明串到一起，并明确要求去读实现与测试。没有
这条路径时，agent 更容易停在简版摘要、漏掉测试行为，或交出 coverage
不足的页面。

基于最近 **3 次** 有效对比实验（已排除 E2B 模板构建取消类 trial）：

| 维度 | Without Skill | With Skill | 结果对比 |
| :--- | :--- | :--- | :--- |
| 通过率 | `0%` | `100%` | 近 3 次有效对照里，without Skill 都保留了至少一项主测试失败，主要表现为漏交 `Limit concurrent work` 示例小节或对应摘要；with Skill 3 次都完整通过。 |
| Agent 执行耗时 | `377.9s` | `465.7s` | With Skill 为了补齐单页交付、源码/测试依据和 manifest 对齐，平均执行时长约增加 `23%`，但换来稳定通过。 |
| Tokens | `1.04M` | `1.42M` | With Skill 的页面覆盖更完整、交叉核对更多，平均总 tokens 约为 Without Skill 的 `1.37x`。 |

## 📁 标准目录结构说明

```text
seed_task/
├── instruction.md
├── task.toml
├── PLAN.json
├── README.md
├── environment/
│   ├── Dockerfile
│   ├── reference_bundle/
│   ├── workspace/
│   └── skills/
├── tests/
└── solution/
```
