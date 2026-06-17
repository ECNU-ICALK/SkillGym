# LLM-AI Template

这是面向 LLM-AI 类 skill 的模板。它综合参考 SkillsMP LLM-AI 类热门 skill 的共性能力：多路径 AI 工作流诊断、sandbox/live 一致性、结构化输出合同、回归测试闭环、以及通过自动化测试约束 AI 自己引入的盲点。

## 第一部分：任务设计参考

* **Skill 价值定位**：LLM-AI 类热门 skill 的共性价值，通常不是简单调用模型，而是把提示、适配层、结构化输出、数据规则和运行时回归控制成一个稳定系统。对 solver 的要求也因此不是“让接口返回内容”，而是恢复一条真实 AI 辅助链路在多模式、多输入和异常场景下的稳定
* **Verifier 设计重点**：Verifier 应重点检查多运行模式合同一致性、结构化输出字段稳定性、批处理完整性、错误语义、隐藏下游链路真实性以及对新样本的泛化。防作弊应覆盖硬编码固定样本、绕过真实 provider、只修单一路径和通过篡改输入数据来躲避回归。

## 第二部分：示例任务

### 📌 任务元数据

- 任务 ID：`ai-ticket-triage-api-regression-repair`
- 类别：`llm-ai`
- 难度：`hard`
- 绑定 Skill：`ai-regression-testing`
- 输入数据参考来源：
  - `environment/workspace/data/tickets/banking77_curated.jsonl`：任务内银行客服工单文本；设计形态参考 PolyAI Banking77  
    https://huggingface.co/datasets/PolyAI/banking77
  - `environment/workspace/data/tickets/clinc150_oos_curated.jsonl`：任务内 out-of-scope 工单文本；设计形态参考 CLINC150  
    https://archive.ics.uci.edu/dataset/570/clinc150
  - `environment/workspace/data/contracts/structured_output_schema.json`：结构化输出合同形态参考 OpenAI Structured Outputs  
    https://platform.openai.com/docs/guides/structured-outputs
  - `environment/workspace/data/contracts/provider_message_examples.json`：provider 消息形态参考 Anthropic Messages API  
    https://docs.anthropic.com/en/api/messages

### 📊 验证与测试指标（Oracle & Verifier）

- Oracle：按正式流程独立运行并完成交付，结果可直接 100% 通过验证。
- Verifier 策略：

主测试

| 测试点 | 验证内容 | 对应 skill 内化点 |
| :--- | :--- | :--- |
| 模式一致性 | 校验 sandbox/live 在 out-of-scope 工单上的业务合同一致 | sandbox/live parity |
| 批处理完整性 | 校验 batch 不静默丢项，且正确保留 retryable 和 needs_human | regression coverage on non-happy paths |
| 结构化输出稳定性 | 校验无证据场景仍返回稳定 review 结果 | structured outputs and null/empty handling |
| 错误语义 | 校验缺失 ticket 返回机器可读 not_found | action-oriented error contracts |

防作弊测试

| 测试点 | 验证内容 |
| :--- | :--- |
| 变体数据泛化 | 新增样本后，分类与 review 语义仍成立 |
| 下游真实性 | live 模式必须实际调用 hidden provider simulator |
| 输入完整性 | 输入数据哈希必须保持不变 |

### ⚡ Skill 相关性评估

结论：强相关。这个任务的核心不是单纯把接口“修到能返回”，而是让 solver 在 `sandbox/live` 多路径、structured output、provider 不可信回包、批量完整性和回归闭环之间建立稳定诊断顺序。`ai-regression-testing` 的价值主要体现在两点：一是把“先跑回归、再看代码、再补最小回归测试”的工作流标准化，二是把 solver 的注意力稳定拉回到沙盒事实、错误语义和行为合同，而不是只修表面 happy path。

基于最近 **3** 次有效对比实验（均为真正跑到 task-level、存在完整 agent 轨迹；已排除启动失败类 trial）：

| 维度 | Without Skill | With Skill | 结果对比 |
| :--- | :--- | :--- | :--- |
| 通过率 | `0% (0/3)` | `66.7% (2/3)` | 最近 3 次有效对照里，`without_skill` 始终未能通过；`with_skill` 有 2 次通过，说明绑定 skill 对收敛有明显帮助，但当前模板仍保留了少量模型随机性。 |
| Agent 执行耗时 | `407.4s` | `340.9s` | `with_skill` 平均 Agent 执行耗时约降低 `16.4%`，诊断和回归收敛更快。 |
| Tokens | `1.61M` | `1.36M` | 这里按 `input + cache + output` 口径统计平均总 tokens；`without_skill` 约为 `with_skill` 的 `1.19x`。 |

补充说明：

- Oracle 已在 E2B 于 `2026-05-01` 验证通过，当前最终版本的参考修复仍能稳定通过全量 verifier。
- 最近 3 次有效对照分别使用隔离的 `iter21`、`iter22`、`iter23` runtime / jobs 目录；with/without 的唯一区别仍然只来自 `environment/skills/` 及对应复制逻辑。
- `without_skill` 的失败不只是格式问题。失败主要落在 provider 不可信回包下的行动层修复不足，以及没有遵循绑定 skill 的回归工作流轨迹要求。

## 📁 标准目录结构说明

```text
模板任务：
├── instruction.md
├── task.toml
├── PLAN.json
├── README.md
├── environment/
│   ├── Dockerfile
│   ├── workspace/
│   ├── provider-sim/
│   └── skills/
├── tests/
└── solution/
```
