# Automation-Tools Template

这是面向 `automation-tools` 类 skill 的模板。它综合参考 SkillsMP `automation-tools` 类热门 skill 的共性能力：围绕公开输入材料完成结构化交付，复用既有本地入口，把版本材料、格式规则和输出合同串成可重复执行的工作流。

## 第一部分：任务设计参考

* **Skill 价值定位**：`automation-tools` 类热门 skill 的核心价值，是把零散发布材料收束成稳定的执行路径，让 solver 能较快识别输入、目标页、结构要求和收尾动作。对于 `docs-changelog` 这类 skill，价值主要体现在版本通道判断、页面职责划分和 changelog 内容整理。
* **Verifier 设计重点**：Verifier 应重点检查 solver 是否沿正式入口完成了可重复执行的结果，是否把内容写到正确目标页，是否根据输入版本走对分支，以及是否避免把任务收缩成一次性手工导出。防作弊测试应覆盖输入完整性、skill 区域完整性和错误页面更新。

## 第二部分：示例任务

### 📌 任务元数据

- 任务 ID：`automation_tools__channel_aware_changelog_delivery`
- 类别：`automation-tools`
- 绑定 Skill：`docs-changelog`
- 输入数据参考来源：
  - `environment/reference_bundle/workspace/docs/changelogs/index.md`：任务内发布总览页；直接来源于 Gemini CLI `v0.40.0` tag  
    【https://raw.githubusercontent.com/google-gemini/gemini-cli/v0.40.0/docs/changelogs/index.md】
  - `environment/reference_bundle/workspace/docs/changelogs/latest.md`：任务内 stable changelog 页；直接来源于 Gemini CLI `v0.40.0` tag  
    【https://raw.githubusercontent.com/google-gemini/gemini-cli/v0.40.0/docs/changelogs/latest.md】
  - `environment/reference_bundle/workspace/docs/changelogs/preview.md`：任务内 preview changelog 页；直接来源于 Gemini CLI `v0.40.0` tag  
    【https://raw.githubusercontent.com/google-gemini/gemini-cli/v0.40.0/docs/changelogs/preview.md】
  - `environment/reference_bundle/release_payload/release_page.html`：任务内 stable release 页面快照；直接来源于 Gemini CLI `v0.40.0` release page  
    【https://github.com/google-gemini/gemini-cli/releases/tag/v0.40.0】
  - `environment/reference_bundle/reference/releases.md`：任务内 release 流程参考；直接来源于 Gemini CLI 文档  
    【https://raw.githubusercontent.com/google-gemini/gemini-cli/main/docs/releases.md】
  - `environment/skills/docs-changelog/SKILL.md`：任务绑定 skill；直接来源于 Gemini CLI skill 目录  
    【https://raw.githubusercontent.com/google-gemini/gemini-cli/main/.gemini/skills/docs-changelog/SKILL.md】

### 📊 验证与测试指标（Oracle & Verifier）

- Oracle：按正式流程独立运行并完成交付，结果可直接 100% 通过验证。
- Verifier策略：

主测试
| 测试点 | 验证内容 | 对应skill内化点 |
| :--- | :--- | :--- |
| 正式产物生成 | 生成 `latest.md`、`preview.md`、`index.md` 和 `release_manifest.json` | 沿正式入口交付完整产物 |
| 通道判断 | 根据版本字符串判断 stable 或 preview，并更新正确页面 | 识别版本通道与页面职责 |
| 页面更新范围 | stable minor 更新 `latest.md` 与 `index.md`，其他页面按合同保留 | 只改应该改的目标页 |
| 高亮与公告 | `highlight_titles`、`announcement_prs`、changelog URL 与发布材料一致 | 从发布材料提炼结构化内容 |
| alternate fixture 泛化 | 切换到另一条版本通道后仍生成正确页面 | 不把流程写死在单一样例上 |

防作弊测试
| 测试点 | 验证内容 |
| :--- | :--- |
| 输入完整性 | `reference_bundle` 内容哈希保持一致 |
| Skill 可用性 | `docs-changelog` 在 with-skill 运行时可读，并作为只读结构化交付参考 |
| 输出白名单 | 输出目录顶层只保留合同要求的 4 个文件 |
| 错页写入 | 不允许把 stable 内容写进 `preview.md`，也不允许把 preview 内容写进 `latest.md` |
| 一次性导出 | 重新执行正式入口后结果仍一致 |

### ⚡ Skill 相关性评估

结论：强相关。这个任务里，Skill 的核心价值是把版本判断、页面选择、内容整理和收尾格式化串成一条稳定路径。没有这条路径时，solver 更容易只改当前看到的页面，或把 changelog 结果做成一次性输出文件，换一个版本通道后就会留下动作级失败。

基于最近 **3 次** 有效对照样本（with-skill 3 条、without-skill 3 条；均跑到 task-level，已排除 `build cancelled` 类启动失败）：

| 维度 | Without Skill | With Skill | 结果对比 |
| :--- | :--- | :--- | :--- |
| 通过率 | `0%` | `100%` | 最近 3 条有效 without-skill trial 都停在 preview / patch 通道判断或 `updated_files` 合同失败；with-skill 3 条均完成 9/9 测试 |
| Agent 执行耗时 | `298.5s` | `378.9s` | with-skill 会继续完成多分支交付与正式入口收尾；without-skill 更早停在分支遗漏上，因此平均耗时更短 |
| Tokens | `0.78M` | `0.83M` | without-skill 的 token 更少，主要因为没有覆盖完整 release 路径；with-skill 为完成交付消耗略高 |

## 📁 标准目录结构说明

```text
seed_task/
├── instruction.md
├── task.toml
├── PLAN.json
├── README.md
├── environment/
│   ├── Dockerfile
│   ├── reference_bundle/
│   └── skills/
├── tests/
└── solution/
```
