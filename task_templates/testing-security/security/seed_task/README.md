# Security Template

这是面向 `security` 类 skill 的模板。它综合参考 SkillsMP 安全类热门 skill 的共性能力：认证与授权检查、输入校验确认、租户范围约束、限流与配额验证，以及把服务实现问题收口成可运行的交付任务。

## 第一部分：任务设计参考

* **Skill 价值定位**：security 类热门 skill 的共同价值，在于帮助 Agent 把认证、授权、输入校验、敏感导出和错误处理串成一条完整检查链路。模板任务应把题面重心放在交付合同、业务边界和禁止事项上，让具体排查和实现路径更多留给 skill 与 solver 自主识别。
* **Verifier 设计重点**：Verifier 应优先检查 solver 是否沿服务链路完成鉴权、授权、输入校验、导出约束和错误语义补齐，并验证行为在替身数据上仍然成立。防作弊点应覆盖只对样例特判、只改少数响应、绕过本地数据源、误改输入快照和删除安全控制。

## 第二部分：示例任务

### 📌 任务元数据

- 任务 ID：`security__tenant-vulnerability-advisory-api`
- 类别：`security`
- 绑定 Skill：`security-review`
- 输入数据参考来源：
  - `environment/workspace/data/nvd_cves.ndjson`：任务内 CVE 快照；字段形态参考 NVD CVE API 2.0  
    https://nvd.nist.gov/developers/vulnerabilities  
    https://services.nvd.nist.gov/rest/json/cves/2.0?cveId=CVE-2024-3094
  - `environment/workspace/data/kev_catalog.json`：任务内 exploited-vulnerability 目录；数据形态参考 CISA KEV catalog  
    https://www.cisa.gov/known-exploited-vulnerabilities-catalog  
    https://www.cisa.gov/sites/default/files/feeds/known_exploited_vulnerabilities.json
  - `environment/workspace/data/epss_scores.csv`：任务内 exploitability 分数；数据形态参考 FIRST EPSS  
    https://www.first.org/epss/data_stats  
    https://epss.empiricalsecurity.com/epss_scores-current.csv.gz
  - `environment/workspace/data/tenants.json`：任务内租户、scope、配额与导出约束；为本模板自定义的本地输入，无单独公开来源
  - `environment/workspace/data/export_jobs.json`：任务内导出任务初始状态；为本模板自定义的本地输入，无单独公开来源

### 📊 验证与测试指标（Oracle & Verifier）

- Oracle：按正式流程独立运行并完成交付，结果可直接 100% 通过验证。
- Verifier策略：

主测试

| 测试点 | 验证内容 | 对应skill内化点 |
| :--- | :--- | :--- |
| 列表与分页 | 检查租户范围、筛选、排序和分页稳定性 | 认证后先看可见数据面，再确认数据边界 |
| 详情与批量 | 检查 detail / bulk 的输入校验、scope 与错误语义 | 输入校验、授权与批量接口限制 |
| 导出任务 | 检查 analyst-only 导出授权、行数上限和 CSV 产物 | 敏感导出控制与最小权限 |
| 限流语义 | 检查 401 / 403 / 429 与限流头 | 安全错误语义与资源保护 |

防作弊测试

| 测试点 | 验证内容 |
| :--- | :--- |
| 替身数据泛化 | 改动 advisory / KEV / EPSS 子集后，服务行为仍按数据源重算 |
| 输入文件完整性 | data 目录 hash 不能变化 |
| 结构完整性 | server、service 和 tests 入口保持存在 |

### ⚡ Skill 相关性评估

结论：强相关。这个任务里，Skill 的核心价值在于把认证、授权、输入校验、批量限制、导出权限和只读输入/运行态边界串成一条连续检查链路；without-skill 虽然能补齐大部分接口，但最近 3 次有效对照都在导出权限动作链路上遗留主测试失败。

基于最近 **3** 次有效对比实验（均为真正跑到 task-level、存在完整 agent 轨迹；已排除启动失败类 trial）：

| 维度 | Without Skill | With Skill | 结果对比 |
| :--- | :--- | :--- | :--- |
| 通过率 | `0%` | `100%` | 近 3 次有效对照里，without Skill 都保留了 `test_export_jobs_create_csv_and_enforce_limits` 失败，问题集中在 analyst-only 导出权限与导出约束动作链路。 |
| Agent 执行耗时 | `591.5s` | `613.6s` | 本轮样本里耗时接近，With Skill 未表现出稳定耗时优势，平均约高 `3.7%`，但最终交付成功率更稳定。 |
| Tokens | `1.18M` | `1.20M` | 两组 token 基本同量级，With Skill 略高约 `1.5%`；主要收益体现在减少关键安全动作遗漏，而不是压低上下文消耗。 |

## 📁 标准目录结构说明

```text
seed_task/
├── instruction.md
├── task.toml
├── PLAN.json
├── README.md
├── environment/
│   ├── Dockerfile
│   ├── workspace/
│   └── skills/
├── tests/
└── solution/
```
