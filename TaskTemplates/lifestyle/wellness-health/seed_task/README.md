# Wellness-Health Template

这是面向 `wellness-health` 类 skill 的模板。它综合参考 SkillsMP wellness-health 类热门 skill 的共性能力：把公开条件数据、活动安排、场地约束、参与者支持需求和交付沟通收拢成一条可执行的活动计划链路。

## 第一部分：任务设计参考

* **Skill 价值定位**：wellness-health 类热门 skill 常见价值，是把“当前条件是否允许这样安排”这件事说清楚，并把需要调整的动作落到场地、时段、提醒信息和执行交接上。模板题面要把交付合同说清楚，把判定细节尽量留给 skill 和 solver 自己识别。
* **Verifier 设计重点**：Verifier 应重点检查 solver 是否做出了正确的调度动作，例如换场地、改时段、降暴露等级或保留合规安排，并验证结果是否满足容量、开放时间、活动限制和支持需求。它还应拦截只看较早导出、跳过本地权威服务、删 session 规避约束或硬编码答案等捷径。

## 第二部分：示例任务

### 📌 任务元数据

- 任务 ID：`wellness-health__weather-safe-community-schedule`
- 类别：`wellness-health`
- 绑定 Skill：`weather-safety-guardrails`
- 输入数据参考来源：
  - `environment/service_seed/conditions_hourly.json`：任务内当前条件快照；设计形态参考 NOAA hourly forecast、Open-Meteo weather forecast 与 Open-Meteo air quality  
    https://api.weather.gov/points/30.2672,-97.7431  
    https://api.weather.gov/gridpoints/EWX/156,91/forecast/hourly  
    https://api.open-meteo.com/v1/forecast?latitude=30.2672&longitude=-97.7431&hourly=apparent_temperature,uv_index,precipitation_probability&timezone=America%2FChicago&forecast_days=3  
    https://air-quality-api.open-meteo.com/v1/air-quality?latitude=30.2672&longitude=-97.7431&hourly=us_aqi,pm2_5,ozone&timezone=America%2FChicago&forecast_days=3
  - `environment/data/venue_catalog.csv`：任务内场地目录；设计形态参考 Austin 官方场地页面  
    https://www.austintexas.gov/parks/austin-recreation-center  
    https://www.austintexas.gov/department/givens-recreation-center  
    https://www.austintexas.gov/department/Big-stacy-pool
  - `environment/data/class_requests.csv`：任务内课程需求与调整偏好；为任务原创业务输入，无单独公开数据链接
  - `environment/data/site_constraints.json`：任务内运营规则与告知对象范围；为任务原创业务输入，无单独公开数据链接
  - `environment/data/reference_weather_snapshot.json`：任务内较早天气导出；由同一公开来源整理出的早期版本
  - `environment/data/reference_air_quality_snapshot.json`：任务内较早空气质量导出；由同一公开来源整理出的早期版本

### 📊 验证与测试指标（Oracle & Verifier）

- Oracle：按正式流程独立运行并完成交付，结果可直接 100% 通过验证。
- Verifier策略：

主测试

| 测试点 | 验证内容 | 对应skill内化点 |
| :--- | :--- | :--- |
| 输出契约 | 检查 4 个输出文件存在、可解析，并包含必需字段、列名和标题 | 先理解交付合同，再组织可交付结果 |
| Session 评估 | 检查每个 session 的风险等级、调整决策、原因码和推荐窗口 | 识别条件变化对活动安排的影响 |
| 正式排期 | 检查最终时段、场地、暴露等级、容量、开放时间、活动限制和支持需求 | 做出正确的换场地、改时段、降暴露等级动作 |
| 提醒信息 | 检查每个 session 都有对应告知，且与最终安排一致 | 输出可执行的参与者提醒 |
| Handoff 一致性 | 检查运营 handoff 是否覆盖主要风险、变更项和场地备注 | 把计划调整交接给执行方 |

防作弊测试

| 测试点 | 验证内容 |
| :--- | :--- |
| 本地权威链路 | 访问日志必须证明 solver 查询了本地 planning service，且覆盖全部计划日期 |
| 输入与隐藏资产保护 | `/root/data/`、隐藏 service 与 seed 数据不得变化；verifier 结束时服务仍健康 |

### ⚡ Skill 相关性评估

结论：强相关。这个任务里，Skill 的核心价值，是把条件风险转化成明确调度动作，并提醒 solver 同时顾及场地约束与参与者支持；缺少 skill 时，更容易停在“继续保留原排期”这类行动失误上。

基于最近 **3** 次有效对比实验（均为真正跑到 task-level、存在完整 agent 轨迹；已排除启动失败类 trial）：

| 维度 | Without Skill | With Skill | 结果对比 |
| :--- | :--- | :--- | :--- |
| 通过率 | `待补` | `待补` | 待补 |
| Agent 执行耗时 | `待补` | `待补` | 待补 |
| Tokens | `待补` | `待补` | 待补 |

## 📁 标准目录结构说明

```text
模板任务：
├── instruction.md          # 任务说明（仅包含症状、业务约束和禁止事项）
├── task.toml               # 任务元数据（标签、技能要求、运行入口）
├── PLAN.json               # 任务构建过程的结构化元信息
├── environment/            # 运行环境
│   ├── Dockerfile          # 单容器镜像定义；在同一容器内启动本地 planning service
│   ├── ...                 # 可选的 data / seed / scripts
│   └── skills/             # 任务绑定的 wellness-health skill 定义
├── tests/                  # Verifier 与 Guardrail 测试集
└── solution/               # 官方参考解法及 solve.sh
```
