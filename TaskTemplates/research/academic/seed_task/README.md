# Academic Template

这是面向 `academic` 类 skill 的模板。它综合参考 SkillsMP academic 方向热门 skill 的共性能力：文献筛选、范围判定、结构化证据抽取、方法比较、跨论文综合、研究空白归纳，以及把多篇论文整理成可复核的综述交付物。

## 第一部分：任务设计参考

* **Skill 价值定位**：academic 类热门 skill 的核心价值，是把文献阅读和综述写作收束成一条稳定链路，让 solver 先判断范围，再抽取证据，随后完成跨论文比较和引用收口。对这类模板任务来说，skill 主要帮助减少在筛选标准、证据定位、主题综合和引用一致性上的试错成本。
* **Verifier 设计重点**：Verifier 应优先验证 solver 是否完成了完整文献筛选与综合链路，而不是只写出表面完整的总结。重点应覆盖候选集全量覆盖、范围分类、证据片段落地、跨文件一致性、主题粒度控制和 bibliography 对齐，并用防作弊测试拦下空表、编造引文和候选集外论文。

## 第二部分：示例任务

### 📌 任务元数据

- 任务 ID：`academic__reasoning-method-review-packet`
- 类别：`academic`
- 绑定 Skill：`academic-researcher`
- 输入数据参考来源：
  - `environment/data/metadata/arxiv_id_feed.xml`：任务内 21 篇候选论文元数据；直接来源于 arXiv API 批量查询  
    【https://arxiv.org/api/query?search_query=&start=0&max_results=21&id_list=2201.11903,2203.11171,2205.11916,2205.10625,2210.03493,2210.03350,2211.10435,2211.12588,2301.13379,2305.04091,2305.10601,2308.09687,2303.03103,2307.15337,2203.14465,2210.03629,2302.04761,2303.09014,2304.07919,2305.02317,2307.02477】
  - `environment/data/metadata/candidate_manifest.tsv`：任务内候选论文清单与版本化 arXiv 链接；设计形态参考同批 arXiv 论文页面  
    【https://arxiv.org/abs/2201.11903v6】  
    【https://arxiv.org/abs/2211.10435v2】  
    【https://arxiv.org/abs/2305.10601v2】
  - `environment/data/text/2201.11903.md`：任务内摘要快照；直接来源于对应 arXiv 论文页面  
    【https://arxiv.org/abs/2201.11903v6】
  - `environment/data/text/2211.10435.md`：任务内摘要快照；直接来源于对应 arXiv 论文页面  
    【https://arxiv.org/abs/2211.10435v2】
  - `environment/data/text/2305.10601.md`：任务内摘要快照；直接来源于对应 arXiv 论文页面  
    【https://arxiv.org/abs/2305.10601v2】

### 📊 验证与测试指标（Oracle & Verifier）

- Oracle：按正式流程独立运行并完成交付，结果可直接 100% 通过验证。
- Verifier策略：

主测试
| 测试点 | 验证内容 | 对应skill内化点 |
| :--- | :--- | :--- |
| 候选集全量覆盖 | `screening_decisions.tsv` 必须覆盖全部 21 篇候选论文且每篇只出现一次 | 先做完整文献筛选 |
| 范围分类与纳入集 | 纳入/排除决策、排除原因和纳入论文核心方法标签保持一致 | 依据范围规则做方法筛选 |
| 证据落地 | `scope_anchor` 与 `supporting_text_snippet` 必须能在本地摘要快照中定位 | 从论文文本提取证据 |
| 摘要表与统计一致 | `included_papers.tsv`、`review_summary.json` 与实际纳入集合一致 | 结构化信息抽取与收口 |
| 主题综合粒度 | `theme_map.json` 既要覆盖全部纳入论文，又不能把主题桶做得过粗 | 跨论文综合与主题归纳 |
| 参考文献一致性 | `references.bib` 只包含纳入论文，且与综述正文和表格一致 | 引用整理与交付闭环 |

防作弊测试
| 测试点 | 验证内容 |
| :--- | :--- |
| 空表或缺件 | 不允许缺失任何合同文件，也不允许用空内容规避 |
| 候选集外论文 | 不允许出现 manifest 之外的论文 ID、标题或引文 |
| 编造证据 | 不允许虚构 scope anchor、supporting snippet 或 benchmark 证据 |
| 跨文件断链 | 不允许筛选表、纳入表、主题图、综述和 bibliography 彼此不一致 |
| 旧草稿照抄 | `legacy_screening_notes.tsv` 中已知错误必须被纠正，不能原样继承 |

### ⚡ Skill 相关性评估

结论：强相关。这个任务的关键难点不在于生成长文本，而在于先完成范围筛选，再完成证据抽取、方法比较、主题综合和引用对齐。without_skill 更容易停在主题粒度过粗、旧草稿误用、分类不稳或跨文件断链这类行动/分析级失败上。

基于最近 **3 组** 有效对照实验（均跑到 task-level，已排除启动失败与构建取消类 trial）：

| 维度 | Without Skill | With Skill | 结果对比 |
| :--- | :--- | :--- | :--- |
| 通过率 | `0%` | `100%` | 最近 3 组有效对照里，without_skill 都至少留下 1 项 verifier 失败，主要集中在 `citation_source` 断链、纳入/排除判断漂移，以及主题图把候选外或排除论文重新带回综合结果。 |
| Agent 执行耗时 | `277.7s` | `343.4s` | without_skill 更早停在筛选或综合错误上，因此平均耗时更短；with_skill 会继续完成完整综述交付。 |
| Tokens | `466795` | `369698` | without_skill 的平均 token 开销约为 with_skill 的 `1.26x`，主要消耗在反复重判论文范围和回补跨文件一致性上。 |

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
│   └── skills/
├── tests/
└── solution/
```
