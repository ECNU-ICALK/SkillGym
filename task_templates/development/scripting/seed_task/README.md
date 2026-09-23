# Scripting Template

这是面向 `scripting` 类 skill 的模板。它综合参考 SkillsMP scripting 类热门 skill 的共性能力：脚本环境确认、可靠的 shell 编排、真实输入处理、失败路径治理、可重复执行和任务级交付校验。

## 第一部分：任务设计参考

* **Skill 价值定位**：scripting 类热门 skill 的核心价值，不只是“写出一段脚本”，而是把真实任务链路变成可运行、可复查、可重跑的自动化交付。对于 `bash-defensive-patterns` 这类 skill，关键点是严格模式、输入校验、安全文件处理、日志与清理，而不是仅靠一次性命令凑出结果。
* **Verifier 设计重点**：Verifier 应覆盖真实输出重算、重复执行稳定性、失败路径清理、并发重入控制、中断恢复、路径安全、输入不可篡改和反硬编码。重点不是卡格式细节，而是确认 solver 真的修好了现有脚本链路，而不是绕开链路、手写结果或只对当前快照打补丁。

## 第二部分：示例任务

### 📌 任务元数据

- 任务 ID：`scripting__airport-report-pipeline`
- 类别：`scripting`
- 绑定 Skill：`bash-defensive-patterns`
- 输入数据参考来源：
  - `environment/data/ourairports/countries.tsv`：任务内国家维表；数据直接来源于  
    `https://raw.githubusercontent.com/davidmegginson/ourairports-data/main/countries.csv`
  - `environment/data/ourairports/regions.tsv`：任务内地区维表；数据直接来源于  
    `https://raw.githubusercontent.com/davidmegginson/ourairports-data/main/regions.csv`
  - `environment/data/ourairports/airports.tsv`：任务内机场事实表；数据直接来源于  
    `https://raw.githubusercontent.com/davidmegginson/ourairports-data/main/airports.csv`
  - `environment/data/ourairports/runways.tsv`：任务内跑道事实表；数据直接来源于  
    `https://raw.githubusercontent.com/davidmegginson/ourairports-data/main/runways.csv`

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

结论：强相关。这个任务里，Skill 的核心价值是把 shell pipeline 的失败传播、路径安全、输入校验、临时目录处理和输出交付方式标准化，从而显著降低试错成本；而 alternate fixture、失败复跑和链路保留约束，可以有效拦住只修表面症状或直接换实现的解法。

基于最近 **4 次** 有效对比实验（均为真正跑到 task-level、存在完整 agent 轨迹；已排除非任务本体失败的 `ReadError` trial）：

| 维度 | Without Skill | With Skill | 结果对比 |
| :--- | :--- | :--- | :--- |
| 通过率 | `0/4` | `2/4` | 近 4 次有效对照里，without Skill 始终卡在共享临时根目录并发隔离与中断清理；with Skill 有 2 次完整通过。 |
| Agent 执行耗时 | `493.6s` | `510.3s` | With Skill 的成功样本会做更完整的诊断与验证，平均耗时略高约 `3.4%`，但换来了明显更高的通过率。 |
| Tokens | `611,481` | `635,147` | With Skill 的平均 token 略高约 `3.9%`；without Skill 更早停在未修复状态，token 反而更低。 |

另有 1 条 `with_skill` E2B run 在 task-level 过程中遭遇 `ReadError`，未计入有效对照统计。

## 📁 标准目录结构说明

```text
seed_task/
├── instruction.md
├── task.toml
├── PLAN.json
├── README.md
├── environment/
│   ├── Dockerfile
│   ├── bin/
│   ├── data/
│   └── skills/
├── tests/
│   ├── fixtures/
│   ├── test.sh
│   ├── test_outputs.py
│   ├── test_guardrails.py
│   └── conftest.py
└── solution/
    ├── fixed/
    └── solve.sh
```
