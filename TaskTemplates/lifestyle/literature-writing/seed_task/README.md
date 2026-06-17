# Literature-Writing Template

这是面向 `literature-writing` 类 skill 的模板。它综合参考 SkillsMP literature-writing 类热门 skill 的共性能力：围绕公开材料收束写作边界、对齐语气、压掉空泛营销话术、建立来源追踪，并把一组分发场景收口成可交付的文案包。

## 第一部分：任务设计参考

* **Skill 价值定位**：literature-writing 类热门 skill 的核心价值，不只是“写一段更顺的文字”，而是把语气、信息优先级、来源边界、自检口径和交付结构一起拉齐。模板任务应让 skill 承接素材取舍、语气迁移、风险措辞收口和最终自查，而题面只保留业务合同和禁止事项。
* **Verifier 设计重点**：Verifier 应优先验证 solver 是否沿本地素材链路完成了完整写作动作，而不只看文案表层是否流畅。重点应覆盖事实来源、术语与禁写项、交付结构、局部场景差异、审校闭环，以及对跳过本地服务、查看隐藏实现、硬编码输出和改输入的防护。

## 第二部分：示例任务

### 📌 任务元数据

- 任务 ID：`literature_writing__zed_parallel_agents_launch_copy`
- 类别：`literature-writing`
- 绑定 Skill：`brand-writer`
- 输入数据参考来源：
  - `environment/data/source_packets/ai_overview.json`：任务内 AI 总览资料包；设计形态参考 Zed AI overview documentation  
    https://raw.githubusercontent.com/zed-industries/zed/main/docs/src/ai/overview.md
  - `environment/data/source_packets/parallel_agents_blog.json`：任务内 Parallel Agents 上线资料包；设计形态参考 Zed blog post  
    https://zed.dev/blog/parallel-agents
  - `environment/data/source_packets/parallel_agents_docs.json`：任务内 Parallel Agents 文档资料包；设计形态参考 Zed docs page  
    https://raw.githubusercontent.com/zed-industries/zed/main/docs/src/ai/parallel-agents.md
  - `environment/data/source_packets/codex_in_zed.json`：任务内 Codex 集成资料包；设计形态参考 Zed blog post  
    https://zed.dev/blog/codex-is-live-in-zed
  - `environment/data/source_packets/repo_readme.json`：任务内项目背景资料包；设计形态参考 zed repository README  
    https://raw.githubusercontent.com/zed-industries/zed/main/README.md

### 📊 验证与测试指标（Oracle & Verifier）

- Oracle：按正式流程独立运行并完成交付，结果可直接 100% 通过验证。
- Verifier策略：

主测试

| 测试点 | 验证内容 | 对应skill内化点 |
| :--- | :--- | :--- |
| 输出契约 | 校验单一 JSON 产物存在、可解析，且完整覆盖 5 个 deliverable 与质量报告 | 先理解正式交付合同，再组织最终文案包 |
| 题材覆盖 | 校验 Parallel Agents、Threads Sidebar、Codex/ACP、open source/Rust/GPU 等主题得到覆盖 | 信息优先级与事实取舍 |
| 来源追踪 | 校验 `source_trace` 与 `fact_ledger` 使用允许来源，并覆盖多份 source packet | 事实来源登记与可审计写作 |
| 风格与禁写项 | 校验禁用表达被移除，且本地质量闸口评分达到阈值 | 品牌语气迁移与风险措辞收口 |

防作弊测试

| 测试点 | 验证内容 |
| :--- | :--- |
| 本地内容服务链路 | 要求 solver 在 verifier 前访问 source index、全部文档、禁写项、拒稿记录和质量闸口 |
| 环境完整性 | 禁止修改工作区输入、本地数据包与隐藏服务，并阻止查看隐藏实现 |

### ⚡ Skill 相关性评估

结论：强相关。这个任务里，Skill 的核心价值是把“公开资料整理 + 语气对齐 + 禁写项收口 + 事实映射 + 本地质量闸口”这条开发者向写作链路标准化，从而降低 solver 在素材边界、措辞风险和终稿自查上的试错成本。without Skill 理论上可解，但更容易在资料覆盖、事实映射、风格收敛或本地质量闸口调用上漏动作。

基于最近 **3 次** 有效对比实验：

| 维度 | Without Skill | With Skill | 结果对比 |
| :--- | :--- | :--- | :--- |
| 通过率 | `0% (0/3)` | `66.7% (2/3)` | without Skill 的 3 次有效 trial 都留下了动作级失败；with Skill 在同版任务上有 2 次完整通过。 |
| Agent 执行耗时 | `225.7s` | `248.0s` | with Skill 平均耗时更高，主要来自更完整的来源采集、语气对齐和本地闸口回填动作。 |
| Tokens | `218.4k` | `382.7k` | with Skill 的上下文与自检开销更高，但换来了更高的 task-level 通过率。 |

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
