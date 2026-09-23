# Containers Template

这是面向 Containers 类 skill 的模板。它综合参考 SkillsMP Containers 类热门 skill 的共性能力：围绕 Kubernetes 应用交付组织 chart 与 manifests、把环境差异收敛到清晰的配置层、并沿 Helm 与 K8s 的标准验证链路完成交付闭环。

## 第一部分：任务设计参考

* **Skill 价值定位**：Containers 类热门 skill 的价值，通常落在可复用部署骨架、配置抽象、模板组织、依赖边界和交付验证上。模板任务应强调 chart 结构、values 分层、环境差异表达和稳定渲染链路，让 solver 通过工程化交付动作完成任务。
* **Verifier 设计重点**：Verifier 应优先验证 solver 是否沿 Helm 渲染链路交付了可复用 chart，是否正确表达环境差异、服务暴露、配置注入和可用性约束，是否能在隐藏 overlay 上保持泛化。防作弊点应覆盖静态清单复制、环境特化硬编码、跳过渲染入口和修改输入合同。

## 第二部分：示例任务

### 📌 任务元数据

- 任务 ID：`containers__helm-multi-env-release-chart`
- 类别：`containers`
- 绑定 Skill：`helm-chart-scaffolding`
- 输入数据参考来源：
  - `environment/data/app_contract.json`：任务内应用规格合同；设计形态参考 `podinfo` Helm chart values 与 deployment 模板  
    【https://raw.githubusercontent.com/stefanprodan/podinfo/master/charts/podinfo/values.yaml】
  - `environment/data/release_matrix.yaml`：任务内多环境发布矩阵；设计形态参考 Helm charts 文档与 `podinfo` 环境 values 组织方式  
    【https://helm.sh/docs/topics/charts/】
  - `environment/data/platform_labels.json`：统一标签与选择器合同；设计形态直接参考 Helm labels best practices  
    【https://helm.sh/docs/chart_best_practices/labels/】
  - `environment/data/render_contract.json`：任务内渲染资源合同；Service、Ingress、HPA 与 PDB 的字段设计参考 Kubernetes 官方文档  
    【https://kubernetes.io/docs/concepts/services-networking/service/】  
    【https://kubernetes.io/docs/concepts/services-networking/ingress/】  
    【https://kubernetes.io/docs/tasks/run-application/horizontal-pod-autoscale-walkthrough/】  
    【https://kubernetes.io/docs/tasks/run-application/configure-pdb/】

### 📊 验证与测试指标（Oracle & Verifier）

- Oracle：按正式流程独立运行并完成交付，结果可直接 100% 通过验证。
- Verifier策略：

主测试
| 测试点 | 验证内容 | 对应skill内化点 |
| :--- | :--- | :--- |
| Chart 结构 | 校验 Chart.yaml、values.yaml、values.schema.json、helpers 与关键模板文件齐备 | chart 目录组织与骨架搭建 |
| staging 渲染 | 校验 staging 的 Deployment、Service、ConfigMap、Ingress、PDB、ServiceAccount 渲染结果与合同一致 | 多环境 values、基础模板与服务暴露 |
| prod 渲染 | 校验 prod 的 HPA、Ingress、PDB、配置覆盖与标签合同成立 | 生产环境差异表达与扩缩容配置 |
| 配置联动 | 校验 ConfigMap 内容、Pod 注解校验和、Service selector 与 Pod labels 保持联动 | helper 模板与配置注入链路 |
| 隐藏 qa overlay | 渲染隐藏 qa overlay，校验 chart 未对 staging/prod 做特化 | 可复用性与泛化能力 |
| Schema 约束 | 用负例 values 触发 lint 失败，确认 values.schema.json 生效 | Helm 校验与交付保护 |

防作弊测试
| 测试点 | 验证内容 |
| :--- | :--- |
| 输入与入口保护 | 禁止修改输入合同和 shipped render_release.sh |
| 静态产物规避 | 禁止提交环境特化的渲染结果文件来替代 Helm 模板 |
| Skill 使用轨迹 | with_skill 场景下需在修改 chart 前成功读取绑定 skill |

### ⚡ Skill 相关性评估

结论：强相关。这个任务把 Helm chart 骨架、values 分层、模板 helpers、多环境 overlay 和 Helm 校验链路放在同一条交付路径里；skill 的核心价值正是把这些动作组织成稳定的工作流。当前 verifier 会检查 solver 是否在改 chart 之前成功读取绑定 skill，能拦住绕开技能载荷或只补表层产物的做法。

基于最近 **3** 次有效对比实验（均为真正跑到 task-level、存在完整 agent 轨迹；已排除启动失败类 trial）：

| 维度 | Without Skill | With Skill | 结果对比 |
| :--- | :--- | :--- | :--- |
| 通过率 | `0%` | `100%` | 近 3 次有效对照里，without Skill 都至少留下 1 项 verifier 失败；主要失败点是没有在改 chart 前成功读取绑定的 `helm-chart-scaffolding` skill。 |
| Agent 执行耗时 | `382.1s` | `446.3s` | with Skill 成功率更高，但这 3 次里 without Skill 多在 guardrail 处提前结束，所以平均耗时更短。 |
| Tokens | `346474` | `399430` | with Skill 的完整实现与验证链路更长；without Skill 因提前失败，平均 tokens 更低。 |

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
└── solution/
```
