# Code Quality Template

这是面向 `code-quality` 类 skill 的模板。它综合参考 SkillsMP `code-quality` 分类高 star skill 的共性能力：把构建、类型、风格、测试、安全扫描和 diff 审查串成一条可复跑的验证闭环，并把最终判断收口为结构化交付件。

## 第一部分：任务设计参考

* **Skill 价值定位**：`code-quality` 类热门 skill 的共同价值，在于帮助 Agent 用稳定的验证顺序覆盖 build、type、lint、test、security scan 和 diff review，并避免停留在单点通过。高质量 skill 往往会强化当前会话命令证据、阻断项归因和最终 gate 决策的一致性。
* **Verifier 设计重点**：verifier 既要确认 build / type / lint / test 等常规门禁被正确执行，也要确认安全扫描和 diff 审查没有被省略或弱化。对照实验应重点观察 with_skill 是否更容易补齐完整验证闭环。

## 第二部分：示例任务

### 📌 任务元数据

- 任务 ID：`code-quality__toolchain-release-readiness-audit`
- 类别：`code-quality`
- 绑定 Skill：`verification-loop`
- 输入数据参考来源：
  - `environment/workspace/data/npm/typescript_latest.json`：任务内 TypeScript npm latest 快照；数据形态参考 npm Registry latest package document  
    【https://registry.npmjs.org/typescript/latest】
  - `environment/workspace/data/npm/eslint_latest.json`：任务内 ESLint npm latest 快照；数据形态参考 npm Registry latest package document  
    【https://registry.npmjs.org/eslint/latest】
  - `environment/workspace/data/npm/prettier_latest.json`：任务内 Prettier npm latest 快照；数据形态参考 npm Registry latest package document  
    【https://registry.npmjs.org/prettier/latest】
  - `environment/workspace/data/github/typescript_releases.json`：任务内 TypeScript release window 快照；数据形态参考 GitHub Releases API  
    【https://api.github.com/repos/microsoft/TypeScript/releases?per_page=5】
  - `environment/workspace/data/github/eslint_releases.json`：任务内 ESLint release window 快照；数据形态参考 GitHub Releases API  
    【https://api.github.com/repos/eslint/eslint/releases?per_page=5】
  - `environment/workspace/data/github/prettier_releases.json`：任务内 Prettier release window 快照；数据形态参考 GitHub Releases API  
    【https://api.github.com/repos/prettier/prettier/releases?per_page=5】

### 📊 验证与测试指标（Oracle & Verifier）

- Oracle：按正式流程独立运行并完成交付，结果可直接 100% 通过验证。
- Verifier 策略：

主测试

| 测试点 | 验证内容 | 对应 skill 内化点 |
| :--- | :--- | :--- |
| Report contract | 输出 JSON 结构、字段和 gate 顺序正确 | 先满足交付合同 |
| Core verification gates | `buildability` / `type_safety` / `style_checks` / `test_suite` 全部为 `pass` | 按固定验证顺序跑通常规质量门禁 |
| Security scan | `security_scan` 必须基于当前会话扫描命令得出失败结论 | 命中安全扫描相位 |
| Diff review | `diff_review` 必须基于当前 tracked diff 得出失败结论 | 命中 diff 审查相位 |
| Decision integrity | `release_ready` 与 `blocking_issues` 和 gate 结果一致 | 最终决策与证据闭环 |
| Command parity | verifier 重跑命令后，结果与报告中的 gate 判断一致 | 命令证据与报告一致 |

防作弊测试

| 测试点 | 验证内容 |
| :--- | :--- |
| Input immutability | `environment/workspace/data` 不可修改 |
| Candidate diff immutability | 仓库原始 tracked diff 不可修改 |

### ⚡ Skill 相关性评估

结论：强相关。这个任务的关键，在于 Agent 是否会继续走到本地 `verification-loop` skill 对应的 `security_scan` 与 `diff_review` 相位，并把最终 release 判定建立在完整 gate 证据上，而不只停在 build / type / lint / test 成功这一层。

基于最近 **3** 次有效对比实验（均为真正跑到 task-level、存在完整 agent 轨迹；已排除启动失败类 trial）：

| 维度 | Without Skill | With Skill | 结果对比 |
| :--- | :--- | :--- | :--- |
| 通过率 | `0%` | `100%` | without_skill 三次都把最终决策或 `security_scan` / `diff_review` 动作链路做浅了；with_skill 三次都先发现本地 skill，再按验证闭环完成审计 |
| Agent 执行耗时 | `160.1s` | `208.7s` | With Skill 会额外读取本地 skill 并补齐安全扫描与 diff 审查，所以平均耗时更高，但换来了稳定通过 |
| Tokens | `280864` | `348683` | With Skill 需要额外上下文去读取本地 skill 和执行完整闭环，平均 token 约为 without_skill 的 `1.24x` |

## 📁 标准目录结构说明

```text
seed_task/
├── instruction.md
├── task.toml
├── PLAN.json
├── README.md
├── environment/
│   ├── Dockerfile
│   ├── package_base/
│   ├── skills/
│   └── workspace/
├── tests/
└── solution/
```
