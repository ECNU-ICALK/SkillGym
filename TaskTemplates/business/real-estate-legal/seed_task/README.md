# Real-Estate-Legal Template

这是面向 `real-estate-legal` 类 skill 的模板。它综合参考 SkillsMP `real-estate-legal` 类热门 skill 的共性能力：公开拍卖公告核对、条款抽取、债务与责任归属判断、买方现金支出测算，以及面向投委会的结论整理。

## 第一部分：任务设计参考

* **Skill 价值定位**：`real-estate-legal` 类热门 skill 的共同价值，在于把公告、法条、税费规则和业务口径组织成一条可执行审查链路。模板任务应把重点放在“当前该查什么、如何收口、如何形成正式交付”。
* **Verifier 设计重点**：Verifier 应优先验证 solver 是否走过当前权威数据链路，并检查事实、责任归属、现金支出和结论之间是否一致。防作弊测试应重点拦截只看旧导出、跳过本地 authority service、漏拿分页风险和沿用旧成本表的捷径。

## 第二部分：示例任务

### 📌 任务元数据

- 任务 ID：`real-estate-legal__caixa-auction-edital-audit`
- 类别：`real-estate-legal`
- 难度：`hard`
- 绑定 Skill：`leiloeiro-edital`
- 输入数据参考来源：
  - `environment/data/source_notice_batch.pdf`：任务内公告 PDF；设计形态参考 CAIXA 拍卖公告  
    https://venda-imoveis.caixa.gov.br/editais/EL00200226CPARE.PDF
  - `environment/data/source_notice_excerpt.pdf`：任务内公告摘录页；内容来自同一份 CAIXA 公告  
    https://venda-imoveis.caixa.gov.br/editais/EL00200226CPARE.PDF
  - `environment/data/source_itbi_sp.html`：任务内圣保罗市 ITBI 页面快照  
    https://prefeitura.sp.gov.br/cidade/secretarias/fazenda/servicos/itbi/index.php?p=2513
  - `environment/data/source_fiduciary_law.html`：任务内法拍流程法条页面快照；设计形态参考《Lei 9.514/1997》Art. 27  
    https://www.planalto.gov.br/ccivil_03/Leis/l9514.htm
  - `environment/data/source_cpc.html`：任务内拍卖程序法条页面快照；设计形态参考《Lei 13.105/2015》  
    https://www.planalto.gov.br/ccivil_03/_ato2015-2018/2015/lei/L13105.htm

### 📊 验证与测试指标（Oracle & Verifier）

- Oracle：按正式流程独立运行并完成交付，结果可直接 100% 通过验证。
- Verifier策略：

主测试

| 测试点 | 验证内容 | 对应skill内化点 |
| :--- | :--- | :--- |
| 交付规范 | 确保 4 个输出文件完整且格式合规（包含字段、列名及标题） | 理解交付标准并输出结构化结果 |
| 数据提取验证 | 依据实时标的重新核对 `notice_extract.json` 的准确性 | 从公告中抽取事实并归纳条款 |
| 支出测算验证 | 依据当前标准重新计算佣金、税金等买方实际支出成本 | 测算买方的资金规模及责任划分 |
| 风险登记验证 | 核对风险识别是否全面，定级与证据来源是否准确 | 风险归类与证据追溯能力 |
| 结论一致性 | 检查报告与底层数据是否一致，核心风险与资金限制是否明确表达 | 结论总结与投委会材料输出 |

防作弊测试

| 测试点 | 验证内容 |
| :--- | :--- |
| 实时合规获取 | 流程记录必须证明被测模型读取了最新的标的、成本及风险接口数据 |
| 禁用历史数据 | 过时的报价、付款方式、税费及成本预估数据均不能作为最终结果 |
| 环境安全性 | 测试期间不得篡改基础数据与后台服务，验证结束后服务需保持正常 |

### ⚡ Skill 相关性评估

结论：强相关。这个任务里，Skill 的核心价值是把 `job_manifest.json`、authority service、分页风险集、当前成本口径和投委会输出串成一条稳定工作流，从而明显降低旧导出依赖和 live-only 更新漏拿的概率。基于最近 5 次有效 task-level 对比，with Skill 的通过率明显高于 without Skill，且平均耗时和 tokens 都更低。

基于最近 **5** 次有效对比实验（均为真正跑到 task-level、存在完整 agent 轨迹；已排除启动失败类 trial）：

| 维度 | Without Skill | With Skill | 结果对比 |
| :--- | :--- | :--- | :--- |
| 通过率 | `0/5` | `60% (3/5)` | 近 5 次有效对照里，without Skill 始终未通过；常见失败路径是没有先走 manifest 和当前 authority service 链路，随后沿用旧口径或漏拿 live-only 更新。 |
| Agent 执行耗时 | `437.7s` | `389.3s` | With Skill 的诊断与收敛更快，平均 Agent 耗时降低约 `11.1%`。 |
| Tokens | `1.89M` | `1.70M` | With Skill 的上下文与试错开销更低，Without Skill 约为 With Skill 的 `1.11x`。 |

## 📁 标准目录结构说明

```text
模板任务：
├── instruction.md          # 任务说明（仅包含症状、业务约束和禁止事项）
├── task.toml               # 任务元数据（标签、技能要求、运行入口）
├── PLAN.json               # 任务构建过程的结构化元信息
├── environment/            # 运行环境
│   ├── Dockerfile          # 单容器镜像定义；在同一容器内启动 authority service 与隐藏下游数据
│   ├── ...                 # 可选的 source 快照 / service seed / scripts
│   └── skills/             # 任务绑定的 real-estate-legal skill 定义与辅助脚本
├── tests/                  # Verifier 与 Guardrail 测试集
└── solution/               # 官方参考代码及 solve.sh
```
