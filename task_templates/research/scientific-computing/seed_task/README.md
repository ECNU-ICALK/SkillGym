# Scientific-Computing Template

这是面向 `scientific-computing` 类 skill 的模板。它综合参考 SkillsMP scientific-computing 类热门 skill 的共性能力：多格式科学文件识别、结构勘查、质量检查、分析前 intake 组织、约定对齐，以及把局部分析结果收束为可继续处理的交付物。

## 第一部分：任务设计参考

* **Skill 价值定位**：scientific-computing 类热门 skill 的共性价值，在于把 netCDF、XML、原始观测文本、JSON contract 这类异构科学输入组织成稳定的分析前工作流。模板任务应把重点放在候选文件发现、结构理解、质量归纳和正式交付，而不是把方法细节直接写进题面。
* **Verifier 设计重点**：Verifier 应优先检查 solver 是否走通了多格式发现与聚合链路，并验证关键约定、精度策略、mutation 响应和可重放性。防作弊设计要覆盖文件名扰动、contract 变更、metadata 变更以及输入完整性，避免只靠表层模板或手写答案过关。

## 第二部分：示例任务

### 📌 任务元数据

- 任务 ID：`scientific-computing__marine-heat-intake-screening`
- 类别：`scientific-computing`
- 绑定 Skill：`exploratory-data-analysis`
- 输入数据参考来源：
  - `environment/data/grids/thermal_subset_alpha.nc`：任务内 OISST 候选网格子集之一；数据形态参考 NOAA OISST daily netCDF  
    https://www.ncei.noaa.gov/products/optimum-interpolation-sst
  - `environment/data/grids/thermal_subset_beta.nc`：候选网格文件目录与逐日组织形态参考  
    https://www.ncei.noaa.gov/thredds/catalog/OisstBase/NetCDF/V2.1/AVHRR/202404/catalog.html
  - `environment/data/buoys/coastal_extract_alpha.txt`：任务内浮标候选观测文本之一；数据形态参考 NDBC historical stdmet  
    https://www.ndbc.noaa.gov/data/historical/stdmet/44013h2024.txt.gz
  - `environment/data/buoys/coastal_extract_beta.txt`：第二份浮标候选观测文本；来源形态同上  
    https://www.ndbc.noaa.gov/data/historical/stdmet/44013h2024.txt.gz
  - `environment/data/metadata/platform_record_alpha.xml`：任务内站点候选元数据 XML 之一；内容形态参考 NDBC station page metadata/history  
    https://www.ndbc.noaa.gov/station_page.php?station=44013
  - `environment/data/metadata/platform_record_beta.xml`：第二份站点候选元数据 XML；来源形态同上  
    https://www.ndbc.noaa.gov/station_page.php?station=44013

### 📊 验证与测试指标（Oracle & Verifier）

- Oracle：按正式流程独立运行并完成交付，结果可直接 100% 通过验证。
- Verifier策略：

主测试

| 测试点 | 验证内容 | 对应skill内化点 |
| :--- | :--- | :--- |
| 输出合同与候选发现 | 检查 5 个输出文件存在、可解析，且所选 buoy/XML/netCDF 与 contract 约束一致 | 先识别文件类型与候选集，再建立正式交付 |
| 结构化重算 | 从文本、XML、netCDF、JSON 重算 input summary、daily panel、candidate windows，并检查 issue vocabulary 与精度策略 | 多格式读取、质量检查、精度控制、contract 驱动筛选 |
| Intake 可追溯 | 检查 markdown intake 是否写明选中输入、grid 点位、主要问题和 shortlist 结论 | 把分析过程收束成可继续使用的分析前说明 |

防作弊测试

| 测试点 | 验证内容 |
| :--- | :--- |
| Contract mutation | 调整 top-k 与阈值后，candidate shortlist 必须跟着变化 |
| Metadata mutation | 改动 latest history 坐标后，grid mapping 与输出必须同步变化 |
| Filename obfuscation | 打乱候选文件名后，仍需选中同一组核心输入 |
| 输入与技能完整性 | `/root/data` 与 `/root/.codex/skills` 内容不得变化，官方入口重复运行需产出一致结果 |

### ⚡ Skill 相关性评估

结论：强相关。这个任务里，Skill 的核心价值是把候选科学文件识别、结构理解、质量检查和 markdown intake 组织成一条清晰链路；新增的本地 probe 只暴露输出约定，不直接泄露答案，因此仍然要求 solver 主动完成文件发现、问题归纳和 contract 响应。

基于最终口径下 **5** 次有效对比实验（均为真正跑到 task-level、存在完整 agent 轨迹；已排除启动失败类 trial）：

| 维度 | Without Skill | With Skill | 结果对比 |
| :--- | :--- | :--- | :--- |
| 通过率 | `0%` | `100%` | 近 5 次有效对照里，without Skill 全部失败，主要落在 issue coverage 不完整、数值被手动截断、以及 contract / metadata mutation 响应不稳；with Skill 5 次全部通过。 |
| Agent 执行耗时 | `449.5s` | `501.1s` | With Skill 的平均耗时略高，主要来自更完整的 intake 和 probe 对齐步骤；但它显著提升了收敛稳定性。 |
| Tokens | `0.76M` | `0.76M` | 两组 token 规模接近；with Skill 略低，说明额外约定并没有带来明显上下文膨胀。 |

## 📁 标准目录结构说明

```text
模板任务：
├── instruction.md          # 任务说明（仅包含症状、业务约束和禁止事项）
├── task.toml               # 任务元数据（标签、技能要求、运行入口）
├── PLAN.json               # 任务构建过程的结构化元信息
├── environment/            # 运行环境
│   ├── Dockerfile          # 单容器镜像定义
│   ├── data/               # 本地输入数据与 contract
│   ├── workspace/          # 官方入口与工作区骨架
│   └── skills/             # 任务绑定 skill 定义与附带探针清单
├── tests/                  # Verifier 与 Guardrail 测试集
└── solution/               # 官方参考代码及 solve.sh
```
