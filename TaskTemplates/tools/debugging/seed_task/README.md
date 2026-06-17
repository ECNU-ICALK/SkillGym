# Debugging Template

这是面向 `debugging` 类 skill 的模板。它综合参考 SkillsMP debugging 类热门 skill 的共性能力：性能捕获分析、构建与运行时诊断、根因定位、证据归纳、差异对比和工程交接。

## 第一部分：任务设计参考

* **Skill 价值定位**：debugging 类 skill 的核心价值，是把症状、日志、profile、trace 和运行时信号组织成一条可复查的调查链路。模板任务应让 skill 在证据收集、根因缩圈、差异判断和交接表达上体现价值，而不要把调查步骤直接泄露到题面里。
* **Verifier 设计重点**：Verifier 应优先从输入重算关键事实，并验证 Agent 是否识别了真正决定性的故障信号、是否保持跨文件一致性、是否引用了正确证据，以及是否遵守了不可修改输入和不可绕开链路的约束。重点应覆盖输出 schema、关键指标容差、根因排序、证据引用、输入不可变和防占位答案，而不是只做固定文案比对。

## 第二部分：示例任务

### 📌 任务元数据

- 任务 ID：`flight-dashboard-route-explorer-investigation`
- 类别：`debugging`
- 绑定 Skill：`cpu-profile-analysis`
- 输入数据参考来源：
  - `environment/data/flights.csv`：任务内航班与延误快照；设计形态参考 Vega Datasets 航班样本  
    【https://raw.githubusercontent.com/vega/vega-datasets/master/data/flights-10k.json】
  - `environment/data/airports.csv`：任务内机场元数据；设计形态参考 Vega Datasets 机场样本  
    【https://raw.githubusercontent.com/vega/vega-datasets/master/data/airports.csv】

### 📊 验证与测试指标（Oracle & Verifier）

- Oracle：按正式流程独立运行并完成交付，结果可直接 100% 通过验证。
- Verifier 策略：

主测试

| 测试点 | 验证内容 | 对应 skill 内化点 |
| :--- | :--- | :--- |
| 输出文件与 schema | 检查必需文件、字段、章节顺序和目录清洁度 | 结构化调查交付 |
| 时间线复算 | 从 profile 和 trace 重算 reference/affected duration 与 gap | 时间窗口与路径对比 |
| 根因识别 | 检查 3 条 finding 是否指向受影响路径特有热点，而不是共享基础成本 | 差异化瓶颈定位 |
| 证据一致性 | 检查 evidence_files、signals、Markdown 叙述和 JSON 内容是否一致 | 证据归纳与 handoff |

防作弊测试

| 测试点 | 验证内容 |
| :--- | :--- |
| 输入 hash 校验 | 防止修改数据、capture、源码或 skill 规避难点 |
| 占位与伪造证据校验 | 防止提交空泛结论、虚构文件名或与 capture 不匹配的信号 |
| 额外输出文件校验 | 防止绕开指定交付合同 |

### ⚡ Skill 相关性评估

结论：强相关。这个任务里，Skill 的核心价值是把 `.cpuprofile`、trace 和路径对比组织成稳定调查流程，从而减少把共享基础成本误判成根因的风险。without skill 的常见风险会落在行动层，例如没有正确比较 reference 与 affected path、遗漏 rendering 侧证据、或提交的 signals 与 capture 内容不一致。

基于最近 **3 次有效 with_skill trial 与 3 次有效 without_skill trial**：

| 维度 | Without Skill | With Skill | 结果对比 |
| :--- | :--- | :--- | :--- |
| 通过率 | `0/3 (0%)` | `3/3 (100%)` | without Skill 的失手点集中在受影响阶段切分、phase 命名和 sampled stack 对齐；with Skill 三次都完成了证据闭环。 |
| Agent 执行耗时 | `303.7s` | `336.8s` | without Skill 往往更早结束，但会带着 verifier 缺口退出；with Skill 耗时略高，换来稳定通过。 |
| Tokens | `339,095` | `372,286` | with Skill 会花更多 token 做 profile/trace 对照与交接整理，但输出质量更稳定。 |

## 📁 标准目录结构说明

```text
seed_task/
├── instruction.md
├── task.toml
├── PLAN.json
├── README.md
├── environment/
│   ├── Dockerfile
│   ├── app/
│   ├── data/
│   ├── artifacts/
│   └── skills/
├── tests/
└── solution/
```
