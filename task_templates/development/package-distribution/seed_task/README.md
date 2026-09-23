# Package Distribution Template

这是面向 Package Distribution 类 skill 的模板。它综合参考 SkillsMP Package Distribution 类热门 skill 的共性能力：包结构整理、构建后端选择、CLI 入口暴露、发布前元数据校验、分发产物生成，以及安装态资源可用性验证。

## 第一部分：任务设计参考

* **Skill 价值定位**：Package Distribution 类热门 skill 的核心价值，是把“仓库里有可运行代码”推进到“可以作为标准软件包被构建、安装、调用和交付”。它要求 solver 同时处理包结构、构建元数据、入口点、资源打包、版本约束和分发产物校验，并避免只补单个脚本或单个配置文件。
* **Verifier 设计重点**：Verifier 应优先验证安装态行为，弱化对源码态表象的依赖，包括 wheel 与 sdist 是否齐备、控制台入口和 `python -m` 是否都可用、安装后的自动化 entry point 是否可被发现、包根级 API 是否能被下游直接导入、类型信息是否随包分发，以及交付清单是否和产物一致。防作弊点应覆盖硬编码输出、绕开构建产物、只在源码目录下可运行和篡改输入数据等问题。

## 第二部分：示例任务

### 📌 任务元数据

- 任务 ID：`package_distribution__pkgmeta_kit_release_candidate`
- 类别：Package Distribution
- 绑定 Skill：`python-pypi-package-builder`
- 输入数据参考来源：
  - `environment/workspace/pkgmeta-kit/data/licenses.json`：任务内许可证目录快照，直接来源于  
    https://github.com/spdx/license-list-data/blob/main/json/licenses.json
  - `environment/workspace/pkgmeta-kit/data/trove_classifiers.py`：任务内 classifier 目录快照，直接来源于  
    https://github.com/pypa/trove-classifiers/blob/main/src/trove_classifiers/__init__.py
  - `environment/workspace/pkgmeta-kit/seed_sampleproject_README.md`：包 README 结构参考，直接来源于  
    https://github.com/pypa/sampleproject/blob/main/README.md

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

结论：强相关。这个任务里，Skill 的核心价值集中在 Python 包结构决策、构建元数据补齐、wheel 与 sdist 双产物校验、安装态资源访问，以及安装后 entry point 的暴露方式。最近这轮迭代把关键差异转到安装态自动化发现与类型分发能力后，with Skill 仍能稳定通过，without Skill 更容易漏掉完整分发链路中的关键动作。

基于最近 **3** 次有效对比实验（均真正跑到 task-level、存在完整 agent 轨迹；已排除 build cancelled 等启动异常 trial）：

| 维度 | Without Skill | With Skill | 结果对比 |
| :--- | :--- | :--- | :--- |
| 通过率 | `0%` | `100%` | 最近 3 次有效对照里，without Skill 都留下至少 1 项 verifier 失败；with Skill 都完成了全部测试点 |
| Agent 执行耗时 | `273.0s` | `326.1s` | With Skill 的执行更完整，额外覆盖了打包与安装态核验路径，因此平均耗时更高 |
| Tokens | `771,132` | `1,083,635` | With Skill 在这组实验中为了完成更完整的分发链路校验，平均 token 开销更高（含 cache token） |

## 📁 标准目录结构说明

```text
模板任务：
├── instruction.md
├── task.toml
├── PLAN.json
├── README.md
├── environment/
│   ├── Dockerfile
│   ├── skills/
│   └── workspace/
├── tests/
└── solution/
```
