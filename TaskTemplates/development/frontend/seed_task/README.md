# Frontend Template

这是面向 Frontend 类 skill 的模板。它综合参考 SkillsMP Frontend 类热门 skill 的共性能力：组件组合、共享状态治理、URL 与页面状态同步、按需加载、键盘与焦点可访问性，以及在真实数据链路下修复运行时前端回归。

## 第一部分：任务设计参考

* **Skill 价值定位**：Frontend 类热门 skill 的核心价值，不是把页面“修到能看”，而是把组件结构、状态所有权、导航同步、性能边界和可访问交互变成稳定的工程模式。它帮助 solver 更快识别哪些 UI 症状其实来自状态源分裂、错误的加载时机或不完整的交互闭环。
* **Verifier 设计重点**：Verifier 应优先验证真实前端行为，而不是只看静态 DOM 形状。重点包括 URL 与 UI 状态是否一致、最后一次用户意图是否覆盖旧状态、重型代码是否只在需要时加载、键盘与焦点是否形成闭环，以及在变体数据和历史导航下是否仍然稳定。

## 第二部分：示例任务

### 📌 任务元数据

- 任务 ID：`react-energy-workbench-state-regressions`
- 类别：`Frontend`
- 绑定 Skill：`frontend-patterns`
- 输入数据参考来源：
  - `environment/data/owid_energy_snapshot.csv`：任务内国家年度能源指标快照；直接裁剪自 Our World in Data energy dataset  
    https://raw.githubusercontent.com/owid/energy-data/master/owid-energy-data.csv
  - `environment/data/owid_energy_codebook.csv`：任务内指标说明与单位；直接裁剪自 Our World in Data energy codebook  
    https://raw.githubusercontent.com/owid/energy-data/master/owid-energy-codebook.csv
  - `environment/data/world_bank_countries.json`：任务内国家地区与收入组元数据；直接来源于 World Bank Country API  
    https://api.worldbank.org/v2/country?format=json&per_page=400

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

结论：强相关。这个任务里，`frontend-patterns` 的核心价值不在于提示某个单点 bug，而在于更稳定地引导 solver 把 URL、共享状态、派生视图、按需加载和键盘焦点当成同一条前端状态链来修。新增的“当前查看上下文”恢复要求，会继续拦下只修表面筛选或只补局部组件行为的解法。

基于最近 **3** 次有效对比实验（`p6`、`p8`、`p9`；均真正跑到 task-level、存在完整 agent 轨迹，已排除 `BuildException` / 构建取消类 trial）：

| 维度 | Without Skill | With Skill | 结果对比 |
| :--- | :--- | :--- | :--- |
| 通过率 | `0%` | `66.7%` | 近 3 次有效对照里，without Skill 没有一次完整通过；主要失败集中在共享状态恢复、派生摘要一致性和抽屉交互闭环，而 with Skill 有 2 次完整通过。 |
| Agent 执行耗时 | `578.2s` | `549.2s` | With Skill 的诊断和收敛更快，平均 Agent 执行耗时降低约 `5.0%`。 |
| Tokens | `1.35M` | `1.41M` | 这 3 轮里 With Skill 的平均 tokens 略高约 `4.4%`；但这些额外开销换来了显著更高的通过率，而 without Skill 仍停留在动作级失败。 |

## 📁 标准目录结构说明

```text
模板任务：
├── instruction.md
├── task.toml
├── PLAN.json
├── README.md
├── environment/
│   ├── Dockerfile
│   ├── app/
│   ├── data/
│   ├── energy-api/
│   └── skills/
├── tests/
└── solution/
```
