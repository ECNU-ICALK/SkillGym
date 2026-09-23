# Monitoring Template

这是面向 `monitoring` 类 skill 的模板。它综合参考 SkillsMP monitoring 类热门 skill 的共性能力：Prometheus 配置、指标采集、inventory 驱动发现、recording rules、alert rules 和服务级监控交付。

## 第一部分：任务设计参考

* **Skill 价值定位**：monitoring 类 Prometheus 配置 skill 的核心价值，是把“能看到一些指标”提升为“能交付一套可运行、可扩展、可验证的监控配置包”。它强调的是采集方式、目标发现、标签整理、规则计算和告警分级，而不是事故处置叙事。
* **Verifier 设计重点**：Verifier 应重点检查 bundle 是否真的完成了采集、发现、规则和告警的交付，而不是只比对 JSON 表面格式。重点应覆盖输入不可变、服务覆盖完整、影子 inventory 不会被带入、目录新增 manifest 后可自动发现、规则可评估以及报告可由当前 bundle 重建。

## 第二部分：示例任务

### 📌 任务元数据

- 任务 ID：`monitoring__harbor-prometheus-bundle`
- 类别：`monitoring`
- 绑定 Skill：`prometheus-configuration`
- 输入数据参考来源：
  - `environment/data/telemetry_reference/prometheus_example_app_README.md`：HTTP 请求计数器与延迟直方图样例  
    【https://raw.githubusercontent.com/brancz/prometheus-example-app/master/README.md】
  - `environment/data/telemetry_reference/prometheus_example_app_pod_monitor.yaml`：inventory 驱动采集配置形态参考  
    【https://raw.githubusercontent.com/brancz/prometheus-example-app/master/manifests/pod-monitor.yaml】
  - `environment/data/telemetry_reference/node_exporter_e2e_output.txt`：Prometheus exposition format 参考  
    【https://raw.githubusercontent.com/prometheus/node_exporter/master/collector/fixtures/e2e-output.txt】
  - `environment/data/docs/harbor_metrics_reference.md`：Harbor 组件监控场景参考  
    【https://goharbor.io/docs/main/administration/metrics/】

### 📊 验证与测试指标（Oracle & Verifier）

- Oracle：按正式流程独立运行并完成交付，结果可直接 100% 通过验证。
- Verifier策略：

主测试
| 测试点 | 验证内容 | 对应skill内化点 |
| :--- | :--- | :--- |
| 输出契约 | 校验 monitoring report JSON 存在、字段完整且覆盖全部合同服务 | 先完成 bundle 交付，再提交结构化结果 |
| 服务级摘要 | 独立重算请求量、错误率、p95 和状态，并与报告对齐 | 指标口径、PromQL 与 histogram 计算 |
| 运行状态 | 校验交付批次下恰好 4 个合同目标可用 | inventory 驱动发现与目标筛选 |
| 规则清单 | 校验 recording rules 与 alert rules 已加载并可评估 | rules 文件加载、命名与表达式正确性 |
| 告警分级 | 校验 page 和 ticket 结果与 policy 一致 | alert rule 设计与分级输出 |

防作弊测试
| 测试点 | 验证内容 |
| :--- | :--- |
| 输入完整性 | `/app/data/` 的输入文件不可修改 |
| 目录新增 manifest | 验证阶段新增一个同批次 inventory 文件后，新目标应被自动发现 |
| 影子目标隔离 | 非合同批次的影子 manifest 不应进入健康目标集合 |
| 报告可重建 | 再次调用环境中的报告脚本时，应能得到与正式输出一致的语义结果 |

### ⚡ Skill 相关性评估

结论：强相关。这个任务里，Skill 的核心价值是把 Prometheus 配置中的发现、标签筛选、recording rules 和 alert rules 工作流标准化，从而降低漏配和误配的概率；without Skill 更容易在目标发现或指标口径上出现动作层面的偏差，导致最终 bundle 不能稳定满足 verifier。

基于最近 **3** 次有效对比实验（均为当前最终版本模板、真实跑到 task-level 的有效轨迹）：

| 维度 | Without Skill | With Skill | 结果对比 |
| :--- | :--- | :--- | :--- |
| 通过率 | `0%` | `100%` | 近 3 次有效对照里，without Skill 都在新增 manifest 发现或辅助目标隔离上留下 verifier 失败；with Skill 3 次都稳定通过 |
| Agent 执行耗时 | `768.4s` | `704.3s` | With Skill 的平均 Agent 耗时降低约 `8.3%`，主要收益来自更快收敛到正确的 Prometheus 工作流 |
| Tokens | `884.8k` | `891.5k` | 两侧 token 基本持平；这一版收益主要体现在动作正确性和通过率，而不是上下文压缩 |

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
│   ├── services/
│   ├── workspace/
│   └── skills/
├── tests/
│   ├── test.sh
│   └── test_outputs.py
└── solution/
    └── solve.sh
```
