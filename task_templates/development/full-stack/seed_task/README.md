# Full-Stack Template

这是面向 full-stack 类 skill 的模板。它综合参考 SkillsMP full-stack 热门 skill 的共性能力：在空白工作目录中建立完整项目结构，补齐依赖与启动链路，在单容器里交付同项目内的页面、接口和本地状态持久化，并让结果能够被稳定校验。

## 第一部分：任务设计参考
* **Skill 价值定位**：这类 skill 的核心价值，在于把“从空工作目录到可运行项目”的初始化路径标准化，减少 solver 在目录结构、脚本入口、依赖装配和本地运行方式上的试错。模板任务应让 skill 的这部分优势直接影响能否尽快进入业务实现阶段。
* **Verifier 设计重点**：校验不应只盯静态文件是否存在，而应覆盖默认启动是否成功、项目骨架是否与题面约束一致、接口是否按输入数据计算、页面是否可实际操作，以及状态变更是否在重启后保留。对照实验里，without_skill 的失败最好落在项目初始化或联调动作没有完成，避免只剩轻微格式偏差。

## 第二部分：示例任务
### 📌 任务元数据
- 任务 ID：`imdb-curation-workbench-scaffold`
- 类别：`full-stack`
- 绑定 Skill：`project-setup-info-local`
- 输入数据参考来源：
  - `environment/data/title_basics_sample.tsv`：任务内片目基础信息；设计形态参考 IMDb `title.basics.tsv.gz`  
    【https://datasets.imdbws.com/title.basics.tsv.gz】
  - `environment/data/title_ratings_sample.tsv`：任务内评分与票数快照；直接取自 IMDb `title.ratings.tsv.gz`  
    【https://datasets.imdbws.com/title.ratings.tsv.gz】
  - `environment/data/title_crew_sample.tsv`：任务内导演与编剧关联；设计形态参考 IMDb `title.crew.tsv.gz`  
    【https://datasets.imdbws.com/title.crew.tsv.gz】
  - `environment/data/title_principals_sample.tsv`：任务内主要演职员关联；设计形态参考 IMDb `title.principals.tsv.gz`  
    【https://datasets.imdbws.com/title.principals.tsv.gz】
  - `environment/data/name_basics_sample.tsv`：任务内人物名称映射；设计形态参考 IMDb `name.basics.tsv.gz`  
    【https://datasets.imdbws.com/name.basics.tsv.gz】

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
结论：中等相关。这个任务把空工作目录起项目、保留默认脚本链路、补齐 App Router 骨架和本地持久化放在前置位置；without_skill 多次停在脚手架、启动健康检查或浏览器工作流，说明 skill 对进入业务实现阶段有帮助，但最近几次 trial 里 with_skill 侧仍存在收敛波动。

基于最近 **4** 次有效对比实验（均为真正跑到 task-level、存在完整 agent 轨迹；已排除启动失败类 trial）：

| 维度 | Without Skill | With Skill | 结果对比 |
| :--- | :--- | :--- | :--- |
| 通过率 | `0%` | `50%` | 近 4 次有效对照里，without_skill 均有 verifier 失败，主要落在浏览器工作流、Next.js 脚手架合同或健康检查；with_skill 有 `2/4` 次完整通过。 |
| Agent 执行耗时 | `651.5s` | `628.7s` | With Skill 的平均 Agent 耗时下降约 `3.5%`，在起项目和联调阶段收敛更快。 |
| Tokens | `2.68M` | `2.65M` | With Skill 的上下文与试错开销略低，平均总 tokens 下降约 `1.0%`。 |

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
│   ├── data_alt/
│   ├── scripts/
│   └── skills/
├── tests/
│   ├── test.sh
│   └── verify_curation_workbench.py
└── solution/
    ├── solve.sh
    └── reference/
```
