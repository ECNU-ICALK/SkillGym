# Smart-Contracts Template

这是面向 `smart-contracts` 类 skill 的模板。它综合参考 SkillsMP `smart-contracts` 类热门 skill 的共性能力：ERC-20 / ERC-4626 兼容性审阅、非标准 token 行为识别、协议侧防护措施核对，以及基于证据的结构化上线结论。

## 第一部分：任务设计参考

* **Skill 价值定位**：`smart-contracts` 类热门 skill 的共性价值，通常落在从标准、实现和集成三层同时审视 token 风险。对这类任务，skill 的作用是把 token 行为标签、协议防护措施和最终上线结论串成一条可复核的分析链。
* **Verifier 设计重点**：Verifier 应独立重算 token 级 findings、协议覆盖状态和最终 decision，并检查 Markdown、TSV、JSON 之间的证据一致性。除了结果是否对，还要覆盖输入不可改写、项目入口可复跑、策略变更能传导到结果。

## 第二部分：示例任务

### 📌 任务元数据

- 任务 ID：`smart-contracts__token_onboarding_review`
- 类别：`smart-contracts`
- 绑定 Skill：`token-integration-analyzer`
- 输入数据参考来源：
  - `environment/data/token_profiles/usdt.json`、`usdc.json`、`sta.json`、`ampl.json`、`amp.json`：任务内候选抵押品行为档案；设计形态参考 weird ERC20 案例库与 token integration checklist  
    `https://github.com/d-xo/weird-erc20`  
    `https://ethereum.org/developers/tutorials/token-integration-checklist/`
  - `environment/data/token_profiles/dai.json`、`wbtc.json`：任务内 ERC-20 基线档案；字段和接口背景参考 ERC-20 标准与 OpenZeppelin ERC20 API  
    `https://eips.ethereum.org/EIPS/eip-20`  
    `https://docs.openzeppelin.com/contracts/5.x/api/token/erc20`
  - `environment/data/reference/erc4626_notes.md`、`environment/protocol/contracts/CollateralVault.sol`：任务内 vault 份额与资产会计约束；设计形态参考 ERC-4626 标准、OpenZeppelin ERC4626 指南与合约实现  
    `https://eips.ethereum.org/EIPS/eip-4626`  
    `https://docs.openzeppelin.com/contracts/5.x/erc4626`  
    `https://github.com/OpenZeppelin/openzeppelin-contracts/blob/master/contracts/token/ERC20/extensions/ERC4626.sol`
  - `environment/protocol/contracts/ApprovalHelper.sol`、`environment/data/reference/erc20_notes.md`：任务内转账与授权处理约束；设计形态参考 OpenZeppelin SafeERC20 实现  
    `https://github.com/OpenZeppelin/openzeppelin-contracts/blob/master/contracts/token/ERC20/utils/SafeERC20.sol`

### 📊 验证与测试指标（Oracle & Verifier）

- Oracle：按正式流程独立运行并完成交付，结果可直接 100% 通过验证。
- Verifier策略：

主测试
| 测试点 | 验证内容 | 对应skill内化点 |
| :--- | :--- | :--- |
| 输出契约 | 校验 5 个交付文件存在、可解析、列顺序正确 | 结构化交付 |
| 决策重算 | 独立重算每个 token 的 decision、risk 和必需措施 | token 行为到上线结论 |
| 协议覆盖核对 | 独立核对每项 protocol measure 的 coverage 与引用位置 | 集成防护措施审阅 |
| 证据一致性 | 校验 Markdown、TSV、JSON 里的 token、measure 和 evidence 是否对齐 | 多输出联动 |
| 策略传导 | 改动 policy 后，至少一项 token 结果要随之变化 | 以 policy 驱动分析 |
| 项目入口复跑 | 用正式 pipeline 重跑，并校验重复运行结果一致 | 端到端工作流落地 |

防作弊测试
| 测试点 | 验证内容 |
| :--- | :--- |
| 输入完整性 | `data` 内容不可修改 |
| 静态答案拦截 | 禁止 hardcode 决策、coverage 或直接提交手写交付文件 |
| 交付来源 | 输出必须由 `run_token_onboarding_review.py` 正式入口重新生成 |

### ⚡ Skill 相关性评估

结论：强相关。这个任务里，Skill 的核心价值落在先识别候选 token 的异常行为，再把这些行为映射到协议侧必需措施，最后收敛成可交付的上线结论。只做表面整理的解法，往往能写出大致正确的结论标签，但会漏掉 blocker、coverage 缺口或 finding 到 decision 的闭环。

基于最近 **4 次** 有效对比实验（均为真正跑到 task-level、存在完整 agent 轨迹；已排除启动失败类 trial）：

| 维度 | Without Skill | With Skill | 结果对比 |
| :--- | :--- | :--- | :--- |
| 通过率 | `0%` | `50%` | 近 4 次有效对照里，without Skill 全部保留至少 1 项 verifier 失败；with Skill 有 2 次稳定通过全部 verifier |
| Agent 执行耗时 | `718.2s` | `759.5s` | With Skill 在这组样本里平均耗时高约 `5.7%`，主要来自更完整的证据梳理和 coverage 校对 |
| Tokens | `495.3K` | `645.0K` | With Skill 在这组样本里 token 开销约为 Without Skill 的 `1.30x`，换来更高的通过率和更完整的分析链 |

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
│   ├── pipeline/
│   ├── protocol/
│   └── skills/
├── tests/
└── solution/
```
