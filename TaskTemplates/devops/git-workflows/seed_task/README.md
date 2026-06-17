# Git-Workflows Template

这是面向 `git-workflows` 类 skill 的模板。它综合参考 SkillsMP `git-workflows` 类热门 skill 的共性能力：在不破坏现有工作区状态的前提下准备隔离分支、沿既有 git 历史完成修复、保留真实验证链路、并生成可交付的变更说明与结果产物。

## 第一部分：任务设计参考

* **Skill 价值定位**：`git-workflows` 类热门 skill 的核心价值，不是单纯给出 git 命令，而是帮助 solver 在分支、工作区、提交历史和交付链之间做出正确动作选择。对于 `using-git-worktrees` 这一类 skill，价值尤其体现在“当前工作区不能动，但另一条修复链必须继续”时，能快速建立可靠的隔离工作区并保护现场状态。
* **Verifier 设计重点**：Verifier 应优先验证 solver 是否沿真实 git 工作流完成了动作，例如是否保护了主工作目录、是否从正确基线分支衍生出修复链路、是否在预置的隐藏 worktree 目录而非主 checkout 或随意目录中完成修复、以及是否让该隔离工作区上的真实发布链路可以复跑。

## 第二部分：示例任务

### 📌 任务元数据

- 任务 ID：`git-workflows__meridian-hotfix-isolated-worktree`
- 类别：`git-workflows`
- 绑定 Skill：`using-git-worktrees`
- 输入数据参考来源：
  - `environment/data/reference/git_worktree.md`：任务内隔离工作区流程参考；直接来源于 Git 官方 `git-worktree` 文档  
    https://git-scm.com/docs/git-worktree
  - `environment/data/reference/github_flow.md`：任务内分支工作流参考；直接来源于 GitHub Docs `GitHub flow`  
    https://docs.github.com/en/get-started/using-github/github-flow
  - `environment/data/reference/conventional_commits.md`：任务内提交约定参考；直接来源于 Conventional Commits `1.0.0`  
    https://www.conventionalcommits.org/en/v1.0.0/
  - `environment/data/reference/keep_a_changelog.md`：任务内 release notes 设计参考；直接来源于 Keep a Changelog `1.1.0`  
    https://keepachangelog.com/en/1.1.0/
  - `environment/data/changelog_fragments.ndjson`：任务内 hotfix release notes 片段；设计形态参考 Git 项目的公开 release notes  
    https://github.com/git/git/blob/master/Documentation/RelNotes/2.45.0.adoc  
    https://github.com/git/git/blob/master/Documentation/RelNotes/2.46.0.adoc

### 📊 验证与测试指标（Oracle & Verifier）

- Oracle：按正式流程独立运行并完成交付，结果可直接 100% 通过验证。
- Verifier策略：

主测试
| 测试点 | 验证内容 | 对应skill内化点 |
| :--- | :--- | :--- |
| 输出产物 | 检查 hotfix report 和 release notes 是否存在、可解析、业务事实正确 | 先完成真实修复链，再交付结构化结果 |
| 热修复脚本复跑 | 在目标 worktree 中重新执行现有 hotfix 脚本并要求成功 | 在正确工作区完成真实链路，而不是一次性伪造结果 |
| worktree 裸测试复跑 | 在目标 worktree 中直接执行 `pytest -q tests/test_pricing.py` 并要求成功 | 建立可直接复跑的隔离工作区基线，而不是依赖一次性环境技巧 |
| 隐藏回归用例 | 用额外输入重测定价逻辑，确认回归真正修复 | 修复真实 bug，而不是只对显式样例特判 |
| release notes 重算 | 从输入数据重算 release notes 文本并核对内容 | 让变更说明来源于事实数据，而不是手写摘要 |

防作弊测试
| 测试点 | 验证内容 |
| :--- | :--- |
| 主工作目录保护 | 主 checkout 的当前分支、dirty status 和 dirty diff 必须与初始状态完全一致 |
| 隔离工作区动作 | 目标 hotfix 分支必须存在于预置隐藏 `.worktrees/` 下的 linked worktree，且不允许直接在主 checkout 完成修复 |
| 基线 ancestry | hotfix 分支必须以指定 release branch 为祖先 |
| 变更范围约束 | hotfix 分支提交不能去改写无关的 release 打包/报告脚本，只允许落在 checkout 逻辑与测试引导相关文件 |
| 输入完整性 | `/root/data` 的内容哈希必须保持不变 |

### ⚡ Skill 相关性评估

结论：强相关。这个任务里，Skill 的核心价值不只是“创建一个 worktree”，而是把隔离工作区建立、worktree 内基线自检、以及后续 hotfix 收敛动作串成一条稳定工作流。without Skill 理论上仍可解，但更容易在 worktree 基线没跑通时转去改写无关发布链脚本，或者只让单次入口勉强通过，却没有把隔离工作区本身修成可直接复跑的状态。

基于最近 **3** 次有效对比实验（均为真正跑到 task-level、存在完整 agent 轨迹；已排除启动失败类 trial）：

| 维度 | Without Skill | With Skill | 结果对比 |
| :--- | :--- | :--- | :--- |
| 通过率 | `0% (0/3)` | `100% (3/3)` | 3 次有效对照里，without Skill 都保留了至少一项 action-level 失败；with Skill 则稳定完成隐藏 `.worktrees/` 路径、主工作目录保护和真实 hotfix 链路复跑。 |
| Agent 执行耗时 | `282.4s` | `278.4s` | 两侧耗时接近，with Skill 平均略低约 `1.4%`；本任务的核心收益主要体现在动作正确性与收敛方向，而不是单纯 wall-clock 压缩。 |
| Tokens | `383.9k` | `392.2k` | without Skill 的 tokens 略低约 `2.1%`，但这是因为它更快收敛到了错误动作；在 task-level 上并没有转化为通过结果。 |

## 📁 标准目录结构说明

```text
seed_task/
├── instruction.md
├── task.toml
├── PLAN.json
├── README.md
├── environment/
│   ├── Dockerfile
│   ├── bootstrap/
│   ├── data/
│   └── skills/
├── tests/
└── solution/
```
