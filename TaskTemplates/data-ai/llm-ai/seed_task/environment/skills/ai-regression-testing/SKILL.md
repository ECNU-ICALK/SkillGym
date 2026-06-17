---
name: "ai-regression-testing"
description: "Use when AI-assisted service changes need regression coverage across sandbox/live parity, structured outputs, retry and error handling, and repeated bug-fix loops."
---

# ai-regression-testing

来源：
- SkillsMP: `ai-regression-testing`
- URL: `https://skillsmp.com/skills/affaan-m-everything-claude-code-docs-zh-cn-skills-ai-regression-testing-skill-md`

## AI 回归测试

专为 AI 辅助开发设计的测试模式，其中同一模型既编写代码又审查代码。这会形成系统性盲点，只有自动化测试才能稳定发现。

### 何时激活

- AI 代理已经修改 API 路由或后端逻辑
- 刚发现并修复了一个 bug，需要防止重新引入
- 项目具有沙盒或模拟模式，可在不依赖数据库的情况下测试
- 代码更改后需要执行 `/bug-check` 或类似检查
- 系统存在多个代码路径，例如沙盒与生产、不同 feature flag

### 核心问题

常见失败模式：

`AI 编写修复 -> AI 审查修复 -> AI 认为“看起来正确” -> 漏洞依然存在`

高频回归模式：

- 沙盒路径和生产路径不一致
- 响应字段加了，但查询或数据选择没有同步补齐
- 错误状态出现后，旧状态或旧数据没有清掉
- 乐观更新失败后没有回滚
- `null` / `undefined` 被类型或分支逻辑掩盖

### 工作原则

- 为已经出现过的 bug 写回归测试，而不是给所有正常代码盲目补测试
- 优先测试 API 响应结构和行为合同，不要只测实现细节
- 如果有沙盒模式，优先使用沙盒模式做快速、确定性的 API 测试
- 先跑自动化测试，再做 AI 代码审查
- 每修一个 bug，都要补一个能复现并拦住它的测试

### 推荐工作流

#### 步骤 1：自动化测试

先运行：

```bash
npm run test
npm run build
```

规则：

- 如果测试失败，优先把失败视为真实缺陷信号
- 如果构建失败，优先处理类型或构建问题
- 只有两者都通过，才进入下一步

#### 步骤 2：代码审查

重点检查：

- 沙盒路径和生产路径是否保持同样的响应合同
- API 响应结构是否符合调用方预期
- 新字段是否真的被完整返回，而不是存在于表面映射中
- 错误处理是否清理旧状态
- 是否存在遗漏回滚、部分修复、只修单一路径的情况

#### 步骤 3：补回归测试

对每个修复过的 bug，补一条能精确拦住该 bug 再次出现的测试。

### 测试策略

- 重点验证必需字段是否都存在
- 重点验证字段不是 `undefined`
- 重点验证沙盒与生产路径是否返回同样的结构
- 重点验证错误时的清理和回滚
- 保持测试快速，优先使用无需数据库的路径

### 要 / 不要

要：

- 在发现 bug 后尽快补测试
- 测 API 合同和行为
- 把运行测试作为 bug 检查的第一步
- 用 bug 本身命名测试

不要：

- 为从未出过问题的区域盲目补测试
- 把 AI 自审当成自动化测试的替代品
- 因为是沙盒数据就跳过沙盒路径测试
- 为了覆盖率数字写大量低价值测试
