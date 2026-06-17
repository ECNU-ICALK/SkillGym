# Productivity Tools Template

这是面向 `productivity-tools` 类 skill 的模板。它综合参考 SkillsMP `productivity-tools` 类热门 skill 的共性能力：围绕公开来源、固定交付合同、可重复执行的本地工作流和明确的结果留档，完成一次带状态的日常效率任务。

## 第一部分：任务设计参考

* **Skill 价值定位**：productivity-tools 类 skill 的常见价值，是把一组分散的操作步骤收束成可重复执行的工作流，让 agent 能更快完成来源接入、状态管理、交付生成和重复运行收口。模板任务适合要求 agent 在已有入口、已有草稿和已有合同之上完成整套交付。
* **Verifier 设计重点**：Verifier 应覆盖正式生成入口、输入来源解析、状态变化、输出留档和替代输入泛化。重点应放在 agent 是否走完完整工作流，而不是个别表层格式。

## 第二部分：示例任务

### 📌 任务元数据

- 任务 ID：`productivity_tools__engineering_release_watch_digest`
- 类别：`productivity-tools`
- 绑定 Skill：`blogwatcher`
- 输入数据参考来源：
  - `environment/release_watch/data/mirror/uv-releases/feed.atom`：任务内 Python 工具链更新源形态参考  
    【https://github.com/astral-sh/uv/releases.atom】
  - `environment/release_watch/data/mirror/nodejs-blog/feed.xml`：任务内运行时博客更新源形态参考  
    【https://nodejs.org/en/feed/blog.xml】
  - `environment/release_watch/data/mirror/github-blog-changelog/feed.xml`：任务内工程平台变更源形态参考  
    【https://github.blog/changelog/feed/】
  - `environment/release_watch/data/mirror/typescript-releases/feed.atom`：任务内语言工具发布源形态参考  
    【https://github.com/microsoft/typescript/releases.atom】

### 📊 验证与测试指标（Oracle & Verifier）

- Oracle：按正式流程独立运行并完成交付，结果可直接 100% 通过验证。
- Verifier策略：

主测试

| 测试点 | 验证内容 | 对应skill内化点 |
| :--- | :--- | :--- |
| 正式产物生成 | build 入口生成 digest、inventory 和 manifest | 工作流入口收敛 |
| 来源解析 | source registry、feed 发现和 RSS/Atom 解析结果符合本地镜像 | 来源接入与扫描 |
| 未读交付 | digest 只写当前未读项，并按优先级分组输出 | 未读项审阅 |
| 重复运行 | 相同输入下第二次运行不再重复交付同一批文章 | 已读状态维护 |
| alternate fixture 泛化 | 变更 feed 快照后，digest 与 manifest 跟随输入变化 | 可重复执行 |

防作弊测试

| 测试点 | 验证内容 |
| :--- | :--- |
| 输入不可变 | `/app/release-watch` 哈希不变 |
| 输出白名单 | `/app/output` 顶层只保留规定产物 |
| 残留清理 | 输出中不允许出现占位词或 verifier 痕迹 |

### ⚡ Skill 相关性评估

结论：强相关。这个任务里，Skill 的核心价值是把来源接入、扫描、未读项处理和重复运行状态整理成一条完整操作链；少了这条链，agent 更容易停在“只写出一版摘要”或“只做出一次扫描结果”的中间态。

基于最近 **3 次** 有效对比实验：

| 维度 | Without Skill | With Skill | 结果对比 |
| :--- | :--- | :--- | :--- |
| 通过率 | `0.0%` | `100.0%` | 近 3 次有效对照里，without Skill 都在 build 阶段 CLI 审计留档上留下缺口，常见缺项是新增来源 add 动作或 delivered-item read 动作，因此至少保留 1 项 verifier 失败。 |
| Agent 执行耗时 | `346.5s` | `519.6s` | With Skill 更稳定地走完整个来源接入、review reopen、扫描、交付和审计链路；without Skill 往往更早停在局部完成态，所以耗时更短但仍失败。 |
| Tokens | `379816` | `834284` | With Skill 在当前模板上会把完整工作流走完，token 开销更高；without Skill 常在审计动作补齐前结束，token 更低但完成度不足。 |

## 📁 标准目录结构说明

```text
seed_task/
├── instruction.md
├── task.toml
├── PLAN.json
├── README.md
├── environment/
│   ├── Dockerfile
│   ├── release_watch/
│   ├── workspace/
│   └── skills/
├── tests/
└── solution/
```
