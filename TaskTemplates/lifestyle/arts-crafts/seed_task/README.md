# Arts-Crafts Template

这是面向 `arts-crafts` 类 skill 的模板。它综合参考 SkillsMP arts-crafts 类热门 skill 的共性能力：围绕公开作品库做候选检索、筛选可交付模型、保留作者与许可信息、落本地文件目录，并把结果整理成可交接的制作材料。

## 第一部分：任务设计参考

* **Skill 价值定位**：arts-crafts 类热门 skill 的价值，通常体现在把分散的作品线索、材料约束、许可边界和交付目录组织成一条可执行的制作路径。对 printable / maker 子类来说，skill 的重点是帮助 solver 找到合适模型、补齐出处与许可、拿到文件并留下交接记录。
* **Verifier 设计重点**：Verifier 应优先验证 solver 是否完成了关键动作链，而不是只看文件名对不对。重点应覆盖来源链路访问、选型规则重算、许可与热度判断、下载文件存在性与校验值，以及拦截手写清单、跳过来源服务、篡改输入或替换文件包等捷径。

## 第二部分：示例任务

### 📌 任务元数据

- 任务 ID：`arts-crafts__fiber-workshop-printable-bundle`
- 类别：`arts-crafts`
- 绑定 Skill：`find-stl`
- 输入数据参考来源：
  - `environment/data/catalog/search_terms.json`：任务内查询提示；检索词设计参考 Printables 的 knit / crochet tag 浏览方式  
    <https://www.printables.com/tag/knit>  
    <https://www.printables.com/tag/crochethook>
  - `environment/data/catalog/candidate_shortlist.json`：任务内候选模型摘要；内容形态参考以下公开模型页  
    <https://www.printables.com/model/354172-yarn-bowl>  
    <https://www.printables.com/model/25823-open-stitch-marker>  
    <https://www.printables.com/model/100186-lockable-stitch-marker>  
    <https://www.printables.com/model/151345-knitting-needle-crochet-hook-holder-v2>  
    <https://www.printables.com/model/178406-crochet-hook-storage-box-1>  
    <https://www.printables.com/model/197262-stitch-marker-box-1>
  - `environment/data/brief/workshop_bundle.json`：任务内槽位目标与交付要求；为本任务编排的本地说明文件，无单独公开链接
  - `environment/data/policy/bundle_rules.json`：任务内许可与筛选规则；为本任务编排的本地规则文件，无单独公开链接

### 📊 验证与测试指标（Oracle & Verifier）

- Oracle：按正式流程独立运行并完成交付，结果可直接 100% 通过验证。
- Verifier策略：

主测试

| 测试点 | 验证内容 | 对应skill内化点 |
| :--- | :--- | :--- |
| 输出合同 | 检查 4 个正式产物、3 个槽位目录和 `model_record.json` 结构是否完整 | 先理解交付物，再组织目录 |
| 选型重算 | 根据 policy 和来源服务数据重算每个槽位的入选模型 | 搜索候选、核对规则、做最终筛选 |
| 文件校验 | 核对下载后的文件集合与哈希值是否与来源服务一致 | 不能只写清单，必须拿到文件 |
| 汇总一致性 | 检查 bundle manifest、audit 和 report 之间的模型、槽位和来源字段是否一致 | 结构化交付与登记闭环 |

防作弊测试

| 测试点 | 验证内容 |
| :--- | :--- |
| 来源链路访问 | 访问日志必须证明 solver 进行了搜索、详情查询、下载链接解析和文件下载 |
| 输入与服务保护 | 公共数据、来源服务代码和镜像文件不可修改，服务在 verifier 结束时仍健康 |

### ⚡ Skill 相关性评估

结论：强相关。这个任务里，Skill 的核心价值是把“找模型、看详情、拉文件、留出处与许可记录”这条动作链标准化，从而减少 solver 在本地来源服务协议和文件交付环节上的试错成本。对照实验里，without Skill 的主要失分集中在跳过规范来源链路、使用不安全 localhost/TLS 绕路，以及未稳定拿到完整文件证据，属于动作层失败。

基于最近 **3** 次有效对比实验（均为真正跑到 task-level、存在完整 agent 轨迹；已排除启动失败类 trial）：

| 维度 | Without Skill | With Skill | 结果对比 |
| :--- | :--- | :--- | :--- |
| 通过率 | `0% (0/3)` | `100% (3/3)` | 近 3 次有效对照里，without Skill 均因来源链路与下载动作不完整而失败；with Skill 稳定完成全链路交付 |
| Agent 执行耗时 | `299.0s` | `222.7s` | With Skill 的诊断与收敛更快，平均 Agent 耗时降低约 `25.5%` |
| Tokens | `713254` | `598149` | Without Skill 的上下文与试错开销约为 With Skill 的 `1.19x` |

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
│   ├── mirror/
│   ├── services/
│   └── skills/
├── tests/
│   ├── test.sh
│   ├── test_helpers.py
│   ├── test_outputs.py
│   └── test_guardrails.py
└── solution/
    ├── fixed/
    └── solve.sh
```
