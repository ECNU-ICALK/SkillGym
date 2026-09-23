# Project-Management Template

这是面向 `project-management` 类 skill 的模板。它综合参考 SkillsMP project-management 类热门 skill 的共性能力：backlog 梳理、Sprint 承诺规划、容量约束判断、依赖关系识别、风险提炼，以及把多来源项目事实沉淀成发布经理可直接使用的交付物。

## 第一部分：任务设计参考

* **Skill 价值定位**：project-management 类热门 skill 的核心价值，是把零散 backlog、优先级、容量和依赖关系组织成稳定的决策流程。它不应该直接泄露最终答案，而应帮助 solver 更快识别事实源、排序逻辑、容量约束和风险收口方式。
* **Task 目标形态**：任务应落在真实风格的项目规划场景里，例如 Sprint 承诺、发布 cutline、依赖排期、容量平衡或 backlog 分诊。题面应重点交代业务交付合同、约束和禁止事项，把具体工作流更多留给 skill 和 solver 自主识别。
* **Verifier 设计重点**：Verifier 应优先验证 solver 是否完成了真实规划链路和关键动作，而不是只卡格式细节。重点应覆盖权威事实源优先级、分页与明细抓取、依赖闭环、容量重算、分诊结果一致性，以及对 stale export、跳过 live chain、硬编码答案和改输入的防护。

## 第二部分：示例任务

### 📌 任务元数据

- 任务 ID：`project-management__supavisor-sprint-commitment`
- 类别：`project-management`
- 难度：`hard`
- 绑定 Skill：`sprint-planner`
- 输入数据参考来源：
  - `environment/data/backlog_export.csv`：任务内 backlog 导出快照；标题和 issue 语义参考 Supavisor 公开 issue backlog  
    https://github.com/supabase/supavisor/issues  
    https://github.com/supabase/supavisor/issues/236  
    https://github.com/supabase/supavisor/issues/320  
    https://github.com/supabase/supavisor/issues/343  
    https://github.com/supabase/supavisor/issues/204  
    https://github.com/supabase/supavisor/issues/349  
    https://github.com/supabase/supavisor/issues/331  
    https://github.com/supabase/supavisor/issues/314
  - `environment/data/planning_notes/issue_context.md`：任务内 issue 摘要、发布主题和本地化上下文；内容参考同一批 Supavisor issue 页面  
    https://github.com/supabase/supavisor/issues/221  
    https://github.com/supabase/supavisor/issues/209  
    https://github.com/supabase/supavisor/issues/163  
    https://github.com/supabase/supavisor/issues/319  
    https://github.com/supabase/supavisor/issues/830  
    https://github.com/supabase/supavisor/issues/854
  - `environment/data/team_capacity.csv`：任务内团队容量配置；为本模板自定义的本地规划输入，无单独公开来源
  - `environment/data/delivery_policy.yaml`：任务内 Sprint 规则、缓冲和选择约束；为本模板自定义的本地规划输入，无单独公开来源

### 📊 验证与测试指标（Oracle & Verifier）

- Oracle：按正式流程独立运行并完成交付，结果可直接 100% 通过验证。
- Verifier策略：

主测试

| 测试点 | 验证内容 | 对应skill内化点 |
| :--- | :--- | :--- |
| 输出契约 | 检查 CSV / JSON / Markdown 是否存在、可解析，并包含必需字段 | 先理解正式交付物，再组织结构化输出 |
| live backlog 重算 | 从 planning service 重新拉取所有分页和 item detail，核对 triage、承诺集合和拒绝原因 | 识别权威事实源并完成完整数据采集 |
| cutline 与容量一致性 | 重算 must-ship 优先顺序、依赖闭环、story points、QA 与 review 带宽 | 依赖/容量驱动的 Sprint 选择逻辑 |
| 经理摘要语义 | 校验经理更新包含承诺范围、容量瓶颈和最高风险 | 将分析结果沉淀成管理层可执行摘要 |

防作弊测试

| 测试点 | 验证内容 |
| :--- | :--- |
| 真实链路与分页 | 访问日志必须证明 solver 调用了 live planning service，走完全部分页，并拉取了每个 item 的 detail |
| 数据与环境完整性 | `/root/data` 与隐藏 service 文件 hash 不得变化，service 在 verifier 结束时仍健康，且 live-only item 不能被 stale export 漏掉 |

### ⚡ Skill 相关性评估

结论：强相关。这个任务里，Skill 的核心价值是把“stale backlog export + live planning service + 容量/policy 重算”这条项目规划链路标准化，同时把题面刻意弱化掉的分页、detail 抓取和 cutline 决策流程补回来。without Skill 仍然理论可解，但更容易在服务发现、明细抓取、依赖闭环和容量收口上出现行动级失败。

基于最近 **3** 次有效对比实验（均为真正跑到 task-level、存在完整 agent 轨迹；已排除启动失败类 trial）：

| 维度 | Without Skill | With Skill | 结果对比 |
| :--- | :--- | :--- | :--- |
| 通过率 | `0%` | `100%` | 近 3 次有效对照里，without Skill 全部保留至少 1 项 verifier 失败；主要失败是 `capacity_summary` 重算错误，且有 trial 额外暴露出只遍历 live backlog 第 1 页的行动级遗漏。 |
| Agent 执行耗时 | `315.3s` | `274.8s` | With Skill 的规划链路更快收敛，平均 Agent 执行耗时降低约 `12.8%`。 |
| Tokens | `1.35M` | `1.22M` | 按 `input + cache + output` 汇总，With Skill 的平均 tokens 约为 Without Skill 的 `0.91x`，上下文与试错开销更低。 |

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
