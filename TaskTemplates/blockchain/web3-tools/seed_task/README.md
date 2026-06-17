# Web3-Tools Template

这是面向 `web3-tools` 类 skill 的模板。它综合参考 SkillsMP `web3-tools` 类热门 skill 的共性能力：公开交易所市场目录读取、native symbol 与 canonical symbol 对齐、OHLCV 数据整理、跨交易所指标比较和结构化交付。

## 第一部分：任务设计参考

* **Skill 价值定位**：`web3-tools` 类热门 skill 的共性价值，通常落在公开市场数据接入、交易所命名差异处理、行情序列整理和稳定落盘上。对这类任务，skill 的作用是让 Agent 先建立交易所视角的数据模型，再进入指标计算、对照和交付。
* **Verifier 设计重点**：Verifier 应独立重算关键市场指标，并检查市场覆盖、native symbol、时间顺序、成交量口径、告警阈值和输出排序是否一致。除了结果数值，还要覆盖输入不可改写、服务访问路径、source manifest 一致性和项目入口可复跑性。

## 第二部分：示例任务

### 📌 任务元数据

- 任务 ID：`web3-tools__cross-exchange-daily-surveillance`
- 类别：`web3-tools`
- 绑定 Skill：`ccxt-python`
- 输入数据参考来源：
  - `environment/data/service_fixtures/market_data.json`：任务内 Coinbase 市场分页目录与 `BTC-USD` / `ETH-USD` 日线载荷；数据整理参考公开历史数据仓库  
    `https://raw.githubusercontent.com/bhaskatripathi/Cryptodata_Coinbase_Kraken_Binance/main/Coinbase_data_combined_v2_merged.xlsx`
  - `environment/data/service_fixtures/market_data.json`：任务内 Kraken 市场分页目录与 `XBTUSD` / `ETHUSD` 日线载荷；数据整理参考公开历史数据仓库  
    `https://raw.githubusercontent.com/bhaskatripathi/Cryptodata_Coinbase_Kraken_Binance/main/Kraken_data_combined_v2_merged.xlsx`
  - `environment/data/reference/market_reference.csv`：任务内较早市场导出参考；字段和命名背景对照同仓库说明  
    `https://raw.githubusercontent.com/bhaskatripathi/Cryptodata_Coinbase_Kraken_Binance/main/README.md`

### 📊 验证与测试指标（Oracle & Verifier）

- Oracle：按正式流程独立运行并完成交付，结果可直接 100% 通过验证。
- Verifier策略：

主测试
| 测试点 | 验证内容 | 对应skill内化点 |
| :--- | :--- | :--- |
| 输出契约 | 校验 JSON、CSV、Markdown 和 source manifest 的结构、字段与排序 | 结构化交付与结果审计 |
| 市场发现 | 校验先取 live manifest，再遍历每个 exchange 的全部 catalog 分页 | 交易所目录发现流程 |
| 符号映射 | 校验 native symbol、canonical symbol、`XBT -> BTC` 别名与目标市场覆盖 | 交易所命名差异处理 |
| 市场指标重算 | 重算 `return_1d`、`return_7d`、`return_30d`、`quote_volume_7d_usd` 和 `avg_spread_bps_7d` | OHLCV 数据归一化 |
| 跨交易所对照 | 重算 30 日收益优胜方、最低 spread 方、close gap 与 coverage | 多交易所结果比较 |
| 项目入口复跑 | 用工作区入口脚本复跑交付并校验稳定性 | 通过项目入口完成交付 |

防作弊测试
| 测试点 | 验证内容 |
| :--- | :--- |
| 输入完整性 | data 与 hidden service 不可修改 |
| 服务访问路径 | solver 必须在 verifier 之前访问 `/api/manifest`、全部 catalog 分页和全部目标 OHLCV 端点 |
| 占位输出拦截 | 禁止占位文本、删减输出、额外输出文件和 verifier 字样泄漏 |
| 交付来源 | 输出必须由 `/app/workspace/marketwatch/` 中的项目入口复跑得出 |

### ⚡ Skill 相关性评估

结论：强相关。这个任务里，Skill 的核心价值落在先读取 live manifest 和分页 catalog，确认 exchange-native market id 与 canonical symbol 的关系，再处理 bar 排序、别名映射和 volume unit 差异。只做表面整理的解法，很容易漏抓分页、漏做 `XBT -> BTC` 对齐，或者把成交量口径算错。

基于最近 **3 次** 有效对比实验（均为真正跑到 task-level、存在完整 agent 轨迹；已排除启动失败类 trial）：

| 维度 | Without Skill | With Skill | 结果对比 |
| :--- | :--- | :--- | :--- |
| 通过率 | `0%` | `100%` | 近 3 次有效对照里，without Skill 都卡在市场覆盖汇总、数值口径或输出合同收敛；with Skill 均稳定通过全部 verifier |
| Agent 执行耗时 | `330.6s` | `226.0s` | With Skill 的目录发现、symbol 对齐和交付收敛更快，平均 Agent 耗时降低约 `31.6%` |
| Tokens | `445.4K` | `337.6K` | Without Skill 的上下文与试错开销约为 With Skill 的 `1.32x` |

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
│   ├── hidden-service-src/
│   ├── skills/
│   └── workspace/
├── tests/
└── solution/
```
