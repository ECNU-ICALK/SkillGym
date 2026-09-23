# Gaming Template

这是面向 `gaming` 类 skill 的模板。它综合参考 SkillsMP gaming 类热门 skill 的共性能力：程序化生成、场景参数控制、页面内状态切换、本地数据驱动展示、浏览器即时反馈与可复现输出。

## 第一部分：任务设计参考

* **Skill 价值定位**：gaming 类热门 skill 的核心价值，通常在于把玩法规则、程序化内容、状态切换和交互呈现组合成一份可直接操作的浏览器交付物。模板任务应让 skill 在数据解释、生成逻辑、交互分区和可复现行为上明显降低试错成本，而不只奖励把数据摆成静态图表。
* **Verifier 设计重点**：Verifier 应同时检查页面能否启动、交互控件是否齐备、局部状态变化是否符合合同、导出内容是否可追溯到输入数据，以及可复现约束是否成立。除此之外，还要覆盖输入不可改写、禁止占位输出与 verifier-hack 等 guardrail。

## 第二部分：示例任务

### 📌 任务元数据

- 任务 ID：`gaming__kanto_encounter_atlas`
- 类别：`gaming`
- 绑定 Skill：`algorithmic-art`
- 输入数据参考来源：
  - `environment/data/pokedex_kanto.json`：Kanto 图鉴快照；设计形态参考 PokeAPI Kanto Pokedex  
    【https://pokeapi.co/api/v2/pokedex/2/】
  - `environment/data/encounter_zones.json`：区域遭遇层、等级区间、出现权重与地点分组；设计形态参考下列 location-area 接口  
    【https://pokeapi.co/api/v2/location-area/viridian-forest-area/】  
    【https://pokeapi.co/api/v2/location-area/mt-moon-1f/】  
    【https://pokeapi.co/api/v2/location-area/rock-tunnel-1f/】  
    【https://pokeapi.co/api/v2/location-area/kanto-power-plant-area/】  
    【https://pokeapi.co/api/v2/location-area/seafoam-islands-b1f/】  
    【https://pokeapi.co/api/v2/location-area/kanto-safari-zone-middle/】
  - `environment/data/type_relations.json`：属性攻防关系与分组；数据形态参考 PokeAPI type 接口  
    【https://pokeapi.co/api/v2/type/】

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

结论：强相关。这个任务里，Skill 的核心价值是把 seeded generative viewer、参数探索、可复现场景和页面内解释层组织成一套收敛更快的实现路径。当前 verifier 也会继续卡住只做表层摘要、缺少交互解释层或缺少可复现生成链路的解法。

基于最近 **3** 次有效对比实验（均为完整 task-level 运行，并按最终 verifier 口径核对）：

| 维度 | Without Skill | With Skill | 结果对比 |
| :--- | :--- | :--- | :--- |
| 通过率 | `0/3` | `3/3` | 最近 3 次有效对照里，without Skill 主要停在 seeded 复现稳定性、参数几何语义或分析面板语义层；with Skill 在最终口径下稳定满足交付合同 |
| Agent 执行耗时 | `733.4s` | `749.5s` | With Skill 平均耗时略高约 `2.2%`，但更多时间花在把交付收尾到 verifier 通过，而不是在无效试错上反复回摆 |
| Tokens | `2.77M` | `2.16M` | Without Skill 的上下文与试错开销约为 With Skill 的 `1.28x` |

## 📁 标准目录结构说明

```text
seed_task/
├── instruction.md
├── task.toml
├── PLAN.json
├── environment/
│   ├── Dockerfile
│   ├── data/
│   ├── skills/
│   ├── verifier/
│   └── workspace/
├── tests/
├── solution/
└── README.md
```
