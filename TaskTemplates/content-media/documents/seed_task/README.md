# Documents Template

这是面向 `documents` 类 skill 的模板。它综合参考 SkillsMP documents 类热门 skill 的共性能力：结构化文档交付、现有草稿沿用、内容替换、图表落版、清理审阅残留和可复跑的生成入口。

## 第一部分：任务设计参考

* **Skill 价值定位**：documents 类 skill 的核心价值，是把“把资料写进文档”推进到“沿用既有文档壳完成正式交付”。模板任务应让 skill 在 `.docx` 包结构理解、占位替换、媒体落版、文档清理和交付入口收敛上形成明显帮助。
* **Verifier 设计重点**：Verifier 应同时检查文档内容、文档壳保留、包内媒体替换、清理状态和可复跑入口。重点应覆盖输入不可改、占位文本清除、评论或审阅残留清除、文档与 manifest 一致，以及 alternate fixture 下的泛化能力。

## 第二部分：示例任务

### 📌 任务元数据

- 任务 ID：`documents__north_america_energy_briefing_packet`
- 类别：`documents`
- 绑定 Skill：`docx`
- 输入数据参考来源：
  - `environment/briefing/data/country_profile.json`：任务内国家基础信息；直接来源于  
    【https://api.worldbank.org/v2/country/USA;CAN;MEX?format=json&per_page=100】
  - `environment/briefing/data/world_bank_population.json`：任务内人口数据快照；直接来源于  
    【https://api.worldbank.org/v2/country/USA;CAN;MEX/indicator/SP.POP.TOTL?format=json&per_page=20000】
  - `environment/briefing/data/world_bank_gdp.json`：任务内 GDP 数据快照；直接来源于  
    【https://api.worldbank.org/v2/country/USA;CAN;MEX/indicator/NY.GDP.MKTP.CD?format=json&per_page=20000】
  - `environment/briefing/data/annual_co2_emissions.csv`：任务内年度 CO2 排放数据快照；直接来源于  
    【https://ourworldindata.org/grapher/annual-co2-emissions-per-country.csv?v=1&csvType=full&useColumnShortNames=false】
  - `environment/briefing/data/electricity_prod_source.csv`：任务内电力来源结构数据快照；直接来源于  
    【https://ourworldindata.org/grapher/electricity-prod-source-stacked.csv?v=1&csvType=full&useColumnShortNames=false】

### 📊 验证与测试指标（Oracle & Verifier）

- Oracle：按正式流程独立运行并完成交付，结果可直接 100% 通过验证。
- Verifier 策略：

主测试

| 测试点 | 验证内容 | 对应 skill 内化点 |
| :--- | :--- | :--- |
| 产物生成 | 能成功生成 `.docx` 与清单文件 | 生成标准交付物 |
| 内容写入 | 规定的章节、表格和图表正确写入文档 | 内容编辑能力 |
| 格式保留 | 页眉、页脚、样式和附录未被破坏 | 在已有模板上编辑 |
| 痕迹清理 | 占位符、评论和示例文本被清除 | 清理多余内容 |
| 清单一致 | 章节、图表和数据年份与生成的文档一致 | 保持信息对齐 |
| 多次运行 | 更换输入后，系统能重新生成正确结果 | 流程的可重复性 |

防作弊测试

| 测试点 | 验证内容 |
| :--- | :--- |
| 保护输入 | 源文件（`/app/briefing`）未被篡改 |
| 保护环境 | 提供的 briefing 输入素材未被篡改 |
| 输出限制 | `/app/output` 仅包含规定文件 |
| 隐藏作弊 | 结果中不得有测试标记或占位残留 |

### ⚡ Skill 相关性评估

结论：强相关。这个任务里，Skill 的核心价值是把现有 Word 草稿、OOXML 包编辑、图表替换和清理收尾串成一条可执行路径；如果没有这条路径，agent 更容易把任务做成外部格式导出、另起文档壳，或停在包内媒体替换与残留清理阶段。

基于最近 **3 次** 有效对比实验（round12、round13、round14；均为真正跑到 task-level、存在完整 agent 轨迹；已排除 build cancelled 类 trial），并按最终稳定版 verifier 口径统一判读：

| 维度 | Without Skill | With Skill | 结果对比 |
| :--- | :--- | :--- | :--- |
| 通过率 | `0%` | `100%` | 这 3 次有效对比里，without skill 都停在 `.docx` 包损坏或正式文档结构收尾失败；with skill 在最终 verifier 口径下都能交出完整文档包。 |
| Agent 执行耗时 | `514.8s` | `565.5s` | with skill 为了读取和沿用 `.docx` 工作流，平均执行时长略高，增加约 `9.8%`，但换来了稳定通过。 |
| Tokens | `2.15M` | `3.24M` | with skill 会为 OOXML 结构理解和文档清理投入更多上下文；without skill 虽然 tokens 更低，但仍停在无效交付。 |

## 📁 标准目录结构说明

```text
seed_task/
├── instruction.md
├── task.toml
├── PLAN.json
├── README.md
├── environment/
│   ├── Dockerfile
│   ├── briefing/
│   ├── workspace/
│   └── skills/
├── tests/
│   ├── conftest.py
│   ├── test.sh
│   ├── test_guardrails.py
│   └── test_outputs.py
└── solution/
    └── solve.sh
```
