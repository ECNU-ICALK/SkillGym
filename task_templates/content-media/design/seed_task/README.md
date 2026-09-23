# Design Template

这是面向 `design` 类 skill 的模板。它综合参考 SkillsMP design 类热门 skill 的共性能力：把页面合同、结构草图、公开数据快照和品牌约束整理成一个可直接运行、可直接核验的浏览器交付物。

## 第一部分：任务设计参考

* **Skill 价值定位**：这类 skill 的共性价值，在于把“做一个好看的页面”推进到“按既定合同完成整套浏览器简报交付”。模板任务应让 skill 在页面排序、模块落位、视口适配、图表嵌入和本地回放校验上形成明显帮助。
* **Verifier 设计重点**：Verifier 应同时检查页面覆盖、合同一致性、数据口径一致性、视口适配和输出目录整洁度。重点不应只盯格式细节，而应优先拦下漏页、漏模块、漏图表、页面不可回放和页面结构偏离合同这类问题。

## 第二部分：示例任务

### 📌 任务元数据

- 任务 ID：`design__north_america_power_mix_brief_site`
- 类别：`design`
- 绑定 Skill：`single-file-briefing-deck`
- 输入数据参考来源：
  - `environment/power_brief/data/country_profile.json`：任务内国家标签和基础资料；直接来源于  
    【https://api.worldbank.org/v2/country/USA;CAN;MEX?format=json&per_page=100】
  - `environment/power_brief/data/world_bank_population.json`：任务内人口数据快照；直接来源于  
    【https://api.worldbank.org/v2/country/USA;CAN;MEX/indicator/SP.POP.TOTL?format=json&per_page=20000】
  - `environment/power_brief/data/world_bank_gdp.json`：任务内 GDP 数据快照；直接来源于  
    【https://api.worldbank.org/v2/country/USA;CAN;MEX/indicator/NY.GDP.MKTP.CD?format=json&per_page=20000】
  - `environment/power_brief/data/annual_co2_emissions.csv`：任务内年度 CO2 排放数据快照；直接来源于  
    【https://ourworldindata.org/grapher/annual-co2-emissions-per-country.csv?v=1&csvType=full&useColumnShortNames=false】
  - `environment/power_brief/data/electricity_prod_source.csv`：任务内按能源来源拆分的发电数据快照；直接来源于  
    【https://ourworldindata.org/grapher/electricity-prod-source-stacked.csv?v=1&csvType=full&useColumnShortNames=false】

### 📊 验证与测试指标（Oracle & Verifier）

- Oracle：按正式流程独立运行并完成交付，结果可直接通过全部验证。
- Verifier 策略：

主测试

| 测试点 | 验证内容 | 对应 skill 内化点 |
| :--- | :--- | :--- |
| 页面生成 | 能生成单文件 HTML 和清单文件 | 完成交付主产物 |
| 合同覆盖 | 页面顺序、模块和图表覆盖与合同一致 | 按合同组织整套页面 |
| 数据一致 | 关键指标、图表标题和说明文字与数据快照一致 | 处理公开数据并写入页面 |
| 页面可用 | 每页可导航、可回放、页内无滚动 | 浏览器简报交付能力 |
| 结构对齐 | 页面结构与草图要求相符 | 把线框要求落到成品页面 |
| 清单一致 | manifest 与页面中的模块、图表、资源保持一致 | 交付校对能力 |

防作弊测试

| 测试点 | 验证内容 |
| :--- | :--- |
| 保护输入 | 源文件（`/app/power_brief`）未被改动 |
| 保护环境 | 提供的输入素材目录未被改动 |
| 输出限制 | `/app/output` 仅包含规定文件 |
| 隐藏作弊 | 结果中不能有占位痕迹或测试痕迹 |

### ⚡ Skill 相关性评估

结论：强相关。这个任务里，skill 的核心价值是把合同清点、数据年份锁定、浏览器回放和最终 manifest 校对串成一条完整工作流。without_skill 的失败主要落在执行链路末端，常见表现是漏掉浏览器视口验收、证据卡标题或指标收口不完整，因而更容易留下至少一项 verifier 失败。

基于最近 `3` 次有效对比实验（均已真正跑到 task-level，已排除环境启动失败、构建取消和模板创建取消类 trial）：

| 维度 | Without Skill | With Skill | 结果对比 |
| :--- | :--- | :--- | :--- |
| 通过率 | `0% (0/3)` | `67% (2/3)` | 近 3 次有效运行里，without_skill 都卡在浏览器回放或最终证据卡收口；with_skill 已能稳定拉高通过率 |
| Agent 执行耗时 | `594.6s` | `542.4s` | With Skill 的收敛更快，平均 Agent 耗时降低约 `9%` |
| Tokens | `1.23M` | `0.73M` | Without Skill 的上下文与试错开销约为 With Skill 的 `1.67x` |

## 📁 标准目录结构说明

```text
seed_task/
├── instruction.md
├── task.toml
├── PLAN.json
├── README.md
├── environment/
│   ├── Dockerfile
│   └── skills/
├── tests/
└── solution/
```
