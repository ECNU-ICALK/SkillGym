# CI/CD Template

这是面向 `cicd` 类 skill 的模板。它综合参考 SkillsMP CI/CD 类热门 skill 的共性能力：多阶段流水线设计、GitHub Actions 复用校验、镜像构建发布、环境门禁、发布切换和交付摘要归档。

## 第一部分：任务设计参考

* **Skill 价值定位**：CI/CD 类 skill 的核心价值，是把分散在 workflow、镜像发布、环境切分、复用校验和发布推进中的高成本决策标准化，帮助 Agent 更快收敛到可交付的自动化方案。模板任务应让 skill 主要作用在 job 编排、依赖关系、环境门禁、可复用校验入口、制品提升和 rollout 策略这些环节。
* **Verifier 设计重点**：Verifier 应优先验证自动化链路是否按合同落地，并通过既有入口产生产物，而不是只检查 YAML 外形。重点应覆盖触发条件、复用校验、制品构建、不可变制品在环境阶段的延续、环境约束、发布策略、输入不可变以及 entrypoint 对仓库当前状态的响应能力。

## 第二部分：示例任务

### 📌 任务元数据

- 任务 ID：`cicd__saturn-checkout-release-automation`
- 类别：`cicd`
- 绑定 Skill：`github-actions-templates`
- 输入数据参考来源：
  - `environment/data/reference/github_actions_node_ci.md`：Node.js 校验 workflow 形态参考  
    【https://github.com/actions/starter-workflows/blob/main/ci/node.js.yml】
  - `environment/data/reference/github_actions_workflow_syntax.md`：workflow 触发、依赖、权限和复用语法参考  
    【https://docs.github.com/en/actions/writing-workflows/workflow-syntax-for-github-actions】
  - `environment/data/reference/github_actions_environments.md`：环境门禁与交付环境口径参考  
    【https://docs.github.com/actions/reference/workflows-and-actions/deployments-and-environments】
  - `environment/data/reference/github_actions_docker_publish.md`：镜像发布步骤形态参考  
    【https://docs.github.com/actions/guides/publishing-docker-images】
  - `environment/data/reference/argo_rollouts_canary.md`：生产流量切换步骤形态参考  
    【https://argo-rollouts.readthedocs.io/en/stable/features/canary/】
  - `environment/data/reference/kubernetes_rolling_update.md`：集群发布与探针校验参考  
    【https://kubernetes.io/docs/tasks/run-application/update-deployment-rolling/】

### 📊 验证与测试指标（Oracle & Verifier）

- Oracle：按正式流程独立运行并完成交付，结果可直接 100% 通过验证。
- Verifier策略：

主测试
| 测试点 | 验证内容 | 对应skill内化点 |
| :--- | :--- | :--- |
| 输出契约 | `artifacts/release_bundle.json` 存在、字段完整且与仓库配置一致 | 自动化交付完成后产出结构化摘要 |
| 校验链入口 | `npm ci`、lint、unit、security、smoke、e2e 和 bundle 入口全部可跑 | 校验链路与交付链路连通 |
| workflow 编排 | 触发条件、复用校验、publish、staging、production、summary 依赖关系成立 | 多阶段 job 组织与复用 workflow |
| 发布与环境 | 镜像发布 action、不可变制品推进、环境名、串行化约束和交付入口满足合同 | 发布 job、环境拆分、权限、制品提升与串行化 |
| rollout 策略 | 流量切换步骤、暂停窗口和分析模板满足合同 | 灰度发布与发布后校验 |

防作弊测试
| 测试点 | 验证内容 |
| :--- | :--- |
| 输入完整性 | `/app/data/` 下合同与参考文件不可修改 |
| 入口重跑 | 删除结果后重新执行 `make release-bundle`，语义结果应保持一致 |
| 变更感知 | 临时改坏 rollout 权重后，entrypoint 应拒绝生成 bundle |
| 旁路防护 | 仅手写答案文件、跳过不可变制品提升或只留表面摘要，无法通过独立重算与 mutation 校验 |

### ⚡ Skill 相关性评估

结论：强相关。这个任务里，Skill 的核心价值是把 GitHub Actions 的校验、发布、环境拆分、复用工作流和制品推进标准化，从而降低试错成本；without Skill 更容易停在 workflow 只完成一半、或 rollout、制品提升和阶段归档没有闭环的动作失败上。

基于最近 **3** 次有效对比实验（均为 task-level、存在完整 agent 轨迹；已排除启动失败类 trial，并按当前最终版 verifier 规则复核）：

| 维度 | Without Skill | With Skill | 结果对比 |
| :--- | :--- | :--- | :--- |
| 通过率 | `0/3 (0%)` | `3/3 (100%)` | 近 3 次有效对照里，without Skill 主要卡在分支引用标签链缺失，或 staging / production 串行化约束未补齐，因此当前 verifier 仍保留失败项 |
| Agent 执行耗时 | `304.7s` | `310.6s` | 这 6 次样本里，with Skill 平均耗时高 `1.9%`；原因是它更稳定地把发布链路补完整，without Skill 更常在未闭环状态提前结束 |
| Tokens | `373,848` | `443,496` | with Skill 的上下文投入更高，但换来了稳定通过；without Skill 平均 tokens 约为 With Skill 的 `0.84x`，同时通过率仍为 `0%` |

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
│   ├── workspace/
│   └── skills/
├── tests/
│   ├── test.sh
│   └── test_outputs.py
└── solution/
    └── solve.sh
```
