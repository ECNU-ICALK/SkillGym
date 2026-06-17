# System Admin Template

这是面向 `system-admin` 类 skill 的模板。它综合参考 SkillsMP system-admin 类热门 skill 的共性能力：交互式终端控制、隔离会话管理、运行时状态检查、审计留痕、live recovery session 接管和发布后复核。

## 第一部分：任务设计参考

* **Skill 价值定位**：system-admin 类热门 skill 的核心价值，是把“能登录进去”提升为“能沿着正确运维链路完成恢复并留下可复核证据”。对于 `tmux` 这类 skill，重点不是单次命令执行，而是隔离交互会话、驱动 TTY-only 控制台、观察运行中状态并在合适时机继续动作。
* **Verifier 设计重点**：Verifier 应验证 solver 是否真的续接了既有控制链路、是否由同一条已 staged 的 live session 完成关键动作，以及是否保留了真实输入与控制台实现不变。重点应覆盖发布产物重算、审计轨迹、会话身份一致性、环境完整性和防止手写结果、替代链路、篡改输入或直接改控制台规避。

## 第二部分：示例任务

### 📌 任务元数据

- 任务 ID：`system-admin__debian-security-digest-recovery`
- 类别：`system-admin`
- 绑定 Skill：`tmux`
- 数据来源：`snapshot.debian.org`

### 📊 验证与测试指标（Oracle & Verifier）

- Oracle：按正式流程独立运行并完成交付，结果可直接 100% 通过验证。
- Verifier策略：

主测试
| 测试点 | 验证内容 | 对应skill内化点 |
| :--- | :--- | :--- |
| 输出契约 | 校验 recovery report JSON 是否存在、字段完整且值与 Debian snapshot 重算结果一致 | 先完成真实恢复，再交付结构化结果 |
| 已发布产物 | 校验 published digest artifact 存在且 sha256 与报告一致 | 不能只写结果，必须完成真实发布 |
| 发布回执一致性 | receipt 与最终输出、published artifact 路径保持一致 | 保持运行链路与交付合同对齐 |
| 会话审计 | 审计日志中必须证明 bootstrap 预置的 staged live session 完成 publish 与 write report | 发现并接管正确的 live session，而不是重开替代链路 |

防作弊测试
| 测试点 | 验证内容 |
| :--- | :--- |
| 输入与控制台完整性 | 上游 snapshot 数据、incident 文件和控制台实现不可修改 |
| 运行后健康状态 | pipeline 必须为 active、stale lock 清除、published=true，且发布、写报告与 staged session owner 身份一致 |

### ⚡ Skill 相关性评估

结论：强相关。这个任务里，Skill 的核心价值是把 live tmux 会话发现、pane capture 和安全 send-keys 这些交互式终端动作标准化，从而让 solver 能接管已经 staged 且拥有发布权的那条 live recovery session；without Skill 更容易停留在重开新会话、找错会话或手写结果的错误路径上。

基于最近 **3 次** 有效对比实验（均为真正跑到 task-level、存在完整 agent 轨迹；已排除启动失败类 trial）：

| 维度 | Without Skill | With Skill | 结果对比 |
| :--- | :--- | :--- | :--- |
| 通过率 | `0/3` | `3/3` | 近 3 次有效对照里，without Skill 都没有完成 staged session 接管；其中 2 次 clean reward=0 明确失败在错误 session 复建/发布，另 1 次旧 wrapper trial 虽 reward 文件缺失，但同样在主测试里暴露了重复 rebuild 的行为级失败。 |
| Agent 执行耗时 | `555.4s` | `171.5s` | With Skill 的诊断与收敛更快，平均 Agent 耗时降低约 `69.1%`。 |
| Tokens | `2.91M` | `0.50M` | Without Skill 的上下文与试错开销约为 With Skill 的 `5.79x`。 |

## 📁 标准目录结构说明

```text
seed_task/
├── instruction.md
├── task.toml
├── PLAN.json
├── README.md
├── environment/
│   ├── Dockerfile
│   ├── console/
│   ├── data/
│   ├── runtime_seed/
│   └── skills/
│       └── tmux/
├── tests/
│   ├── test.sh
│   └── test_outputs.py
└── solution/
    └── solve.sh
```
