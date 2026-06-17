# IDE Plugins Template

这是面向 IDE Plugins 类 skill 的模板。它综合参考 SkillsMP IDE Plugins 类热门 skill 的共性能力：扩展脚手架整理、多语言资源同步、命令与视图接线、引导内容配置、导出产物生成与 VSIX 交付。

## 第一部分：任务设计参考

* **Skill 价值定位**：IDE Plugins 类热门 skill 的核心价值，在于帮助 solver 快速识别一个编辑器扩展的交付面并把这些面接齐。对于本地化相关任务，常见关键点包括贡献项文案、运行态消息、引导内容和打包产物是否一起到位。
* **Verifier 设计重点**：Verifier 应优先验证扩展交付是否完整，而不是只看某几个文件有没有被编辑。重点包括多语言贡献项、菜单/视图入口、运行态消息、引导内容和导出产物是否一起对齐，以及这些面是否会随着输入语言资产变化而再生成。

## 第二部分：示例任务

### 📌 任务元数据

- 任务 ID：`ide-plugins__vscode-release-briefing-localization`
- 类别：`IDE Plugins`
- 绑定 Skill：`vscode-ext-localization`
- 输入数据参考来源：
  - `environment/data/releases/1.87.json`：任务内 VS Code 1.87 更新快照；内容整理自官方 2024 年 2 月更新说明  
    【https://code.visualstudio.com/updates/v1_87】
  - `environment/data/releases/1.88.json`：任务内 VS Code 1.88 更新快照；内容整理自官方 2024 年 3 月更新说明  
    【https://code.visualstudio.com/updates/v1_88】
  - `environment/data/releases/1.89.json`：任务内 VS Code 1.89 更新快照；内容整理自官方 2024 年 4 月更新说明  
    【https://code.visualstudio.com/updates/v1_89】
  - `environment/data/locales/*/briefing_terms.json`：任务内多语言术语与文案结构；设计形态参考 VS Code 扩展本地化指南与公开语言资源仓库  
    【https://code.visualstudio.com/api/working-with-extensions/localization】  
    【https://github.com/microsoft/vscode-loc】
  - `environment/data/locales/*/extension_copy.json`：任务内扩展多语言交付文案源，包括贡献项、运行态 bundle 和 walkthrough markdown；设计形态参考 VS Code 扩展本地化指南与公开语言资源仓库  
    【https://code.visualstudio.com/api/working-with-extensions/localization】  
    【https://github.com/microsoft/vscode-loc】

### 📊 验证与测试指标（Oracle & Verifier）

- Oracle：按正式流程独立运行并完成交付，结果可直接 100% 通过验证。
- Verifier策略：

主测试

| 测试点 | 验证内容 | 对应skill内化点 |
| :--- | :--- | :--- |
| 默认请求导出 | 校验默认请求可产出三份多语言简报和一个 VSIX | 本地化导出与打包闭环 |
| Manifest 覆盖 | 校验命令、菜单、视图、配置和引导入口都具备三语言覆盖 | `package.json` 贡献项本地化 |
| Walkthrough 覆盖 | 校验引导内容的多语言资源路径与内容都可用 | 引导内容本地化 |
| Runtime 覆盖 | 校验运行态消息包在三种语言下都齐全 | `bundle.l10n` 资源接线 |
| 刷新命令 | 校验版本列表刷新入口与状态提示一起可用 | 命令与视图联动 |
| Locale Copy 同步 | 校验语言资产变动后，manifest、bundle、walkthrough、导出结果和 VSIX 都会一起变化 | 多语言交付面同步 |
| 变体请求泛化 | 校验换一份请求后简报内容跟随变化 | 避免硬编码，保持输入驱动 |

防作弊测试

| 测试点 | 验证内容 |
| :--- | :--- |
| 输入文件保护 | 校验更新快照、语言素材和请求文件 hash 保持不变 |
| 变体请求回归 | 切换另一份请求后结果必须随之变化 |
| 语言资产变体 | 改写 locale data 后，扩展 shipped 资源与导出结果都要随之再生成 |
| 产物再生成 | 清空输出目录后重新执行，结果仍需完整生成 |

### ⚡ Skill 相关性评估

结论：相关性成立，但稳定性一般。这个任务里，`vscode-ext-localization` 的核心价值仍然是帮助 solver 把一个 VS Code 扩展的多语言交付面一次性看全，并沿着现有扩展入口把这些面接齐。题目把多语言命令、视图、引导内容、运行态消息、locale data 同步和导出简报放在同一条交付链路上，能有效拦住只做单一语言导出或只补局部文案的解法；同时，最近对照显示 locale copy 到导出简报这一步仍有收敛波动。

基于最近 **3** 次有效对比实验（均为真正跑到 task-level、存在完整 agent 轨迹；已排除启动失败类 trial）：

| 维度 | Without Skill | With Skill | 结果对比 |
| :--- | :--- | :--- | :--- |
| 通过率 | `0%` | `33%` | 近 3 次有效对照里，Without Skill 都卡在 locale copy 变更未完整传到导出葡语简报；With Skill 有 1 次完整通过，另外 2 次仍在同一条单一来源同步上失手。 |
| Agent 执行耗时 | `312.7s` | `315.1s` | 两侧耗时基本持平；With Skill 平均高约 `0.8%`，主要波动来自两次未完全收敛的复查。 |
| Tokens | `1.12M` | `0.90M` | With Skill 的上下文开销更低，Without Skill 约为 With Skill 的 `1.24x`。 |

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
└── solution/
```
