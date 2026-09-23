# Cloud Template

这是面向 Cloud 类 skill 的模板。它综合参考 SkillsMP Cloud 类热门 skill 的共性能力：将分散的基础设施需求抽象成可复用模块、在多环境之间统一接口与标签合同、通过真实 IaC 执行链路验证资源拓扑，并补齐示例、版本约束、测试与文档等共享交付要素。

## 第一部分：任务设计参考

* **Skill 价值定位**：Cloud 类热门 skill 的核心价值，不是把某个环境临时堆出来，而是把基础设施能力建设成可复用、可推广、可交接的工程资产。模板任务应强调模块抽象、跨环境一致性、输入输出合同、资源标签治理和真实 Terraform 验证链路，而不是把题退化成一次性脚本拼装。
* **Verifier 设计重点**：Verifier 应优先验证 solver 是否真的沿 Terraform 真实链路建设了共享模块，是否让多个环境消费同一个模块接口，是否满足子网、路由、NAT、标签和 EKS 接入等资源行为合同，以及是否保留了模块文档、示例、版本约束和测试配套。防作弊点应覆盖平行模块、环境特化硬编码、保留重复资源实现、静态产物替代和只对单一蓝图成立的实现。

## 第二部分：示例任务

### 📌 任务元数据

- 任务 ID：`cloud__terraform-shared-vpc-module-library`
- 类别：`cloud`
- 绑定 Skill：`terraform-module-library`
- 输入数据参考来源：
  - `environment/data/environment_blueprints/staging.json`：任务内 `staging` 网络蓝图；设计形态参考 `terraform-aws-modules/terraform-aws-vpc` 的共享 VPC 模块使用方式  
    【https://github.com/terraform-aws-modules/terraform-aws-vpc】
  - `environment/data/environment_blueprints/prod.json`：任务内 `prod` 网络蓝图；设计形态同样参考 `terraform-aws-modules/terraform-aws-vpc` 的多环境复用方式  
    【https://github.com/terraform-aws-modules/terraform-aws-vpc】
  - `environment/data/module_contract.json`：模块输入输出与结构合同；设计形态直接参考 HashiCorp Terraform module development guidance  
    【https://developer.hashicorp.com/terraform/language/modules/develop】
  - `environment/data/eks_subnet_tag_contract.json`：EKS 子网标签合同；数据语义直接来源于 Amazon EKS 官方子网标签要求  
    【https://docs.aws.amazon.com/eks/latest/userguide/tag-subnets-auto.html】
  - `environment/data/platform_tags.json`：平台统一标签合同；设计形态参考 AWS Tagging best practices  
    【https://docs.aws.amazon.com/tag-editor/latest/userguide/best-practices-and-strats.html】

### 📊 验证与测试指标（Oracle & Verifier）

- Oracle：按正式流程独立运行并完成交付，结果可直接 100% 通过验证。
- Verifier策略：

主测试
| 测试点 | 验证内容 | 对应skill内化点 |
| :--- | :--- | :--- |
| 共享模块消费 | 校验 `live/staging` 和 `live/prod` 都通过同一 `source` 路径消费共享模块，且不再直接持有核心 VPC / subnet / route / NAT 资源 | 从一次性环境配置抽象为共享模块 |
| 模块结构合同 | 校验模块包含 `main.tf`、`variables.tf`、`outputs.tf`、`versions.tf`、`README.md`、完整示例和模块测试文件 | 模块库结构、文档、示例和测试配套 |
| staging 资源计划 | 运行真实 Terraform plan，校验 `staging` 的子网数量、IGW 路由、单 NAT 策略和标签合同 | 变量接口设计与资源建模 |
| prod 资源计划 | 运行真实 Terraform plan，校验 `prod` 的三 AZ 拓扑、多 NAT 策略和标签合同 | 多环境复用与差异参数化 |
| 隐藏 qa 蓝图 | 基于隐藏蓝图临时生成新的根模块并 plan，校验模块未对现有两套蓝图做特判 | 可复用性与泛化能力 |

防作弊测试
| 测试点 | 验证内容 |
| :--- | :--- |
| 平行实现规避 | 禁止把 `staging`、`prod` 保留为两套独立资源实现，同时只额外放一个未被消费的模块目录 |
| 硬编码与静态产物 | 禁止靠固定 CIDR、固定 AZ 数量、静态输出文件或旁路脚本代替真实 Terraform 模块求值 |

### ⚡ Skill 相关性评估

结论：强相关。这个任务把 `terraform-module-library` 的核心价值压在了“构建共享 Terraform 模块库”而不是“单环境堆资源”上：solver 必须补齐标准模块骨架、设计可复用输入输出接口、让多个环境消费同一模块，并通过真实 `terraform plan` 满足网络拓扑与标签合同。对照实验里，without Skill 虽然也会尝试写模块，但连续 3 次都停留在表面抽象，没有把计划结果建模成 verifier 期望的共享蓝图语义，因此公开蓝图和隐藏 `qa` 蓝图同时失败。

基于最近 **3** 次有效对比实验（均为真正跑到 task-level、存在完整 agent 轨迹；已排除启动失败类 trial）：

| 维度 | Without Skill | With Skill | 结果对比 |
| :--- | :--- | :--- | :--- |
| 通过率 | `0% (0/3)` | `100% (3/3)` | without Skill 连续 3 次都因计划拓扑未满足共享蓝图合同而至少保留 3 项 verifier 失败；with Skill 3 次都完整通过。 |
| Agent 执行耗时 | `498.3s` | `348.9s` | With Skill 的构建与收敛更快，平均 Agent 执行耗时降低约 `30%`。 |
| Tokens | `0.98M` | `0.90M` | Without Skill 的上下文与返工开销约为 With Skill 的 `1.09x`。 |

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
