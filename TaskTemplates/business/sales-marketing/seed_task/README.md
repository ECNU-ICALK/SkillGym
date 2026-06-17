# SEO Launch Readiness Remediation Template

这是面向 `sales-marketing` 类 SEO skill 的模板。它综合参考 SkillsMP 销售营销类热门 SEO 能力的共性：本地营销站审计、收录准备度诊断、页面规范化修复、站内发现路径修复、sitemap 治理、结构化数据校验和 source-backed 发布说明。

## 第一部分：任务设计参考

* **Skill 价值定位**：SEO 类 skill 的共同价值，不是生成一份泛泛的优化建议，而是把“用 live crawl / audit 找根因、修真实页面、重建站点、再复验”的流程标准化。高质量 skill 应帮助 agent 优先区分历史 snapshot 和当前事实源，并把页面修复与站点级发布门槛联动起来。
* **Verifier 设计重点**：Verifier 应同时验证目标页面最终状态、站点级发现路径、旧 URL 归并、输出合同和防作弊边界。重点包括 live audit 是否通过、target page 是否全部过 gate、关键词覆盖和输出是否一致、输入和隐藏服务是否未被修改，以及 solver 是否真的用了本地 live audit 链路。

## 第二部分：示例任务

### 📌 任务元数据

- 任务 ID：`sales-marketing__seo_launch_readiness_remediation`
- 类别：`sales-marketing`
- 难度：`hard`
- 绑定 Skill：`seo`
- 输入数据参考来源：
  - `environment/data/reference_pages/posthog-product-analytics.json`：任务内产品分析页参考形态；来源于  
    [https://posthog.com/product-analytics](https://posthog.com/product-analytics)
  - `environment/data/reference_pages/posthog-pricing.json`：任务内定价页参考形态；来源于  
    [https://posthog.com/pricing](https://posthog.com/pricing)
  - `environment/data/reference_pages/sentry-error-monitoring.json`：任务内错误监控页参考形态；来源于  
    [https://sentry.io/for/performance/](https://sentry.io/for/performance/)
  - `environment/data/reference_pages/posthog-docs.json`：任务内 docs hub 发现路径参考形态；来源于  
    [https://posthog.com/docs](https://posthog.com/docs)

### 📊 验证与测试指标（Oracle & Verifier）

- Oracle：按正式流程独立运行并完成交付，结果可直接 100% 通过验证。
- Verifier策略：

主测试

| 测试点 | 验证内容 | 对应能力考核点 |
| :--- | :--- | :--- |
| 文件完整且格式正确 | 3 个指定文件存在且能成功解析 | 规范化交付 |
| 目标页面全量覆盖 | 报告和表格完整包含清单中的所有目标页 | 全局审查与覆盖 |
| 通过发布标准审计 | 所有目标页在审计工具中无阻挡项 (blocker) | 真实审计与修复闭环 |
| 页面状态与审计结果一致 | 规范链接(canonical)、标题、标签、H1、结构化数据及站内链接一致 | SEO 修复与复测 |
| 旧链接妥善合并 | 旧链接被正确重定向，且不再出现在网站地图中 | 旧链接与重定向治理 |
| 关键词数据一致 | 关键词覆盖表与审计结果、关键词映射表相符 | 关键词与页面结果校验 |
| 业务总结通俗易懂 | 摘要包含修复概况、潜在风险、页面路径和发布建议 | 面向业务团队的汇报能力 |

防作弊测试

| 测试点 | 验证内容 |
| :--- | :--- |
| 真实审计痕迹 | 操作者在最终验证前，切实调用了逐页审查、自动评估等审计流程 |
| 原始输入未被篡改 | `seo_inputs/` 文件夹未被修改 |
| 隐藏服务未被篡改 | 本地 `seo-audit` 服务未被修改 |
| 预置文件未被篡改 | 考核捆绑的 skill 文件内容未被修改 |
| 输出内容无作假 | 结果中没有无意义的占位符、代办标记 (todo) 或伪造验证的痕迹 |

### ⚡ Skill 相关性评估

结论：强相关。这个任务里，Skill 的核心价值是把“先查 live gate、再逐页复验、再修发现路径和旧 URL、最后重跑 build 和 audit”的工作流标准化，从而明显降低遗漏收录阻塞和误用旧 snapshot 的概率。

基于最近 **3** 次有效对比实验（均为真正跑到 task-level、存在完整 agent 轨迹；已排除启动失败类 trial）：

| 维度 | Without Skill | With Skill | 结果对比 |
| :--- | :--- | :--- | :--- |
| 通过率 | `0/3` | `3/3` | `without_skill` 三次都至少保留 1 项 verifier 失败；代表性失败是没走 live release gate，导致 live blockers 仍存在，属于行动级失败。 |
| Agent 执行耗时 | `356.9s` | `371.5s` | 这组任务的主要分离信号不是更短耗时，而是 `with_skill` 更稳定走完整 live SEO workflow；`without_skill` 往往更早停在不完整修复。 |
| Tokens | `0.50M` | `0.98M` | `without_skill` 通常 token 更少，因为它经常少做 live 诊断和复验动作；这里更关键的是完成率和工作流遵循度，而不是省 token。 |

## 📁 标准目录结构说明

```text
seed_task/
├── instruction.md
├── task.toml
├── PLAN.json
├── README.md
├── environment/
│   ├── Dockerfile
│   ├── bin/
│   ├── data/
│   ├── hidden-service-src/
│   └── skills/
├── tests/
│   ├── conftest.py
│   ├── test.sh
│   ├── test_outputs.py
│   └── test_guardrails.py
└── solution/
    ├── solve.py
    └── solve.sh
```
