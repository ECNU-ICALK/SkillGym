import assert from "node:assert/strict";
import {
  buildBlockingReviewerPrompt,
  buildRepairPrompt,
  buildSingleTaskPlannerPrompt,
  buildTaskAttemptBrief,
  buildTaskWriterPrompt,
} from "../src/prompts.js";
import type { DerivedTaskPlan } from "../src/schema.js";
import { buildGenerationUnits, type GenerationUnit, type SkillInfo, type TaskTemplate } from "../src/discovery.js";

const debugSkill: SkillInfo = {
  name: "Node Connect",
  dirName: "01__node-connect",
  relativeDir: "01__node-connect",
  sourceDir: "/tmp/skills/01__node-connect",
  skillMdPath: "/tmp/skills/01__node-connect/SKILL.md",
};

const sessionSkill: SkillInfo = {
  name: "Session Logs",
  dirName: "03__session-logs",
  relativeDir: "03__session-logs",
  sourceDir: "/tmp/skills/03__session-logs",
  skillMdPath: "/tmp/skills/03__session-logs/SKILL.md",
};

const template: TaskTemplate = {
  templateId: "tools__debugging",
  templateRelativePath: "tools/debugging",
  sourceDir: "/tmp/template/tools/debugging",
  taskTomlPath: "/tmp/template/tools/debugging/task.toml",
  instructionPath: "/tmp/template/tools/debugging/instruction.md",
  environmentDir: "/tmp/template/tools/debugging/environment",
  solutionDir: "/tmp/template/tools/debugging/solution",
  testsDir: "/tmp/template/tools/debugging/tests",
  templateSkillsDir: "/tmp/template/tools/debugging/environment/skills",
  metadata: {
    id: "debugging-template",
    name: "Debugging Template",
    difficulty: "hard",
    category: "debugging",
    tags: ["debugging", "node"],
  },
  referenceSkills: [debugSkill],
};

const unit: GenerationUnit = {
  template,
  inputSkills: [debugSkill],
  skillMode: "per-skill",
  targetSkill: debugSkill,
  scopeSlug: "01__node-connect",
  scopeLabel: "Node Connect",
  taskCount: 5,
  pendingTaskOrdinals: [1, 2, 3, 4, 5],
  finalFamilyDir: "/tmp/output/final/tools__debugging/01__node-connect",
  publishedTasks: [],
};

const historyAwareUnit: GenerationUnit = {
  ...unit,
  pendingTaskOrdinals: [2],
  publishedTasks: [
    {
      derivedTaskId: "task1",
      taskOrdinal: 1,
      taskDir: "/tmp/output/final/tools__debugging/01__node-connect/task1__with_skill",
      planPath: "/tmp/output/final/tools__debugging/01__node-connect/task1__with_skill/plan.json",
      instructionPath: "/tmp/output/final/tools__debugging/01__node-connect/task1__with_skill/instruction.md",
      taskTomlPath: "/tmp/output/final/tools__debugging/01__node-connect/task1__with_skill/task.toml",
      testOutputsPath: "/tmp/output/final/tools__debugging/01__node-connect/task1__with_skill/tests/test_outputs.py",
      environmentDir: "/tmp/output/final/tools__debugging/01__node-connect/task1__with_skill/environment",
    },
  ],
};

const plan: DerivedTaskPlan = {
  derivedTaskId: "task1",
  taskOrdinal: 1,
  title: "Debugging Task 1",
  realWorldContext: "A production dashboard team is investigating service connectivity incidents from real operations.",
  referenceData: "Reference data:\n\n- Node.js net documentation: https://nodejs.org/api/net.html",
  taskGoal: "Repair the failing dashboard service.",
  inputAssets: "Provide offline service logs and a minimal Node.js connection fixture.",
  requiredOutputs: "The agent must update the service config and produce a short incident note.",
  verifierFocus: "Check connectivity behavior, config semantics, and the incident note contract.",
  skillBenefitRationale: "Requires the injected debugging workflow.",
  difficulty: "hard",
  category: "debugging",
  templateId: template.templateId,
  skillMode: "per-skill",
  targetSkillDirName: debugSkill.dirName,
  targetSkillName: debugSkill.name,
};

const brief = buildTaskAttemptBrief(unit, plan, {
  attemptIndex: 2,
});
const singleTaskPlannerPrompt = buildSingleTaskPlannerPrompt(unit, {
  derivedTaskId: plan.derivedTaskId,
  taskOrdinal: plan.taskOrdinal,
});
const writerPrompt = buildTaskWriterPrompt(unit, plan);
const blockingReviewerPrompt = buildBlockingReviewerPrompt(unit, plan);
const historyWriterPrompt = buildTaskWriterPrompt(historyAwareUnit, plan);
const historyBlockingReviewerPrompt = buildBlockingReviewerPrompt(historyAwareUnit, plan);
const repairPrompt = buildRepairPrompt({
  unit,
  plan,
  blockingIssues: ["reviewer:task1 instruction.md leaked the skill name"],
  staticIssues: ["static:task1 task.toml metadata.source_template_id is wrong"],
  runtimeIssues: ["runtime:task1 harbor verifier reward=0 < 1.0"],
  skillEffectIssues: ["skill-effect:task1 with_skill_pass__no_skill_invalid_fail"],
  runtimeLogRoot: "/tmp/artifacts/runtime/task1/cycle-0-attempt-1",
  skillEffectEvidenceRoot: "/tmp/artifacts/skill_effect/task1/cycle-0-attempt-1",
  skillEffectResultPath: "/tmp/artifacts/task1.skill-effect.cycle-0.attempt-1.json",
});

const allModeUnit = buildGenerationUnits(template, [debugSkill, sessionSkill], {
  skillMode: "all",
  taskCount: 2,
})[0];
const threeTaskUnit = buildGenerationUnits(template, [debugSkill], {
  skillMode: "per-skill",
  taskCount: 3,
})[0];
const allModeBrief = buildTaskAttemptBrief(
  allModeUnit!,
  {
    derivedTaskId: "task1",
    taskOrdinal: 1,
  },
  {
    attemptIndex: 1,
  },
);

assert.equal(allModeUnit?.scopeSlug, "all-skills");
assert.deepEqual(threeTaskUnit?.pendingTaskOrdinals, [1, 2, 3]);

assert.match(brief, /当前 task: task1 \(Task 1\)/);
assert.match(brief, /当前 attempt: attempt-2/);
assert.match(brief, /当前唯一允许修改的任务目录: draft\//);
assert.match(brief, /当前证据目录: artifacts\//);
assert.match(brief, /历史 attempt 和其他 task 的未发布草稿都不属于当前上下文/);
assert.match(brief, /模板目录: template_source\//);
assert.match(brief, /输入 skills 目录: input_skills\//);
assert.match(brief, /draft\/environment\/skills\/ 由系统从 input_skills\/ 预注入/);
assert.match(brief, /这些 injected skills 是只读 payload/);
assert.match(brief, /template_source\/environment\/skills\/ 里的内容只作为模板上下文参考/);
assert.match(brief, /最终 shipped skills 只由 input_skills\/ 决定/);
assert.match(brief, /Harbor 任务格式摘要/);
assert.match(brief, /instruction\.md：用户可见的任务说明与约束/);
assert.match(brief, /solution\/solve\.sh：用于证明任务可行性的 oracle 解法/);
assert.match(brief, /tests\/test\.sh：verifier 入口/);
assert.match(brief, /Harbor 会先在容器化环境中运行 agent，再执行 \/tests\/test\.sh 来判定 reward/);
assert.match(brief, /\/logs\/、\/oracle\/、\/tests\//);
assert.doesNotMatch(brief, /builder_refs\/harbor/);
assert.match(brief, /正式历史任务只看 final-root 下已发布的 \*__with_skill 任务/);
assert.doesNotMatch(brief, /family 增量/);
assert.doesNotMatch(brief, /familyTheme/);
assert.doesNotMatch(brief, /similarTasks/);
assert.doesNotMatch(brief, /transferTasks/);
assert.doesNotMatch(brief, /drafts\//);

assert.match(singleTaskPlannerPrompt, /当前只规划一个任务 task1/);
assert.match(singleTaskPlannerPrompt, /你只需要为当前槽位返回一个单题 blueprint/);
assert.match(singleTaskPlannerPrompt, /web search/);
assert.match(singleTaskPlannerPrompt, /referenceData/);
assert.match(singleTaskPlannerPrompt, /realWorldContext/);
assert.match(singleTaskPlannerPrompt, /taskGoal/);
assert.match(singleTaskPlannerPrompt, /inputAssets/);
assert.match(singleTaskPlannerPrompt, /requiredOutputs/);
assert.match(singleTaskPlannerPrompt, /verifierFocus/);
assert.match(singleTaskPlannerPrompt, /只返回 schema 要求的 10 个字段/);
assert.doesNotMatch(singleTaskPlannerPrompt, /只返回 schema 要求的 5 个字段/);
assert.match(singleTaskPlannerPrompt, /derivedTaskId、taskOrdinal、templateId、skillMode、targetSkillDirName、targetSkillName 由程序补齐/);
assert.match(singleTaskPlannerPrompt, /display name: Task 1/);
assert.match(singleTaskPlannerPrompt, /历史 attempt 和其他未发布草稿都不是正式去重基准/);
assert.doesNotMatch(singleTaskPlannerPrompt, /family planner/);
assert.doesNotMatch(singleTaskPlannerPrompt, /familyTheme/);
assert.doesNotMatch(singleTaskPlannerPrompt, /similarTasks/);
assert.doesNotMatch(singleTaskPlannerPrompt, /transferTasks/);
assert.doesNotMatch(singleTaskPlannerPrompt, /primaryOutputFile/);

assert.match(writerPrompt, /template_source\/、input_skills\/、当前 task 的 plan\.json blueprint/);
assert.match(writerPrompt, /realWorldContext、referenceData、taskGoal、inputAssets、requiredOutputs、verifierFocus/);
assert.doesNotMatch(writerPrompt, /builder_refs\/harbor/);
assert.match(writerPrompt, /metadata\.source_template_id 必须等于 "tools__debugging"/);
assert.match(writerPrompt, /environment\/skills\/ 中只能保留一个 shipped skill/);
assert.match(writerPrompt, /这些 injected skills 是只读 payload/);
assert.match(writerPrompt, /不是当前任务必须参考的去重对象/);
assert.match(writerPrompt, /只以 final-root 下已经发布的 \*__with_skill 同 family 任务为准/);
assert.match(writerPrompt, /不要把 \*__no_skill 对照副本当成历史任务/);
assert.match(writerPrompt, /当前只允许修改 draft\/ 内的文件/);
assert.match(writerPrompt, /非 skill 输入资产，应优先 COPY 到 WORKDIR 或其子目录/);
assert.match(writerPrompt, /纯可执行工具可以放在 \/usr\/local\/bin/);
assert.match(writerPrompt, /不得把 skills 复制到普通运行时路径/);
assert.match(writerPrompt, /唯一允许语句是 COPY skills \/root\/\.codex\/skills/);
assert.match(writerPrompt, /不要再添加任何把 skills\/ 或 \/root\/\.codex\/skills 复制、移动、同步、软链接到其他目录/);
assert.match(writerPrompt, /instruction\.md 写作契约/);
assert.match(writerPrompt, /不要明说“使用某个 skill”/);
assert.match(writerPrompt, /Brief opening, Input data, Your task, Output, Notes/);
assert.match(writerPrompt, /未修改的初始 environment 必须无法通过 verifier/);
assert.match(writerPrompt, /solution\/solve\.sh 必须像真实 solver 一样/);
assert.match(writerPrompt, /verifier 主测试只能断言 instruction\.md 明确写出的用户可见契约/);
assert.match(writerPrompt, /防作弊测试只能检测硬编码、fixture 过拟合或 shortcut 行为/);
assert.match(writerPrompt, /shipped skill payload、installed skill path 等内部实现细节/);
assert.match(writerPrompt, /不得对已发布 sibling 任务做简单领域换皮/);
assert.doesNotMatch(writerPrompt, /primaryOutputFile/);
assert.doesNotMatch(writerPrompt, /primary_output_file/);
assert.match(historyWriterPrompt, /已发布 Harbor family 目录/);
assert.match(historyWriterPrompt, /task1__with_skill/);

assert.match(blockingReviewerPrompt, /单题 blocking 审查/);
assert.match(blockingReviewerPrompt, /writer 不应改写 injected skill payload/);
assert.match(blockingReviewerPrompt, /taskResults 中只返回当前这个任务/);
assert.match(blockingReviewerPrompt, /历史任务去重主要由 planner\/writer 负责/);
assert.match(blockingReviewerPrompt, /reviewer 不需要逐项复审已发布任务/);
assert.match(blockingReviewerPrompt, /明显复制已发布 \*__with_skill 任务的场景、输入资产、输出契约和 verifier 策略/);
assert.match(blockingReviewerPrompt, /未修改的初始 environment 如果可以通过 verifier/);
assert.match(blockingReviewerPrompt, /solution\/solve\.sh 是否像真实 solver 一样/);
assert.doesNotMatch(blockingReviewerPrompt, /builder_refs\/harbor/);
assert.match(blockingReviewerPrompt, /当前 task:\s+- task1 \(Task 1\) -> draft\//);
assert.match(blockingReviewerPrompt, /当前只审这个 task 的当前 attempt/);
assert.doesNotMatch(blockingReviewerPrompt, /当前 family 规划:/);
assert.match(historyBlockingReviewerPrompt, /历史任务去重主要由 planner\/writer 负责/);
assert.doesNotMatch(historyBlockingReviewerPrompt, /已发布 tasks:/);
assert.doesNotMatch(historyBlockingReviewerPrompt, /task1__with_skill/);

assert.match(repairPrompt, /不要修改 template_source\/、input_skills\/、artifacts\//);
assert.doesNotMatch(repairPrompt, /builder_refs\//);
assert.match(repairPrompt, /不要修改 environment\/skills\/ 下 injected skill 的内容/);
assert.match(repairPrompt, /family workspace 根目录、历史 attempt、Harbor 仓库代码/);
assert.match(repairPrompt, /你还可以读取这些本 attempt 的运行证据/);
assert.match(repairPrompt, /Oracle runtime evidence root: \/tmp\/artifacts\/runtime\/task1\/cycle-0-attempt-1/);
assert.match(repairPrompt, /Skill-effect evidence root: \/tmp\/artifacts\/skill_effect\/task1\/cycle-0-attempt-1/);
assert.match(repairPrompt, /skill-effect 总结 JSON: \/tmp\/artifacts\/task1\.skill-effect\.cycle-0\.attempt-1\.json/);
assert.doesNotMatch(repairPrompt, /Oracle fallback evidence root/);
assert.doesNotMatch(repairPrompt, /Oracle fallback summary JSON/);
assert.doesNotMatch(repairPrompt, /with_skill 日志根目录/);
assert.doesNotMatch(repairPrompt, /with_skill 结果 JSON/);
assert.doesNotMatch(repairPrompt, /no_skill reward 文件/);
assert.doesNotMatch(repairPrompt, /no_skill 结果 JSON/);
assert.match(repairPrompt, /metadata\.source_template_id/);
assert.match(repairPrompt, /blocking reviewer:/);
assert.match(repairPrompt, /非 skill 输入资产，应优先 COPY 到 WORKDIR 或其子目录/);
assert.match(repairPrompt, /唯一允许语句是 COPY skills \/root\/\.codex\/skills/);
assert.match(repairPrompt, /with_skill_pass__no_skill_invalid_fail/);
assert.match(repairPrompt, /已发布 \*__with_skill sibling \/ 历史任务过近/);
assert.match(repairPrompt, /Brief opening, Input data, Your task, Output, Notes/);
assert.match(repairPrompt, /不要为了保留过窄测试而把 hidden requirement 硬塞进 instruction\.md/);
assert.match(repairPrompt, /修复 solution\/solve\.sh 时，必须像真实 solver 一样/);
assert.match(repairPrompt, /未修改的初始 workspace 必须仍然不能通过 verifier/);
assert.match(repairPrompt, /修复 verifier 主测试时，只能断言 instruction\.md 明确写出的用户可见契约/);
assert.match(repairPrompt, /修复防作弊测试时，只能检测硬编码、fixture 过拟合或 shortcut 行为/);
assert.doesNotMatch(repairPrompt, /family:/);
assert.doesNotMatch(repairPrompt, /primaryOutputFile/);
assert.doesNotMatch(repairPrompt, /primary_output_file/);

assert.match(allModeBrief, /当前 task 必须保留全部输入 skills 的关键能力点和实际解题收益/);
