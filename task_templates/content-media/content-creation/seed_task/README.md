# Content Creation Template

这是面向 `content-creation` 类 skill 的模板。它综合参考 SkillsMP content-creation 类热门 skill 的共性能力：把一组资料、主张清单和风格样本整理成多渠道发布内容，并在固定交付合同下保持语气、证据和渠道区分。

## 第一部分：任务设计参考

* **Skill 价值定位**：content-creation 类 skill 的核心价值，在于把“材料已经齐了，但还缺成稿与分发版本”的工作推进到“交出可审阅、可发布、可复跑的内容包”。模板任务应让 skill 在主判断提炼、段落推进、语气继承、渠道改写和证据落点上形成明显帮助。
* **Verifier 设计重点**：Verifier 应同时检查正式产物、claim 对齐、manifest 完整性、渠道紧凑度、风格继承和 rerun 灵敏度。重点应覆盖固定输出合同、证据引用、thread 的紧凑表达、video 的字幕松紧，以及更换输入后能否跟随更新。

## 第二部分：示例任务

### 📌 任务元数据

- 任务 ID：`content_creation__renewable_capacity_publication_pack`
- 类别：`content-creation`
- 绑定 Skill：`article-writing`
- 输入数据参考来源：
  - `environment/campaign/data/source_manifest.json`：任务内来源目录与引用链接；直接整理自  
    【https://www.irena.org/Publications/2025/Mar/Renewable-Capacity-Statistics-2025】  
    【https://www.iea.org/reports/from-taking-stock-to-taking-action-the-roadmaps-to-tripling-renewables-by-2030】  
    【https://www.iea.org/reports/tripling-renewable-power-by-2030】  
    【https://ourworldindata.org/grapher/electricity-prod-source-stacked.csv?v=1&csvType=full&useColumnShortNames=false】
  - `environment/campaign/data/claim_bank.json`：任务内核心数字、主张和 claim id；数据直接整理自  
    【https://www.irena.org/Publications/2025/Mar/Renewable-Capacity-Statistics-2025】  
    【https://www.iea.org/reports/from-taking-stock-to-taking-action-the-roadmaps-to-tripling-renewables-by-2030】  
    【https://www.iea.org/reports/tripling-renewable-power-by-2030】  
    【https://ourworldindata.org/grapher/electricity-prod-source-stacked.csv?v=1&csvType=full&useColumnShortNames=false】
  - `environment/campaign/data/source_extracts.json`：任务内证据摘录与措辞支点；内容直接整理自  
    【https://www.irena.org/Publications/2025/Mar/Renewable-Capacity-Statistics-2025】  
    【https://www.iea.org/reports/from-taking-stock-to-taking-action-the-roadmaps-to-tripling-renewables-by-2030】  
    【https://www.iea.org/reports/tripling-renewable-power-by-2030】

### 📊 验证与测试指标（Oracle & Verifier）

- Oracle：按正式流程独立运行并完成交付，结果可直接 100% 通过验证。
- Verifier 策略：

主测试

| 测试点 | 验证内容 | 对应 skill 内化点 |
| :--- | :--- | :--- |
| 正式构建入口 | `build_content_pack.py` 能稳定生成 5 个指定产物 | 固定交付流程 |
| manifest 对齐 | `content_manifest.json` 的 key、deliverables、claim_support_notes 完整对齐合同 | 结构化交付与来源说明 |
| 渠道化改写 | newsletter、LinkedIn、thread、video 都满足各自长度与结构约束 | 多渠道改写与节奏控制 |
| 证据落点 | 关键数字、claim id 和 source id 都来自打包输入且落点正确 | 证据先行写作 |
| 风格继承 | newsletter 能沿用 house style，LinkedIn 能保留 business reader 角度 | 语气继承与受众对齐 |
| 紧凑表达 | thread 保持紧凑步进，video 的 `On-screen text` 比 `Voiceover` 更紧 | 渠道压缩与节奏管理 |

防作弊测试

| 测试点 | 验证内容 |
| :--- | :--- |
| 保护输入 | `/app/campaign` 打包输入内容未被篡改 |
| 输出限制 | `/app/output` 仅包含规定文件 |
| 输出清洁 | 结果里不得含 `verifier`、`TODO`、`TBD`、模板占位残留 |

### ⚡ Skill 相关性评估

结论：强相关。这个任务里，Skill 的核心价值是把长内容写作里的受众判断、证据落点、渠道改写和 thread 论证顺序收拢成稳定流程；没有 Skill 时，agent 更容易在 thread 的推进顺序和 manifest 交付边界上跑偏。当前主测试把这些行动层问题单独卡住，因此能稳定区分“写出了内容”和“按既定写作工作流交出了合格内容包”。

基于最近 **3** 次有效对比实验（均为真正跑到 task-level、存在完整 agent 轨迹；已排除启动失败类 trial）：

| 维度 | Without Skill | With Skill | 结果对比 |
| :--- | :--- | :--- | :--- |
| 通过率 | `0% (0/3)` | `100% (3/3)` | 近 3 次有效对照里，without Skill 都留下主测试失败，主要集中在 thread 论证顺序、claim 落点和 manifest 交付边界 |
| Agent 执行耗时 | `584.3s` | `491.1s` | With Skill 的收敛更快，平均 Agent 耗时降低约 `16.0%` |
| Tokens | `404,665` | `395,998` | Without Skill 的上下文与试错开销略高，平均总 tokens 约为 With Skill 的 `1.02x` |

## 📁 标准目录结构说明

```text
seed_task/
├── instruction.md
├── task.toml
├── PLAN.json
├── README.md
├── environment/
│   ├── Dockerfile
│   ├── campaign/
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
