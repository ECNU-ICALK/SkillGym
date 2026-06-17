# Mobile Template

这是面向 `mobile` 类 skill 的模板。它综合参考 SkillsMP `mobile` 类热门 skill 的共性能力：移动端交互收口、再次进入体验、缓存更新策略、快捷入口、弱网可用性，以及把公开数据驱动的应用交付成可运行结果。

## 第一部分：任务设计参考

* **Skill 价值定位**：`mobile` 类热门 skill 的共同价值，在于把移动端场景下容易分散的交付点串起来，例如狭窄视口、再次进入、状态恢复、快捷入口和资源加载策略。高质量 skill 不应直接给出答案，而应帮助 solver 更快识别要补哪条链路、哪些状态需要保留、哪些更新必须在线优先。
* **Verifier 设计重点**：Verifier 应优先验证 solver 是否完成了移动端主链路和关键行为，避免把主要判定压力放在文案格式上。重点应覆盖当前数据更新、再次进入链路、离线说明页、快捷入口元数据、移动视口可操作性、状态提示一致性，以及对硬编码结果、输入篡改和缓存策略错误的防护。

## 第二部分：示例任务

### 📌 任务元数据

- 任务 ID：`mobile__citibike-commuter-reentry-pwa`
- 类别：`mobile`
- 绑定 Skill：`progressive-web-app`
- 输入数据参考来源：
  - `environment/data/system_information.json`：任务内系统信息  
    https://gbfs.citibikenyc.com/gbfs/en/system_information.json
  - `environment/data/station_information.json`：任务内站点元数据  
    https://gbfs.citibikenyc.com/gbfs/en/station_information.json
  - `environment/data/station_status.json`：任务内站点状态数据  
    https://gbfs.citibikenyc.com/gbfs/en/station_status.json

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

结论：强相关，但 solver 收敛仍受执行质量影响。这个任务里，Skill 的核心价值是把快捷入口、再次进入、离线说明页、在线更新和状态提示这几条移动 Web 高成本链路标准化；without Skill 会稳定丢失离线再次进入或离线说明页，而 with Skill 仍可能在站点详情链路或 manifest 合同上失手。

基于最近 **3** 次有效对照实验（均为真正跑到 task-level、存在完整 agent 轨迹；已排除启动失败类 trial）：

| 维度 | Without Skill | With Skill | 结果对比 |
| :--- | :--- | :--- | :--- |
| 通过率 | `0%` | `33.3%` | 近 3 次有效对照里，without Skill 全部失败；失败点集中在离线再次进入首页和离线说明页，with Skill 有 1 次完整通过、2 次停在详情链路或 manifest 合同遗漏。 |
| Agent 执行耗时 | `573.2s` | `656.7s` | Without Skill 更早停在未完成状态，因此平均耗时更低；With Skill 在完整链路上投入更多诊断与实现时间。 |
| Tokens | `1.51M` | `1.61M` | Without Skill 较早收束到不完整解法，tokens 略低；With Skill 为补齐完整行为链路承担了更高上下文和实现开销。 |

## 📁 标准目录结构说明

```text
seed_task/
├── instruction.md
├── task.toml
├── PLAN.json
├── environment/
│   ├── Dockerfile
│   ├── app/
│   ├── data/
│   ├── services/
│   ├── scripts/
│   └── skills/
├── tests/
└── solution/
```
