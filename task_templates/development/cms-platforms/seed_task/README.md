# CMS Platforms Template

这是面向 `cms-platforms` 类 skill 的模板。它综合参考 SkillsMP `cms-platforms` 类热门 skill 的共性能力：搭建内容模型、整理导入链路、约束发布与权限边界，并向前台提供可消费的数据接口。

## 第一部分：任务设计参考

* **Skill 价值定位**：这类热门 skill 的共同价值，在于帮助 Agent 沿着 CMS 平台的主工作流完成 collections、relationships、draft/publish、access control 与 feed/query 设计。高质量模板应让 skill 在内容模型、行为约束、行级可见范围和接口拼装上提供帮助，而不是把任务压成纯脚本生成或简单格式修改。
* **Verifier 设计重点**：Verifier 应优先验证 solver 是否沿着内容导入、关系建模、发布控制、接口过滤和角色授权这条链路完成交付，并检查输出文件与接口结果之间的一致性。对于这类 skill，还应重点验证 local API、draft/publish、row-level access 和草稿工作队列的执行结果，而不是只看静态文件是否存在。

## 第二部分：示例任务

### 📌 任务元数据
- 任务 ID：`cms-platforms__met-highlight-feed`
- 类别：`cms-platforms`
- 绑定 Skill：`payload`
- 输入数据参考来源：
  - `environment/data/met_departments.json`：任务内部门数据；设计形态参考 The Met Collection API departments endpoint  
    【https://collectionapi.metmuseum.org/public/collection/v1/departments】
  - `environment/data/met_object_details.ndjson`：任务内馆藏对象详情快照；设计形态参考 The Met Collection API object endpoint  
    【https://metmuseum.github.io/】
  - `environment/data/met_objects_seed.csv`：任务内对象种子与编辑位映射；字段形态参考 The Met Open Access catalog 与对象详情接口  
    【https://github.com/metmuseum/openaccess】

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

结论：强相关。这个任务里，Skill 的核心价值主要落在 collections、relationships、draft/publish、row-level access、hook 归属控制和 feed endpoint 的联动上。最近 3 次有效对照里，without_skill 都卡在草稿生命周期与角色边界动作上；with_skill 至少完成过 1 次全通过，但仍会受模型执行波动影响。

基于最近 **3** 次有效对比实验（均为真正跑到 task-level、存在完整 agent 轨迹；已排除启动失败类 trial）：

| 维度 | Without Skill | With Skill | 结果对比 |
| :--- | :--- | :--- | :--- |
| 通过率 | `0% (0/3)` | `33% (1/3)` | without_skill 在 3 次有效对照里都保留了 verifier 失败；with_skill 有 1 次完整通过，说明 skill 对收敛有帮助，但当前仍存在执行波动 |
| Agent 执行耗时 | `730.5s` | `744.1s` | with_skill 的 2 次失败试跑拉高了均值，当前耗时优势不明显 |
| Tokens | `3.28M` | `3.17M` | with_skill 的平均上下文开销略低，约为 without_skill 的 `0.97x` |

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
│   ├── oracle.py
│   ├── test_outputs.py
│   ├── test_mutation.py
│   └── test.sh
└── solution/
    ├── fixed/
    └── solve.sh
```
