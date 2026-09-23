# Culinary Arts Template

这是面向 `culinary-arts` 类 skill 的模板。它综合参考 SkillsMP culinary-arts 类热门 skill 的共性能力：结构化餐食检索、从菜谱到采购清单的转化，以及围绕具体服务方案开展的轻量营养校验。

## 第一部分：任务设计参考
* **Skill 价值定位**：culinary-arts 类 skill 的价值，通常体现在把餐食计划、菜谱事实、食材决策和服务排期组织成一条可执行的工作链路。高质量 skill 应帮助 solver 降低检索成本、统一查询顺序，并让采购与营养判断始终基于同一套权威来源。
* **Verifier 设计重点**：Verifier 应同时检查结果正确性和工作流是否合规。对这一类任务来说，通常需要从来源记录重新计算餐次覆盖、食材汇总和营养校验结果，并额外确认 solver 确实走了指定的 planning 接口，而不是直接绕到底层存储读取数据。

## 第二部分：示例任务
### 📌 任务元数据
- 任务 ID：`culinary-arts__paprika_workshop_ops_packet`
- 类别：Culinary Arts
- 绑定 Skill：`paprika`, `healthy-eating`
- 输入数据参考来源：
  - `environment/paprika_seed/recipes.json`：任务内 Paprika recipe detail records；具体 recipe 来源形态参考  
    【https://www.themediterraneandish.com/chickpea-salad/】  
    【https://www.bbcgoodfood.com/recipes/orzo-salmon-traybake】  
    【https://www.eatingwell.com/recipe/275923/white-bean-turkey-bowls/】  
    【https://www.feastingathome.com/miso-tofu-bowls/】  
    【https://www.loveandlemons.com/quinoa-lentil-salad/】  
    【https://www.delish.com/cooking/recipe-ideas/a28625784/sheet-pan-pesto-chicken-recipe/】
  - `environment/paprika_seed/meals.json`：任务内 meal-plan rows；Paprika meal planning interface 形态参考  
    【https://www.paprikaapp.com/】
  - `environment/paprika_seed/groceries.json`：任务内 grocery carryover rows；Paprika grocery list interface 形态参考  
    【https://www.paprikaapp.com/】
  - `environment/data/event_brief.json`：任务内 nutrition target brief；daily target framing 参考  
    【https://www.dietaryguidelines.gov/】

### 📊 验证与测试指标（Oracle & Verifier）
- Oracle：按正式流程独立运行并完成交付，结果可直接 100% 通过验证。
- Verifier策略：

主测试

| 测试点 | 验证内容 | 对应skill内化点 |
| :--- | :--- | :--- |
| 计划餐次覆盖 | `meal_manifest.json` 是否按服务日期和 meal slot 完整覆盖 6 个计划餐次 | `paprika meals --json` |
| 菜谱明细补全 | recipe UID、标签、时长、serving 放大后是否与预期一致 | `paprika recipe <uid> --json` |
| 扣减后采购差额 | pantry 扣减、reserved grocery 扣减、正向采购行排序是否正确 | `paprika groceries --all --json` |
| 每日营养校验 | 每日 kcal / protein / fiber 结果与 target check 是否一致 | `healthy-eating` 的 nutrition check framing |
| 厨房交接合同 | note 结构、菜名覆盖、carryover 摘要是否完整 | 从操作数据提炼可执行 handoff |

防作弊测试

| 测试点 | 验证内容 |
| :--- | :--- |
| 可见输入未变 | `/root/data` 输入快照保持不变 |
| Paprika seed 未变 | backing seed 数据未被篡改 |
| 工作流护栏 | access log 必须体现 `paprika` CLI entrypoint 的 meals / recipe / groceries 查询 |
| 输出边界 | `/root/output` 之外不能生成额外顶层交付物 |

### ⚡ Skill 相关性评估
结论：强相关。这个任务的核心差异在于，with-skill 直接把 Paprika lookup workflow 固化为 `paprika meals --json`、`paprika recipe <uid> --json` 和 `paprika groceries --all --json` 的工作链，而 without-skill 会更容易自行发现内部入口并绕开 skill 约定的 CLI entrypoint。

基于最近 **3** 次有效对比实验（均为真正跑到 task-level、存在完整 agent 轨迹；已排除启动失败类 trial）：

| 维度 | Without Skill | With Skill | 结果对比 |
| :--- | :--- | :--- | :--- |
| 通过率 | `0%` | `100%` | 近 3 次有效对照里，without Skill 都在 workflow guardrail 上失败：agent 使用了内部 `mealops` 路径，没有走 skill 指定的 `paprika` CLI entrypoint |
| Agent 执行耗时 | `192.9s` | `175.9s` | With Skill 的发现和收敛更快，平均 Agent 耗时降低约 `9%` |
| Tokens | `195156.3` | `137603.0` | Without Skill 的上下文与试错开销约为 With Skill 的 `1.42x` |

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
│   ├── paprika_cli/
│   ├── paprika_seed/
│   └── skills/
├── tests/
└── solution/
```
