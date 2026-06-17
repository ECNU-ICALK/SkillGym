# Bioinformatics Template

这是面向 `bioinformatics` 类 skill 的模板。它综合参考 SkillsMP bioinformatics 类热门 skill 的共性能力：读取公开来源分子数据、识别分析口径、完成结构化 QC 与统计链路、生成可复跑图表，并把结果收口为研究交接材料。

## 第一部分：任务设计参考

* **Skill 价值定位**：bioinformatics 类热门 skill 的共同价值，在于帮助 Agent 识别数据形态、分析阶段和约束来源，再把清洗、统计、注释和交付组织成一条稳定工作流。模板任务应把价值放在“如何从公开来源数据稳定走到可验证交付”，并避免把方法细节全部摊开在题面里。
* **Verifier 设计重点**：Verifier 应优先验证 solver 是否沿数据链路完成读取、清洗、统计、分组和结果回写，并检查多份交付物之间的一致性。对于绑定工作流型 skill 的任务，还应验证 solver 是否使用当前 authority source，并拦截只依赖旧导出或静态答案的捷径。

## 第二部分：示例任务

### 📌 任务元数据

- 任务 ID：`bioinformatics__pbmc-single-cell-cluster-handoff`
- 类别：`bioinformatics`
- 绑定 Skill：`scanpy`
- 输入数据参考来源：
  - `environment/data/pbmc3k_filtered_gene_bc_matrices.tar.gz`：任务内 PBMC 10x 计数矩阵；数据直接来源于 10x Genomics PBMC 3k 数据集  
    https://cf.10xgenomics.com/samples/cell-exp/1.1.0/pbmc3k/pbmc3k_filtered_gene_bc_matrices.tar.gz  
    https://www.10xgenomics.com/resources/datasets/3-k-pbm-cs-from-a-healthy-donor-1-standard-1-1-0
  - `environment/service_seed/current_marker_panel.csv`：任务内 marker panel 的设计形态参考 Scanpy PBMC3k tutorial  
    https://scanpy-tutorials.readthedocs.io/en/latest/pbmc3k.html
  - `environment/data/analysis_manifest.json`：任务内 local policy service 地址与 authority 说明，无单独公开数据链接
  - `environment/data/submission_contract.json`：任务内交付合同文件，无单独公开数据链接
  - `environment/data/reference_analysis_policy.json`：任务内旧口径分析提示，无单独公开数据链接
  - `environment/data/reference_marker_panel.csv`：任务内旧口径 marker panel 提示，无单独公开数据链接

### 📊 验证与测试指标（Oracle & Verifier）

- Oracle：按正式流程独立运行并完成交付，结果可直接 100% 通过验证。
- Verifier 策略：

主测试

| 测试点 | 验证内容 | 对应 skill 内化点 |
| :--- | :--- | :--- |
| 输出契约 | 检查 7 个交付物存在、可解析，并包含必需字段、列名和章节 | 先理解正式交付合同，再组织结构化结果 |
| QC 重算 | 按当前 policy 重算 retained cells、retained genes、阈值和中位数统计 | 单细胞 QC 与过滤口径 |
| 分群摘要 | 按当前 policy 重算分群结果，核对 cluster 级别统计与代表 marker | 预处理、降维、分群与结果汇总 |
| Marker 排名 | 按当前 marker 规则重算每个 group 的 marker gene 排名 | marker gene 识别与排序 |
| 注释与 handoff | 检查 coarse cell-type label、支持 markers、报告段落与图是否一致 | 基于 marker 的注释与研究交接 |

防作弊测试

| 测试点 | 验证内容 |
| :--- | :--- |
| 当前 authority source | 访问日志必须证明 solver 查询了当前 policy 和 marker panel endpoint；只依赖 `reference_*` 不能通过 |
| 数据与环境完整性 | `/root/data`、隐藏 service 和 seed 内容不得变化；service 在 verifier 结束时仍健康 |

### ⚡ Skill 相关性评估

结论：强相关。这个任务里，Skill 的核心价值是把 10x 读入、QC、降维、分群、marker 排名和注释整理成一条稳定工作流，从而明显降低分析偏航和试错成本；without Skill 更容易停在旧口径依赖、分群失配、marker 排名方法失配或 annotation 判断偏差这类分析级失败上。

基于最近 **3** 次有效对比实验（均为真正跑到 task-level、存在完整 agent 轨迹；已排除启动失败类 trial）：

| 维度 | Without Skill | With Skill | 结果对比 |
| :--- | :--- | :--- | :--- |
| 通过率 | `0%` | `100%` | 近 3 次有效对照里，without Skill 稳定保留当前 policy 下的 QC retained-cell 偏差，并进一步带出 group total 不一致；with Skill 能稳定完成当前口径交付 |
| Agent 执行耗时 | `501.1s` | `390.5s` | With Skill 的工作流收敛更快，平均 Agent 耗时降低约 `22.1%` |
| Tokens | `1.63M` | `1.11M` | Without Skill 的上下文与试错开销约为 With Skill 的 `1.46x` |

## 📁 标准目录结构说明

```text
模板任务：
├── instruction.md          # 任务说明（仅包含症状、业务约束和禁止事项）
├── task.toml               # 任务元数据（标签、技能要求、运行入口）
├── PLAN.json               # 任务构建过程的结构化元信息
├── README.md
├── environment/            # 运行环境
│   ├── Dockerfile          # 单容器镜像定义；在同一容器内启动本地 policy service
│   ├── data/
│   ├── hidden-service-src/
│   ├── service_seed/
│   └── skills/
├── tests/                  # Verifier 与 Guardrail 测试集
└── solution/               # 官方参考解法及 solve.sh
```
