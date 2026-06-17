# Health-Fitness Template

这是面向 `health-fitness` 类 skill 的模板。它综合参考 SkillsMP health-fitness 类热门 skill 的共性能力：会员 intake 理解、基础能量与宏量目标推导、训练动作检索、器械与禁忌约束处理、公开营养数据库检索、可执行计划生成和教练交接。

## 第一部分：任务设计参考

* **Skill 价值定位**：health-fitness 类热门 skill 的核心价值，是把会员目标、训练限制、饮食限制和公开数据库里的事实，组织成一条可执行的计划生成链路。模板任务不应该把完整方法直接写进题面，而应该把价值放在“识别该查什么、去哪里查、如何把结果收口成可交付方案”。
* **Task 目标形态**：任务应落在真实风格的健身工作室、线上教练或营养顾问场景里，要求 Agent 结合 intake、动作库、食物库、器械清单和当前 policy，产出结构化评估、训练安排、餐单和 handoff。题面要强调业务症状、正式交付物和禁止事项，把检索与诊断路径尽量留给 skill 和 solver 自己识别。
* **Verifier 设计重点**：Verifier 应优先验证 solver 是否经过真实规划链路，并检查计划是否满足营养、动作、器械、训练日和禁忌限制，而不是只卡文案格式。它还应通过防作弊测试拦截只看旧导出、跳过 live service、删餐次、删训练日、替换真实数据链路或硬编码答案等捷径。

## 第二部分：示例任务

### 📌 任务元数据

- 任务 ID：`health-fitness__boutique-gym-onboarding-plan`
- 类别：`health-fitness`
- 难度：`hard`
- 绑定 Skill：`fitness-nutrition`
- 输入数据参考来源：
  - `environment/data/reference_exercise_shortlist.json`：任务内候选动作导出；设计形态参考 wger 的 exercise / equipment / muscle 数据  
    https://wger.de/en/software/api
  - `environment/data/reference_food_shortlist.csv`：任务内候选食物导出；设计形态参考 USDA FoodData Central 的食物与营养字段  
    https://fdc.nal.usda.gov/api-guide  
    https://fdc.nal.usda.gov/download-datasets.html
  - `environment/data/member_profile.json`：任务内虚构会员 intake；为任务原创业务输入，无单独公开数据链接
  - `environment/data/equipment_inventory.csv`：任务内门店器械与替代分组；为任务原创业务输入，无单独公开数据链接
  - `environment/data/meal_slot_rules.csv`：任务内餐次角色约束；为任务原创业务输入，无单独公开数据链接
  - `environment/data/planner_manifest.json`：任务内本地配置文件，用于声明 live planning service 地址与计划窗口，无单独公开数据链接

### 📊 验证与测试指标（Oracle & Verifier）

- Oracle：按正式流程独立运行并完成交付，结果可直接 100% 通过验证。
- Verifier策略：

主测试

| 测试点 | 验证内容 | 对应skill内化点 |
| :--- | :--- | :--- |
| 输出契约 | 检查 4 个输出文件存在、可解析，并包含必需字段、列名和标题 | 先理解正式交付合同，再组织结构化结果 |
| 评估重算 | 按当前 policy 重算 BMI、BMR、TDEE、训练日/休息日热量与宏量目标 | 会员评估与营养目标推导 |
| 训练计划校验 | 用 live exercise catalog 重算动作合法性、器械可用性、禁忌限制、训练日覆盖和目标肌群覆盖 | 动作检索、器械映射、约束收敛 |
| 餐单校验 | 用 live nutrition catalog 重算每条食物营养值、整日热量/宏量/纤维、过敏原与餐次规则 | 营养检索、克数换算、配餐一致性 |
| Handoff 一致性 | 检查 handoff 是否准确反映评估、训练安排、餐单和替代建议 | 教练交接与执行闭环 |

防作弊测试

| 测试点 | 验证内容 |
| :--- | :--- |
| 真实链路与旧导出规避 | 访问日志必须证明 solver 查询了 live planning service；仅依赖 `reference_*` 导出不能通过 |
| 数据与环境完整性 | `/root/data/`、隐藏服务和 skill 目录内容不得变化；服务在 verifier 结束时仍健康 |

### ⚡ Skill 相关性评估

结论：强相关。这个任务里，Skill 的核心价值是把会员评估、动作筛选、营养检索和教练 handoff 串成一条稳定工作流，从而明显降低约束冲突和试错成本；without Skill 更容易停在旧导出依赖、错误动作选择、宏量不达标或 handoff 与实际计划脱节的行动级失败上。

基于最近 **3** 次有效对比实验（均为真正跑到 task-level、存在完整 agent 轨迹；已排除启动失败类 trial）：

| 维度 | Without Skill | With Skill | 结果对比 |
| :--- | :--- | :--- | :--- |
| 通过率 | `0%` | `66.7%` | Without Skill 三次均未通过，失败集中在 assessment 计算、餐单营养换算和 handoff 风险提示；With Skill 有 2 次完整通过，另 1 次仅在 handoff 摘要覆盖度上失败。 |
| Agent 执行耗时 | `528.6s` | `649.0s` | With Skill 更常把完整评估、训练、餐单和 handoff 链路走完，因此平均 Agent 执行时长更高约 `22.8%`；Without Skill 更早失败。 |
| Tokens | `1.30M` | `1.13M` | Without Skill 的总 token 开销约为 With Skill 的 `1.15x`，说明缺少 skill 后试错和上下文回溯更重。 |

## 📁 标准目录结构说明

```text
模板任务：
├── instruction.md          # 任务说明（仅包含症状、业务约束和禁止事项）
├── task.toml               # 任务元数据（标签、技能要求、运行入口）
├── PLAN.json               # 任务构建过程的结构化元信息
├── environment/            # 运行环境
│   ├── Dockerfile          # 单容器镜像定义；在同一容器内启动 planning service 与隐藏下游服务
│   ├── ...                 # 可选的 service seed / data / scripts
│   └── skills/             # 任务绑定的 health-fitness skill 定义与辅助脚本
├── tests/                  # Verifier 与 Guardrail 测试集
└── solution/               # 官方参考修复代码及 solve.sh
```
