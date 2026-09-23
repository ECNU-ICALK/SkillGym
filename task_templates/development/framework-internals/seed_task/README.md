# Framework Internals Template

这是面向 Framework Internals 类 skill 的模板。它综合参考 SkillsMP Framework Internals 类热门 skill 的共性能力：在现有框架内部补齐一项能力，让配置、构建、运行时和导出链路保持一致，并通过完整执行路径验证结果。

## 第一部分：任务设计参考

* **Skill 价值定位**：Framework Internals 类热门 skill 的核心价值，在于帮助 solver 识别一项框架能力会落在哪些内部层次，然后按既有模式把它接完整。对于 `flags` 这类 skill，关键点是理解“一个开关会经过哪些内部链路”，避免只改题面可见的一处入口。
* **Verifier 设计重点**：Verifier 应优先验证 solver 是否让同一项能力同时在配置、构建、运行时和导出路径中生效，是否把编译期 bundle 规划和运行时 bundle 选择保持一致，是否能在 alternate fixture 上保持泛化，以及是否避免把任务降成静态答案。重点不在表面格式，而在完整链路是否一致。

## 第二部分：示例任务

### 📌 任务元数据

- 任务 ID：`framework-internals__segment-cache-flag-plumbing`
- 类别：`framework-internals`
- 绑定 Skill：`flags`
- 输入数据参考来源：
  - `environment/workspace/data/upstream/flag_contract.json`：任务内配置合同快照；设计语义参考 Next.js 内部配置、构建和导出链路  
    【https://github.com/vercel/next.js/blob/canary/packages/next/src/server/config-shared.ts】
  - `environment/workspace/data/upstream/flag_behavior_notes.json`：任务内行为说明快照；直接参考公开 Next.js 文档中的实验性配置说明  
    【https://nextjs.org/docs/app/getting-started/cache-components】
  - `environment/workspace/data/upstream/docs_route_snapshot.json`：任务内路由与分段快照；设计形态参考公开 Next.js 文档路由  
    【https://nextjs.org/docs/app/api-reference/config/next-config-js】
  - `environment/workspace/data/upstream/fixture_matrix.json`：任务内场景矩阵；基于题目内两组配置场景整理

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

结论：强相关。这个任务里，`flags` 的核心价值是把“单个框架开关需要穿过哪些内部层次”明确下来，尤其是 app bundle 选择、server 侧 define scope、运行时环境注入和 export 路径的一致性。当前任务里最容易漏掉的点，是把启用态 define 错带到 server scope；带 skill 的诊断探针会直接把这个缺口暴露出来。

基于最近 **3** 次有效对照实验（均为完整跑到 task-level 的 E2B trial，已排除 build 被取消类 trial）：

| 维度 | Without Skill | With Skill | 结果对比 |
| :--- | :--- | :--- | :--- |
| 通过率 | `0% (0/3)` | `100% (3/3)` | `without_skill` 都停在动作级缺口：启用场景下 `next-runtime.webpack-config.js` 的 app/server define 作用域没有彻底分离，最终固定剩 1 个 verifier 失败；`with_skill` 3 次均完成全部链路并通过 |
| Agent 执行耗时 | `196.2s` | `245.8s` | `with_skill` 平均更长，原因是它会继续补齐整条链路并跑完收尾验证；`without_skill` 往往在部分接线后提前结束，但仍未过题 |
| Tokens | `0.78M` | `0.95M` | `with_skill` 平均 token 更高，主要花在跨文件链路核对与 probe 诊断之后的完整收敛；`without_skill` 虽然更省上下文，但没有完成关键 scope 修正 |

## 📁 标准目录结构说明

```text
seed_task/
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
