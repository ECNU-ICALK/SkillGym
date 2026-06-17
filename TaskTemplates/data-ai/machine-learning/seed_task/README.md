# Machine Learning Template

这是面向 Machine Learning 类 skill 的模板。它综合参考 SkillsMP Machine Learning 类热门 skill 的共性能力：从真实风格时序数据构建可复现训练链路、按业务合同拆分开发集、导出可重放模型包并保持离线推理一致性。

## 第一部分：任务设计参考

* **Skill 价值定位**：Machine Learning 类热门 skill 的核心价值，不只是“把模型跑起来”，而是把训练、验证、holdout 评估、导出和复现过程工程化。高质量任务应要求 solver 在真实数据约束下交付稳定、可重放、可审计的训练结果。
* **Verifier 设计重点**：Verifier 应优先验证行为结果：合同驱动的 split 是否真实、指标是否可复算、导出包能否复现预测、重复运行是否稳定。防作弊重点应覆盖硬编码结果、绕过真实训练、无视有效前缀约束和非确定性输出。

## 第二部分：示例任务

### 📌 任务元数据
- 任务 ID：`machine-learning__occupancy-phase-sequence-classifier`
- 类别：Machine Learning
- 绑定 Skill：`pytorch-patterns`
- 输入数据参考来源：
  - `environment/data/phase_sequences/development_index.csv`：任务内开发集序列索引；由 UCI Occupancy Detection 的 `datatraining.txt` 与 `datatest.txt` 生成固定窗口序列快照  
    https://cdn.uci-ics-mlr-prod.aws.uci.edu/357/occupancy%2Bdetection.zip
  - `environment/data/phase_sequences/holdout_index.csv`：任务内 holdout 序列索引；由 UCI Occupancy Detection 的 `datatest2.txt` 生成固定窗口序列快照  
    https://cdn.uci-ics-mlr-prod.aws.uci.edu/357/occupancy%2Bdetection.zip
  - `environment/data/phase_sequences/source_metadata.json`：任务内数据来源元信息；来源说明参考  
    https://archive-beta.ics.uci.edu/dataset/357/occupancy+detection

### 📊 验证与测试指标（Oracle & Verifier）
- Oracle：按正式流程独立运行并完成交付，结果可直接 100% 通过验证。
- Verifier 策略：

主测试
| 测试点 | 验证内容 | 对应 skill 内化点 |
| :--- | :--- | :--- |
| 输出完整度 | 检查要求的文件、列名、数据格式等是否均按规定生成 | 任务交付规范解读 |
| 验证集匹配 | 检查评估用的测试样本必须与输入的文件序列精准对齐 | 评估数据链路完整性 |
| 指标验算 | 验证提供的统计结果是否与具体每一条样本的预测表现一致计算得出 | 数据自证度与可靠度 |
| 验证规则动态调整 | 检查系统能够根据设定的分配比例动态得出有效的分类集合 | 数据管理与切割动作 |
| 模型留存可靠性 | 输出的模型加载执行后，结果要与此前提交的验证结果完全相同 | 模型导出及回溯的一致性 |
| 效果及格线 | 对最新数据验证要求准确度或者相关指标不能低于基础预定分数 | 模型选型的有效性体现 |

防作弊测试
| 测试点 | 验证内容 |
| :--- | :--- |
| 数据切分变动测试 | 给定切分比例修改后重跑流程，文件相关结构也要及时对应更新验证 |
| 追加噪声测试 | 在文件数据末端打乱补充无效信息时在有效范围下测试表现不因此崩溃 |
| 运行稳定性验证 | 相同的输入在配置和数据未改变时得到完全相同的输出结果 |

### ⚡ Skill 相关性评估

结论：强相关。该任务核心是生成可复现、可导出、可重放的 PyTorch 训练链路，并且要真实执行合同驱动的开发集拆分、变长序列 batching 和 CPU-safe bundle reload，这直接对应 `pytorch-patterns` 的使用场景：编写训练脚本、控制可复现性、保证设备无关行为、组织模型与数据加载流程。相对无 skill 情况，with skill 更容易一次性同时满足 determinism、contract-driven split、variable-length batching 和 bundle-reload 一致性。

基于最近 **3** 次有效对比实验（均为真正跑到 task-level、存在完整 agent 轨迹；已排除启动失败类 trial）。其中最早一轮发生在最终 verifier 双门槛口径确定前，已按当前最终口径统一回算；其余两轮直接跑在当前最终 verifier 上：

| 维度 | Without Skill | With Skill | 结果对比 |
| :--- | :--- | :--- | :--- |
| 通过率 | `0%` | `100%` | 近 3 次有效对照里，without skill 均至少遗留 1 项 verifier 失败；失败以动作级问题为主，集中在未稳定满足最终质量门槛或未完全满足 bundle reload 合同。 |
| Agent 执行耗时 | `854.9s` | `869.7s` | 本任务里 with skill 的主要收益体现在通过率与完整交付稳定性，而不是平均耗时下降。 |
| Tokens | `4.59M` | `3.04M` | Without skill 的上下文与试错开销约为 With skill 的 `1.51x`。 |

## 📁 标准目录结构说明

```text
seed_task/
├── instruction.md
├── task.toml
├── PLAN.json
├── README.md
├── environment/
│   ├── Dockerfile
│   ├── generate_seed_data.py
│   ├── data/
│   ├── project/
│   └── skills/
├── tests/
│   ├── test.sh
│   └── test_outputs.py
└── solution/
    ├── fixed_run_pipeline.py
    └── solve.sh
```
