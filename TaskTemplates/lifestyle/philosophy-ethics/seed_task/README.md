# Philosophy Ethics Template

这是面向 `philosophy-ethics` 类 skill 的模板。它综合参考 SkillsMP philosophy-ethics 类热门 skill 的共性能力：围绕公共治理问题、公开政策材料、结构化证据和受约束的决策交付物，完成问题重述、关键分歧识别、风险与控制收束，以及可复跑的决策包生成。

## 第一部分：任务设计参考

* **Skill 价值定位**：philosophy-ethics 类热门 skill 的共同价值，不在于给出漂亮观点，而在于帮助 Agent 把复杂判断拆回约束、前提、证据、利益相关方和后续动作。高质量模板应让 skill 在“怎样把一个模糊判断变成可交付决策包”上形成稳定帮助。
* **Verifier 设计重点**：Verifier 应优先验证 solver 是否沿同一套本地材料完成选项判断、问题登记、假设优先级、控制映射、bundle 汇总和 memo 收口，并检查替代输入下结论是否重算。重点应放在决策链路是否闭合，而不是表层文风。

## 第二部分：示例任务

### 📌 任务元数据

- 任务 ID：`philosophy-ethics__k12-genai-decision-packet`
- 类别：`philosophy-ethics`
- 绑定 Skill：`axiom`
- 输入数据参考来源：
  - `environment/data/reference/unesco_guidance.md`：任务内教育治理约束摘要；设计形态参考 UNESCO《Guidance for generative AI in education and research》  
    【https://unesdoc.unesco.org/in/rest/annotationSVC/DownloadWatermarkedAttachment/attach_import_ab3dfd25-729d-41e8-877f-176076322557?_=386693eng.pdf&from=1&to=48】
  - `environment/data/reference/doe_future_teaching_learning.md`：任务内美国教育场景治理摘要；设计形态参考 U.S. Department of Education OET AI 报告  
    【https://www.ed.gov/sites/ed/files/documents/ai-report/ai-report.pdf】
  - `environment/data/reference/doe_leader_toolkit.md`：任务内教育领导者治理摘要；数据直接来源于 U.S. Department of Education toolkit  
    【https://files.eric.ed.gov/fulltext/ED661924.pdf】
  - `environment/data/reference/privacy_terms.md`：任务内学生隐私与服务条款摘要；设计形态参考 PTAC best practices 与 model terms  
    【https://studentprivacy.ed.gov/resources/protecting-student-privacy-while-using-online-educational-services-requirements-and-best】  
    【https://studentprivacy.ed.gov/resources/protecting-student-privacy-while-using-online-educational-services-model-terms-service】
  - `environment/data/reference/nist_oecd_accessibility.md`：任务内风险治理与系统分类摘要；设计形态参考 NIST AI RMF、NIST GenAI profile、OECD AI classification、ADA rule fact sheet  
    【https://doi.org/10.6028/NIST.AI.100-1】  
    【https://doi.org/10.6028/NIST.AI.600-1】  
    【https://doi.org/10.1787/cb6d9eca-en】  
    【https://www.ada.gov/resources/2024-03-08-web-rule/】
  - `environment/data/reference/pew_usage.md`：任务内 adoption pressure 摘要；数据直接来源于 Pew teen ChatGPT schoolwork article  
    【https://www.pewresearch.org/short-reads/2025/01/15/about-a-quarter-of-us-teens-have-used-chatgpt-for-schoolwork-double-the-share-in-2023/】

### 📊 验证与测试指标（Oracle & Verifier）

- Oracle：按正式流程独立运行并完成交付，结果可直接 100% 通过验证。
- Verifier策略：

主测试
| 测试点 | 验证内容 | 对应skill内化点 |
| :--- | :--- | :--- |
| 正式产物生成 | 单一 build 入口生成全部交付物 | 把判断链路收敛到正式出口 |
| 选项判断 | `option_assessment.tsv` 与 oracle 重算一致 | 识别约束、挑战表面可行性 |
| 问题与控制闭环 | `decision_issues.tsv` 与 `safeguard_plan.yaml` 对齐 | 从核心分歧走到具体控制 |
| 假设审计 | `assumption_audit.tsv` 需要体现层次、类型、风险排序，并把 Top 3 接到 `monitoring` | 从隐含前提走到可验证问题 |
| bundle 汇总 | `decision_bundle.json` 与 memo 的 recommendation、rejected outcomes、open questions 一致 | 重建最终结论并保持一致 |
| 替代输入泛化 | 改动 budget cap 后重新运行，selected outcome 必须变化 | 不能把结论写死，必须基于输入重算 |

防作弊测试
| 测试点 | 验证内容 |
| :--- | :--- |
| 输入不可变 | `/root/data` 哈希不变 |
| Skill 可用性 | 运行时可发现 `axiom`，帮助组织假设审计、风险排序与决策收束 |
| 输出白名单 | `/root/output` 顶层只保留规定产物 |
| 临时文本清理 | 不允许出现 TODO、临时说明或测试痕迹 |

### ⚡ Skill 相关性评估

结论：强相关。这个任务里，Skill 的核心价值不在于生成更长的 memo，而在于把“公开治理决策”拆成可量化的假设审计、风险排序和后续监控闭环。当前示例任务里，without skill 更容易把假设表写成定性描述或把高风险项停在表层硬约束上，with skill 更容易收敛到可执行的假设矩阵与 handoff-ready packet。

基于最近 **3** 次有效对比实验：

| 维度 | Without Skill | With Skill | 结果对比 |
| :--- | :--- | :--- | :--- |
| 通过率 | `0%` | `100%` | 最近 3 次有效对照里，without Skill 都在 `assumption_audit.tsv` 的定量风险矩阵上保留 verifier 失败；with Skill 3 次都满足当前最终版 verifier |
| Agent 执行耗时 | `452.7s` | `376.6s` | With Skill 的平均 Agent 耗时更低，下降约 `16.8%` |
| Tokens | `601266` | `454966` | Without Skill 的上下文与试错开销约为 With Skill 的 `1.32x` |

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
│   ├── skills/
│   └── workspace/
├── tests/
└── solution/
```
