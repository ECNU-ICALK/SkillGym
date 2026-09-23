# Knowledge Base Template

这是面向 `knowledge-base` 类 skill 的模板。它综合参考 SkillsMP knowledge-base 类热门 skill 的共性能力：围绕公开资料池、既有知识页外壳和固定交付合同，完成资源审校、替换、补齐和可复跑的页面生成入口。

## 第一部分：任务设计参考

* **Skill 价值定位**：knowledge-base 类 skill 的常见价值，是把公开资料查验、知识页结构、资源筛选规则和交付边界收束成一套可发布的页面更新流程。模板任务适合让 agent 在资料审校、缺口补齐、说明文字收口和输出留档之间做完整交付。
* **Verifier 设计重点**：Verifier 应覆盖正式生成入口、资源选择规则、页面壳保留、审计报告对齐、来源快照一致性和替代输入泛化。重点应放在是否完成了整套资源更新工作流，而不是个别句式或表层排版。

## 第二部分：示例任务

### 📌 任务元数据

- 任务 ID：`knowledge_base__promises_async_await_resource_refresh`
- 类别：`knowledge-base`
- 绑定 Skill：`resource-curator`
- 输入数据参考来源：
  - `environment/knowledge_base/data/candidate_resources.json`：任务内官方参考资源形态参考  
    【https://developer.mozilla.org/en-US/docs/Web/JavaScript/Guide/Using_promises】  
    【https://developer.mozilla.org/en-US/docs/Web/JavaScript/Reference/Statements/async_function】
  - `environment/knowledge_base/data/candidate_resources.json`：任务内文章资源形态参考  
    【https://javascript.info/promise-basics】  
    【https://javascript.info/async-await】  
    【https://dev.to/lydiahallie/javascript-visualized-promises-async-await-5gke】  
    【https://web.dev/articles/async-functions】  
    【https://www.freecodecamp.org/news/avoiding-the-async-await-hell-c77a0fb71c4c/】
  - `environment/knowledge_base/data/candidate_resources.json`：任务内视频与长文资源形态参考  
    【https://www.youtube.com/watch?v=8aGhZQkoFbQ】  
    【https://www.youtube.com/watch?v=DHvZLI7Db8E】  
    【https://www.youtube.com/watch?v=PoRJizFvM7s】  
    【https://github.com/getify/You-Dont-Know-JS/blob/1st-ed/async%20%26%20performance/README.md】
  - `environment/knowledge_base/data/candidate_resources.json`：任务内非目标语言干扰资源形态参考  
    【https://learn.microsoft.com/en-us/dotnet/csharp/asynchronous-programming/】

### 📊 验证与测试指标（Oracle & Verifier）

- Oracle：按正式流程独立运行并完成交付，结果可直接 100% 通过验证。
- Verifier策略：

主测试

| 测试点 | 验证内容 | 对应skill内化点 |
| :--- | :--- | :--- |
| 正式产物生成 | build 入口生成页面、审计报告和 manifest | 资源交付入口收敛 |
| 资源选择合同 | 参考、文章、视频、长文资源的数量、覆盖面和顺序符合合同 | 审校与缺口补齐 |
| 页面壳保留 | frontmatter、概念正文、锚点和资源区外壳继续可用 | 在既有知识页上更新 |
| 审计对齐 | report 与 manifest 能解释从草稿到最终页的资源变化 | 资源审计闭环 |
| alternate fixture 泛化 | 替代 bundle 下资源选择和最终产物会随输入变化 | 可复跑工作流 |

防作弊测试

| 测试点 | 验证内容 |
| :--- | :--- |
| 输入不可变 | `/app/knowledge-base` 哈希不变 |
| 输出白名单 | `/app/output` 顶层只保留规定产物 |
| 残留清理 | 输出中不允许出现占位词、TODO 或 verifier 痕迹 |

### ⚡ Skill 相关性评估

结论：强相关。这个任务里，Skill 的主要价值在于把资源审查、缺口补齐、双句说明写作和可复跑 build 入口串成一条完整交付路径；少了这条路径，agent 更容易停在“链接选对了，但资源说明没写完整”或“当前 bundle 能跑，替代 bundle 的说明文字不跟着更新”的中间态。

基于最近 **3 次** 有效对比实验：

| 维度 | Without Skill | With Skill | 结果对比 |
| :--- | :--- | :--- | :--- |
| 通过率 | `0%` | `100%` | 近 3 次有效对照里，without Skill 都保留了至少一项 verifier 失败；with Skill 3 次都完成了整套交付。 |
| Agent 执行耗时 | `266.7s` | `301.0s` | With Skill 会投入更多时间完成双句说明、审计说明和可复跑 build 收口；without Skill 更早停在不完整交付，所以平均耗时更短但结果未通过。 |
| Tokens | `312,464` | `533,491` | With Skill 会消耗更多上下文去完成来源说明与说明文字收口；without Skill token 更少，但主要因为它更早停在失败状态。 |

## 📁 标准目录结构说明

```text
seed_task/
├── instruction.md
├── task.toml
├── PLAN.json
├── README.md
├── environment/
│   ├── Dockerfile
│   ├── knowledge_base/
│   ├── workspace/
│   └── skills/
├── tests/
└── solution/
```
