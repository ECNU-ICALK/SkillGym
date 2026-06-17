# Testing Template

这是面向 browser / E2E testing 类 skill 的模板。它综合参考 SkillsMP testing 分类里高 star 浏览器测试技能的共性能力：围绕首屏状态、异步加载、过滤、详情、比较和导出，构造一个可重复运行、可稳定验证的本地任务。

## 第一部分：任务设计参考

* **Skill 价值定位**：这类 skill 的核心价值，是把浏览器侧验证从单点冒烟提升为可复跑、可定位、可收敛的端到端覆盖。高质量 skill 通常会强化首帧状态判断、延迟内容量测、等待节奏和结果复核。
* **Verifier 设计重点**：verifier 既要确认业务流是否都被覆盖，也要确认断言是否足够深入，能拦下只看终态文本或只做浅层等待的方案。对照实验还要放入局部语义回归点，观察 with_skill 是否更容易命中首帧与稳定性关键路径。

## 第二部分：示例任务

### 📌 任务元数据

- 任务 ID：`testing__airport-ops-console-browser-coverage`
- 类别：`testing`
- 绑定 Skill：`browser-testing`
- 输入数据参考来源：
  - `environment/data/airports.csv`：机场主数据快照；设计形态参考 OurAirports 机场目录  
    【https://ourairports.com/data/airports.csv】
  - `environment/data/countries.csv`：国家代码与名称映射；设计形态参考 OurAirports 国家字典  
    【https://ourairports.com/data/countries.csv】
  - `environment/data/regions.csv`：地区代码与名称映射；设计形态参考 OurAirports 地区字典  
    【https://ourairports.com/data/regions.csv】
  - `environment/data/runways.csv`：跑道明细快照；设计形态参考 OurAirports 跑道目录  
    【https://ourairports.com/data/runways.csv】

### 📊 验证与测试指标（Oracle & Verifier）

- Oracle：按正式流程独立运行并完成交付，结果可直接 100% 通过验证。
- Verifier 策略：

主测试

| 测试点 | 验证内容 | 对应 skill 内化点 |
| :--- | :--- | :--- |
| Dashboard shell | `npm test` 可直接跑通 | 先接入既有测试入口，再扩充覆盖 |
| Theme first paint | 首帧阶段已应用保存主题，且能拦下短暂异常覆盖 | 首帧状态检查 |
| Layout stability | 延迟内容加载时关键元素位置稳定 | 异步 UI 稳定性采样 |
| Detail flow | 覆盖一个机场详情检查 | 详情页业务断言 |
| Compare flow | 覆盖过滤后比较两个机场 | 过滤与比较断言 |
| Export flow | 覆盖过滤后导出当前列表 | 导出与下载行为 |
| Hidden theme regression | `theme-flicker` 下复跑失败 | 首帧主题回归拦截 |
| Hidden layout regression | `insights-layout-shift` 下复跑失败 | 位置漂移回归拦截 |
| Hidden export regression | `export-us-12000-klax-region-bug` 下复跑失败 | 导出内容回归拦截 |
| Server wiring guardrail | 不得在测试里改走另一条 server 启动路径 | 保持 mutation 与审计链路可见 |

防作弊测试

| 测试点 | 验证内容 |
| :--- | :--- |
| App immutability | 测试区外应用文件不可修改 |
| Data immutability | 输入数据不可修改 |
| Server wiring | 测试不得自起并替换仓库既有 server wiring |
| Journey logging | access log 必须显示 detail / compare / export 都被走到 |

### ⚡ Skill 相关性评估

结论：强相关。这个任务的核心价值，是把首屏主题、延迟内容稳定性、详情、比较和导出串成一条可复跑的浏览器验证链。`browser-testing` 类 skill 的价值，主要体现在更稳的首帧判断、更少的无效试错和更高的关键路径命中率。

基于最近 **5** 次有效对比实验（均为真正跑到 task-level、存在完整 agent 轨迹；已排除启动失败类 trial，按最终版 verifier 口径重算）：

| 维度 | Without Skill | With Skill | 结果对比 |
| :--- | :--- | :--- | :--- |
| 通过率 | `0%` | `80%` | without_skill 常见失败集中在首帧主题与延迟稳定性验证链路，部分 trial 还漏掉 detail 回归或 theme-flicker 拦截；with_skill 更容易补齐整条浏览器验证路径 |
| Agent 执行耗时 | `397.7s` | `528.4s` | with_skill 会花更多时间完成首帧采样、稳定性量测和导出复核；without_skill 往往更早失败 |
| Tokens | `968176` | `1947242` | with_skill 上下文投入更高，但换来了明显更高的通过率和更完整的验证闭环 |

## 📁 标准目录结构说明

```text
seed_task
├── instruction.md
├── task.toml
├── PLAN.json
├── README.md
├── environment
│   ├── Dockerfile
│   ├── data
│   ├── skills
│   └── workspace
├── tests
└── solution
```
