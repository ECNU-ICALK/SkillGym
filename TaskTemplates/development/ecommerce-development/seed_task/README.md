# Ecommerce Development Template

这是面向 `ecommerce-development` 类 skill 的模板。它综合参考 SkillsMP 这一类热门 skill 的共性能力：商店初始化、商品结构配置、配送规则、支付规则、公开接口定制，以及把多来源商品素材整理成可运营的 WooCommerce 工作区。

## 第一部分：任务设计参考

* **Skill 价值定位**：ecommerce-development 类热门 skill 的价值，通常落在把平台配置、目录结构、支付与配送规则、定制代码和交付验证串成一条完整交付链路。它应该帮助 solver 更快识别平台内的关键动作和检查路径，并把结果沉淀成可运行的商店能力。
* **Verifier 设计重点**：Verifier 应优先验证平台动作是否落地，例如目录是否按数据生成、变体是否可用、配送和支付规则是否生效、接口是否按输入数据返回结果。它还需要防止硬编码、跳过平台配置、篡改输入数据或只做表层接口伪装。

## 第二部分：示例任务

### 📌 任务元数据

- 任务 ID：`ecommerce_development__museum_printshop_launch`
- 类别：`ecommerce-development`
- 绑定 Skill：`wordpress-woocommerce-development`
- 输入数据参考来源：
  - `environment/data/met_print_seed.csv`：任务内商品种子行；字段组织参考 The Met Open Access 对象快照与馆藏上新清单  
    https://github.com/metmuseum/openaccess
  - `environment/data/met_object_details.ndjson`：任务内作品明细快照；对象字段直接来源于 The Met Collection API  
    https://metmuseum.github.io/  
    https://collectionapi.metmuseum.org/public/collection/v1/objects/436532
  - `environment/data/met_departments.json`：任务内部门清单快照；字段直接来源于 The Met Collection API departments 接口  
    https://collectionapi.metmuseum.org/public/collection/v1/departments
  - `environment/data/collection_plan.json`：任务内系列与上架计划文件；结构设计参考 WooCommerce 商品分类与系列组织  
    https://woocommerce.com/document/managing-product-taxonomies/
  - `environment/data/shipping_rules.json`：任务内配送规则文件；结构设计参考 WooCommerce shipping zones / shipping classes  
    https://woocommerce.com/document/setting-up-shipping-zones/
  - `environment/data/checkout_policy.md`：任务内支付约束文件；约束形态参考 WooCommerce payment gateway 配置  
    https://woocommerce.com/document/payment-gateway-api/

### 📊 验证与测试指标（Oracle & Verifier）

- Oracle：按正式流程独立运行并完成交付，结果可直接 100% 通过验证。
- Verifier 策略：

主测试

| 测试点 | 验证内容 | 对应 skill 内化点 |
| :--- | :--- | :--- |
| 基础结构齐备 | 页面入口、依赖程序与关键脚本能够顺利启动 | 任务初始环境整合配置 |
| 过程与流转检验 | 在页面中对目标核心场景进行操作，相关反馈流程应完整并生效 | 功能环节串联度测试 |
| 相同输入复现 | 在同样基础环境下多次运行或重试，可得出相同结构的数据响应 | 实现结果稳定性保障 |
| 多变体动态适配 | 当替换输入基础数据时，系统需提供正确的衍生显示及相关逻辑应对 | 灵活性与输入参数探索 |
| 输出一致性校验 | 核对业务面板展现或汇总内容的说明能否对得上要求数据范围 | 分析处理数据的呈现准度 |
| 结构交付合规 | 最终保存下来的生成文档或者资源内容格式齐整 | 最终发布过程追溯 |

防作弊测试

| 测试点 | 验证内容 |
| :--- | :--- |
| 限定参数核实 | 限制篡改依赖目录或源信息进行取巧完成 |
| 源文件定值扫描 | 发现直接在项目中输出预期静态内容以作答的问题现象 |

### ⚡ Skill 相关性评估

结论：待实验补齐。这个任务的核心价值在于把 WooCommerce 的目录搭建、配送规则、支付范围控制和定制 feed 串成一条完整交付链路；题面只保留交付合同与业务约束，能否快速识别并完成平台内关键动作，将直接影响收敛速度与通过率。

基于最近 **n** 次有效对比实验（待补齐）：

| 维度 | Without Skill | With Skill | 结果对比 |
| :--- | :--- | :--- | :--- |
| 通过率 | `待补齐` | `待补齐` | `待补齐` |
| Agent 执行耗时 | `待补齐` | `待补齐` | `待补齐` |
| Tokens | `待补齐` | `待补齐` | `待补齐` |

## 📁 标准目录结构说明

```text
模板任务：
├── instruction.md
├── task.toml
├── PLAN.json
├── README.md
├── environment/
│   ├── Dockerfile
│   ├── data/
│   ├── skills/
│   └── workspace/
├── tests/
└── solution/
```
