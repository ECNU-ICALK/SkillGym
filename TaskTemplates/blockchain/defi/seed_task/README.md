# DeFi Template

这是面向 `defi` 类 skill 的模板。它综合参考 SkillsMP `defi` 类热门 skill 的共性能力：协议搭建、流动性池机制、奖励分发、治理投票、参数变更执行，以及把链上动作整理成可核对的本地交付物。

## 第一部分：任务设计参考

* **Skill 价值定位**：`defi` 类热门 skill 的共同价值，在于把协议组件拆成清晰的合约边界、状态更新规则和操作顺序。对于这类 skill，重点是帮助 Agent 快速落下 staking、AMM、governance 这几类常见协议骨架，并把关键动作串成一条可复跑的工作流。
* **Verifier 设计重点**：Verifier 应优先检查链上动作是否齐全、合约状态演化是否一致、奖励与治理逻辑是否满足约束，以及报告是否和当前回放结果对齐。对这类任务，动作级行为校验、输入不可改、回放重跑一致性，通常比格式细节更重要。

## 第二部分：示例任务

### 📌 任务元数据

- 任务 ID：`defi__governance_liquidity_launch`
- 类别：`defi`
- 绑定 Skill：`defi-protocol-templates`
- 输入数据参考来源：
  - `environment/data/spec/token_catalog.json`：任务内资产元数据；设计形态参考 Uniswap token metadata  
    <https://github.com/Uniswap/default-token-list/blob/main/src/tokens/mainnet.json>
  - `environment/data/spec/launch_plan.yaml`：任务内协议参数包；参数口径参考 Uniswap V2 pool mechanics  
    <https://docs.uniswap.org/contracts/v2/concepts/protocol-overview/how-uniswap-works>
  - `environment/data/spec/reward_program.csv`：任务内激励排期；设计口径参考 Uniswap liquidity mining program  
    <https://blog.uniswap.org/introducing-uni>
  - `environment/data/spec/reference/staking_rewards_notes.md`：任务内奖励累计说明；设计口径参考 Synthetix StakingRewards  
    <https://github.com/Synthetixio/synthetix/blob/develop/contracts/StakingRewards.sol>
  - `environment/data/spec/reference/erc20votes_notes.md`：任务内投票权 checkpoint 说明；直接来源于  
    <https://docs.openzeppelin.com/contracts/5.x/api/token/erc20#ERC20Votes>
  - `environment/data/spec/scenario_replay.json`：任务内回放序列；由模板根据上述公开材料整理生成，无单独公开下载链接

### 📊 验证与测试指标（Oracle & Verifier）

- Oracle：按正式流程独立运行并完成交付，结果可直接 100% 通过验证。
- Verifier策略：

主测试

| 测试点 | 验证内容 | 对应skill内化点 |
| :--- | :--- | :--- |
| 输出规范 | 检查 `launch_report.json` 文件是否存在、格式是否可解析，并且包含规定的核心字段与基础数据结构 | 掌握正式交付规范 |
| 协议行为还原 | 独立部署当前智能合约并完整模拟该业务场景，核对流动性提供者（LP）、奖励发放、投票及治理操作的最终结果 | 协议组件实现与操作流程调度 |
| AMM 与奖励规则 | 检查流动性份额、代币兑换结果、奖励累加情况、资金限额以及退出机制 | 常见 DeFi 状态更新规则 |
| 治理执行流程 | 检查委托（delegation）、提案（proposal）、投票（vote）、进入队列（queue）、执行（execute）等环节以及参数更新的结果 | 投票权与治理流程 |
| 报告一致性 | 校验报告中的固定字段、操作步骤顺序以及参与者（actor）范围，确认其与全新模拟运行的结果保持完全一致 | 模拟结果整理与生成规范报告 |

防作弊测试

| 测试点 | 验证内容 |
| :--- | :--- |
| 输入防篡改 | 确保 `spec/` 目录下的输入文件不可修改 |
| 历史报告防护 | 清空或修改旧有报告后重新执行程序，确认系统会根据当前的实际运行结果重新生成准确的报告 |
| 参与者动态扩展 | 在不修改公开接口和已有操作类型的前提下，增加额外的参与者（actor），检查运行过程与结果汇总是否依然严格由输入数据驱动 |
| 权限与异常拦截 | 检查未授权的参数修改、投票权不足的提案、未到期强制执行等违规操作是否能被正确拦截 |
| 奖励发放上限 | 检查已被提取（claim）的奖励总额不会超过系统已注入的奖励总数 |

### ⚡ Skill 相关性评估

结论：强相关。这个任务里，Skill 的核心价值是把 staking、AMM、governance 三类常见协议模板压缩成一套可直接落地的本地实现路线；without Skill 更容易在 LP 份额、reward rollover、vote checkpoint、queue/execute 这些动作层细节上掉分。

基于最近 **3** 次有效对比实验（均为真正跑到 task-level、存在完整 agent 轨迹；已排除启动失败类 trial）：

| 维度 | Without Skill | With Skill | 结果对比 |
| :--- | :--- | :--- | :--- |
| 通过率 | `0%` | `100%` | 最近 3 次有效对照里，without Skill 都保留了 verifier 失败项；with Skill 3 次均完成全部 13 个测试点 |
| Agent 执行耗时 | `328.0s` | `315.6s` | With Skill 的协议拼装和回放收敛更快，平均 Agent 耗时降低约 `3.8%` |
| Tokens | `763,144` | `746,554` | Without Skill 的上下文与试错开销约为 With Skill 的 `1.02x`，且失败集中在协议行为探针与状态约束上 |

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
│   │   └── spec/
│   ├── workspace/
│   └── skills/
├── tests/
└── solution/
```
