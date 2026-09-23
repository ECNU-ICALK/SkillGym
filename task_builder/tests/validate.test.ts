import assert from "node:assert/strict";
import os from "node:os";
import path from "node:path";
import { promises as fs } from "node:fs";
import type { GenerationUnit, SkillInfo, TaskTemplate } from "../src/discovery.js";
import {
  appendManifest,
  buildManifestPath,
  buildRunSummaryPath,
  writeRunSummary,
} from "../src/manifest.js";
import { buildAcceptanceFinalRoot, buildPublishedVariantTaskDir, sanitizeAndCopyTask } from "../src/materialize.js";
import { inspectPublishedFamily, selectExecutableUnits } from "../src/published.js";
import {
  type BlockingReviewResult,
  type DerivedTaskPlan,
} from "../src/schema.js";
import {
  buildSkillEffectBucket,
  isAcceptedSkillEffectBucket,
  isRepairRequiredSkillEffectBucket,
  prepareNoSkillVariant,
  prepareWithSkillVariant,
  stripSkillCopyLines,
} from "../src/skill_effect.js";
import { archiveTracePairs } from "../src/trace_archive.js";
import {
  buildFinalRoot,
  buildRawRoot,
  ensureDir,
  pathExists,
  readText,
  runCommand,
  writeText,
} from "../src/utils.js";
import {
  createFamilyWorkspace,
  createTaskAttemptWorkspace,
  prepareAttemptDraftSkeleton,
} from "../src/workspace.js";
import {
  validateBlockingReviewResult,
  validateDraftStatic,
  validateTaskPlans,
} from "../src/validate.js";

const fixtureRoot = await fs.mkdtemp(path.join(os.tmpdir(), "codex-task-builder-v2-"));

async function createSkillFixture(dirName: string, name: string): Promise<SkillInfo> {
  const sourceDir = path.join(fixtureRoot, "skills", dirName);
  await ensureDir(sourceDir);
  await writeText(path.join(sourceDir, "SKILL.md"), `---\nname: "${name}"\n---\n`);
  await writeText(path.join(sourceDir, "notes.txt"), `${name}\n`);
  return {
    name,
    dirName,
    relativeDir: dirName,
    sourceDir,
    skillMdPath: path.join(sourceDir, "SKILL.md"),
  };
}

const nodeConnectSkill = await createSkillFixture("01__node-connect", "Node Connect");
const sessionLogsSkill = await createSkillFixture("03__session-logs", "Session Logs");

const template: TaskTemplate = {
  templateId: "tools__debugging",
  templateRelativePath: "tools/debugging",
  sourceDir: path.join(fixtureRoot, "template", "tools", "debugging"),
  taskTomlPath: path.join(fixtureRoot, "template", "tools", "debugging", "task.toml"),
  instructionPath: path.join(fixtureRoot, "template", "tools", "debugging", "instruction.md"),
  environmentDir: path.join(fixtureRoot, "template", "tools", "debugging", "environment"),
  solutionDir: path.join(fixtureRoot, "template", "tools", "debugging", "solution"),
  testsDir: path.join(fixtureRoot, "template", "tools", "debugging", "tests"),
  templateSkillsDir: path.join(fixtureRoot, "template", "tools", "debugging", "environment", "skills"),
  metadata: {
    id: "debugging-template",
    name: "Debugging Template",
    difficulty: "hard",
    category: "debugging",
    tags: ["debugging"],
  },
  referenceSkills: [],
};

const perSkillUnit: GenerationUnit = {
  template,
  inputSkills: [nodeConnectSkill],
  skillMode: "per-skill",
  targetSkill: nodeConnectSkill,
  scopeSlug: nodeConnectSkill.dirName,
  scopeLabel: nodeConnectSkill.name,
  taskCount: 2,
  pendingTaskOrdinals: [1, 2],
  finalFamilyDir: "/tmp/final/tools__debugging/01__node-connect",
  publishedTasks: [],
};

const allSkillUnit: GenerationUnit = {
  template,
  inputSkills: [nodeConnectSkill, sessionLogsSkill],
  skillMode: "all",
  targetSkill: null,
  scopeSlug: "all-skills",
  scopeLabel: "All input skills",
  taskCount: 2,
  pendingTaskOrdinals: [1, 2],
  finalFamilyDir: "/tmp/final/tools__debugging/all-skills",
  publishedTasks: [],
};

const plan: DerivedTaskPlan = {
  derivedTaskId: "task1",
  taskOrdinal: 1,
  title: "Task 1",
  realWorldContext: "A platform team is investigating real service connectivity failures.",
  referenceData: "Reference data:\n\n- Node.js net documentation: https://nodejs.org/api/net.html",
  taskGoal: "Repair the failing service.",
  inputAssets: "Provide offline logs and broken configuration files.",
  requiredOutputs: "The agent must update the configuration and write a diagnosis report.",
  verifierFocus: "Check service behavior and report content against the promised contract.",
  skillBenefitRationale: "Requires the injected debugging workflow.",
  difficulty: "hard",
  category: "debugging",
  templateId: template.templateId,
  skillMode: "per-skill",
  targetSkillDirName: nodeConnectSkill.dirName,
  targetSkillName: nodeConnectSkill.name,
};

async function makeDraftFixture(
  unit: GenerationUnit,
  taskPlan: DerivedTaskPlan,
  options: {
    sourceTemplateId?: string;
    instructionText?: string;
    dockerfile?: string;
    mutateInjectedSkill?: boolean;
    visibleSkillOverride?: SkillInfo[];
    includeLegacyPrimaryOutputFile?: boolean;
  } = {},
): Promise<string> {
  const root = await fs.mkdtemp(path.join(os.tmpdir(), "codex-builder-draft-"));
  const visibleSkills = options.visibleSkillOverride ?? unit.inputSkills;

  await ensureDir(path.join(root, "environment", "skills"));
  for (const skill of visibleSkills) {
    await fs.cp(skill.sourceDir, path.join(root, "environment", "skills", skill.dirName), { recursive: true, force: true });
  }
  if (options.mutateInjectedSkill) {
    await writeText(
      path.join(root, "environment", "skills", visibleSkills[0]!.dirName, "notes.txt"),
      "mutated\n",
    );
  }

  await ensureDir(path.join(root, "solution"));
  await ensureDir(path.join(root, "tests"));
  await writeText(path.join(root, "plan.json"), `${JSON.stringify(taskPlan, null, 2)}\n`);
  const legacyPrimaryOutputFileLine = options.includeLegacyPrimaryOutputFile
    ? 'primary_output_file = "legacy-output.txt"\n'
    : "";
  await writeText(
    path.join(root, "task.toml"),
    `version = "1.0"

[metadata]
id = "${taskPlan.derivedTaskId}"
name = "Task ${taskPlan.taskOrdinal} | Fixture"
description = "Fixture task."
author_name = "Test Author"
author_email = "test@example.com"
difficulty = "${taskPlan.difficulty}"
category = "${taskPlan.category}"
tags = ["debugging", "fixture"]
${legacyPrimaryOutputFileLine}source_template_id = "${options.sourceTemplateId ?? taskPlan.templateId}"
task_role = "task"

[environment]
cpus = 2
memory_mb = 2048
storage_mb = 5120
gpus = 0
`,
  );
  await writeText(path.join(root, "instruction.md"), options.instructionText ?? "Repair the system.\n");
  await writeText(
    path.join(root, "environment", "Dockerfile"),
    options.dockerfile ?? "FROM ubuntu:24.04\nWORKDIR /root\nCOPY skills /root/.codex/skills\n",
  );
  await writeText(path.join(root, "solution", "solve.sh"), "#!/bin/bash\n");
  await writeText(path.join(root, "tests", "test.sh"), "#!/bin/bash\nmkdir -p /logs/verifier\n");
  await writeText(path.join(root, "tests", "test_outputs.py"), "def test_ok():\n    assert True\n");
  return root;
}

{
  const taskPlans: DerivedTaskPlan[] = [
    {
      derivedTaskId: "task1",
      taskOrdinal: 1,
      title: "Task 1",
      realWorldContext: "A",
      referenceData: "Reference data:\n\n- Source A: https://example.com/a",
      taskGoal: "A",
      inputAssets: "A",
      requiredOutputs: "A",
      verifierFocus: "A",
      skillBenefitRationale: "A",
      difficulty: "hard",
      category: "debugging",
      templateId: template.templateId,
      skillMode: "per-skill",
      targetSkillDirName: nodeConnectSkill.dirName,
      targetSkillName: nodeConnectSkill.name,
    },
    {
      derivedTaskId: "task2",
      taskOrdinal: 2,
      title: "Task 2",
      realWorldContext: "B",
      referenceData: "Reference data:\n\n- Source B: https://example.com/b",
      taskGoal: "B",
      inputAssets: "B",
      requiredOutputs: "B",
      verifierFocus: "B",
      skillBenefitRationale: "B",
      difficulty: "hard",
      category: "debugging",
      templateId: template.templateId,
      skillMode: "per-skill",
      targetSkillDirName: nodeConnectSkill.dirName,
      targetSkillName: nodeConnectSkill.name,
    },
  ];

  assert.deepEqual(validateTaskPlans(taskPlans, { taskOrdinals: [1, 2] }), []);
}

{
  const blockingReview: BlockingReviewResult = {
    taskResults: [
      {
        derivedTaskId: plan.derivedTaskId,
        blockingPass: false,
        blockingIssues: ["instruction.md leaked the shipped skill name"],
      },
    ],
  };
  const validation = validateBlockingReviewResult([plan], blockingReview);
  assert.equal(validation.taskIssuesById.get(plan.derivedTaskId)?.[0]?.scope, "reviewer");
  assert.match(
    validation.taskIssuesById.get(plan.derivedTaskId)?.[0]?.message ?? "",
    /leaked the shipped skill name/,
  );
}

{
  const cleanDraft = await makeDraftFixture(perSkillUnit, plan);
  try {
    const issues = await validateDraftStatic(cleanDraft, plan, perSkillUnit);
    assert.deepEqual(
      issues.map((issue) => issue.message),
      [],
    );
  } finally {
    await fs.rm(cleanDraft, { recursive: true, force: true });
  }
}

{
  const wrongMetadataDraft = await makeDraftFixture(perSkillUnit, plan, {
    sourceTemplateId: "wrong-template",
  });
  try {
    const issues = await validateDraftStatic(wrongMetadataDraft, plan, perSkillUnit);
    assert.ok(issues.some((issue) => issue.message.includes("metadata.source_template_id=wrong-template")));
  } finally {
    await fs.rm(wrongMetadataDraft, { recursive: true, force: true });
  }
}

{
  const legacyMetadataDraft = await makeDraftFixture(perSkillUnit, plan, {
    includeLegacyPrimaryOutputFile: true,
  });
  try {
    const issues = await validateDraftStatic(legacyMetadataDraft, plan, perSkillUnit);
    assert.deepEqual(issues, []);
  } finally {
    await fs.rm(legacyMetadataDraft, { recursive: true, force: true });
  }
}

{
  const mutatedSkillDraft = await makeDraftFixture(perSkillUnit, plan, {
    mutateInjectedSkill: true,
  });
  try {
    const issues = await validateDraftStatic(mutatedSkillDraft, plan, perSkillUnit);
    assert.ok(issues.some((issue) => issue.message.includes("与输入 skill 不一致")));
  } finally {
    await fs.rm(mutatedSkillDraft, { recursive: true, force: true });
  }
}

{
  const allModePlan: DerivedTaskPlan = {
    ...plan,
    derivedTaskId: "task1",
    taskOrdinal: 1,
    skillMode: "all",
    targetSkillDirName: "",
    targetSkillName: "",
  };
  const allModeDraft = await makeDraftFixture(allSkillUnit, allModePlan);
  try {
    const issues = await validateDraftStatic(allModeDraft, allModePlan, allSkillUnit);
    assert.deepEqual(issues, []);
  } finally {
    await fs.rm(allModeDraft, { recursive: true, force: true });
  }
}

{
  const outputRoot = path.join(fixtureRoot, "output");
  await appendManifest(
    {
      runId: "run-1",
      templateId: template.templateId,
      phase: "workspace",
      status: "completed",
    },
    outputRoot,
  );
  await writeRunSummary("run-1", { ok: true }, outputRoot);
  assert.equal(await pathExists(buildManifestPath(outputRoot)), true);
  assert.equal(await pathExists(buildRunSummaryPath(outputRoot, "run-1")), true);
  const manifestText = await readText(buildManifestPath(outputRoot));
  assert.match(manifestText, /"templateId":"tools__debugging"/);
}

{
  const outputRoot = path.join(fixtureRoot, "materialize-output");
  const rawRoot = buildRawRoot(outputRoot);
  const finalRoot = buildFinalRoot(outputRoot);
  await Promise.all([ensureDir(rawRoot), ensureDir(finalRoot)]);

  const sourceDraftDir = path.join(rawRoot, "run-1", template.templateId, nodeConnectSkill.dirName, "task1");
  await ensureDir(sourceDraftDir);
  await writeText(path.join(sourceDraftDir, "task.toml"), "x\n");
  await writeText(path.join(sourceDraftDir, "instruction.md"), "x\n");
  await ensureDir(path.join(sourceDraftDir, "environment"));
  await ensureDir(path.join(sourceDraftDir, "solution"));
  await ensureDir(path.join(sourceDraftDir, "tests"));
  await writeText(path.join(sourceDraftDir, "plan.json"), "{}\n");

  const result = await sanitizeAndCopyTask({
    sourceDraftDir,
    templateId: template.templateId,
    scopeSlug: nodeConnectSkill.dirName,
    taskName: "task1__with_skill",
    rawRoot,
    targetRoot: finalRoot,
  });
  assert.equal(result.disposition, "created");
  assert.equal(
    result.targetTaskDir,
    path.join(finalRoot, template.templateId, nodeConnectSkill.dirName, "task1__with_skill"),
  );
  assert.equal(
    buildPublishedVariantTaskDir({
      targetRoot: finalRoot,
      templateId: template.templateId,
      scopeSlug: nodeConnectSkill.dirName,
      taskName: "task1",
      variant: "no_skill",
    }),
    path.join(finalRoot, template.templateId, nodeConnectSkill.dirName, "task1__no_skill"),
  );
}

{
  const finalRoot = path.join(fixtureRoot, "published-final");
  const ignoredDirectFinalDir = path.join(finalRoot, template.templateId, nodeConnectSkill.dirName, "task1__with_skill");
  await ensureDir(path.join(ignoredDirectFinalDir, "tests"));
  await writeText(path.join(ignoredDirectFinalDir, "plan.json"), "{}\n");
  await writeText(path.join(ignoredDirectFinalDir, "instruction.md"), "x\n");
  await writeText(path.join(ignoredDirectFinalDir, "task.toml"), "x\n");
  await writeText(path.join(ignoredDirectFinalDir, "tests", "test_outputs.py"), "x\n");
  for (const oldDirName of ["similar1__with_skill", "transfer1__with_skill"]) {
    const ignoredOldFamilyDir = path.join(finalRoot, template.templateId, nodeConnectSkill.dirName, oldDirName);
    await ensureDir(path.join(ignoredOldFamilyDir, "tests"));
    await writeText(path.join(ignoredOldFamilyDir, "plan.json"), "{}\n");
    await writeText(path.join(ignoredOldFamilyDir, "instruction.md"), "x\n");
    await writeText(path.join(ignoredOldFamilyDir, "task.toml"), "x\n");
    await writeText(path.join(ignoredOldFamilyDir, "tests", "test_outputs.py"), "x\n");
  }
  for (const [acceptanceKind, taskName] of [
    ["pf_success", "task1__with_skill"],
    ["oracle_fallback_success", "task2__with_skill"],
  ] as const) {
    const publishedDir = path.join(
      buildAcceptanceFinalRoot(finalRoot, acceptanceKind),
      template.templateId,
      nodeConnectSkill.dirName,
      taskName,
    );
    await ensureDir(path.join(publishedDir, "tests"));
    await writeText(path.join(publishedDir, "plan.json"), "{}\n");
    await writeText(path.join(publishedDir, "instruction.md"), "x\n");
    await writeText(path.join(publishedDir, "task.toml"), "x\n");
    await writeText(path.join(publishedDir, "tests", "test_outputs.py"), "x\n");
  }

  const state = await inspectPublishedFamily(perSkillUnit, finalRoot);
  assert.equal(
    state.finalFamilyDir,
    path.join(buildAcceptanceFinalRoot(finalRoot, "pf_success"), template.templateId, nodeConnectSkill.dirName),
  );
  assert.deepEqual(state.publishedTasks.map((publishedTask) => publishedTask.derivedTaskId), ["task1", "task2"]);
  assert.deepEqual(state.publishedTasks.map((publishedTask) => publishedTask.acceptanceKind), [
    "pf_success",
    "oracle_fallback_success",
  ]);
  assert.deepEqual(state.pendingTaskOrdinals, []);

  const selected = selectExecutableUnits([
    { ...perSkillUnit, pendingTaskOrdinals: [1] },
    { ...perSkillUnit, scopeSlug: "queued", pendingTaskOrdinals: [1] },
    { ...perSkillUnit, scopeSlug: "done", pendingTaskOrdinals: [] },
  ]);
  assert.equal(selected.executableUnits.length, 2);
  assert.equal(selected.skippedCount, 1);

  const limitedSelected = selectExecutableUnits([
    { ...perSkillUnit, pendingTaskOrdinals: [1] },
    { ...perSkillUnit, scopeSlug: "queued", pendingTaskOrdinals: [1] },
    { ...perSkillUnit, scopeSlug: "done", pendingTaskOrdinals: [] },
  ], 1);
  assert.equal(limitedSelected.executableUnits.length, 1);
  assert.equal(limitedSelected.skippedCount, 2);

  const unlimitedSelected = selectExecutableUnits([
    { ...perSkillUnit, pendingTaskOrdinals: [1] },
    { ...perSkillUnit, scopeSlug: "queued", pendingTaskOrdinals: [1] },
    { ...perSkillUnit, scopeSlug: "done", pendingTaskOrdinals: [] },
  ], 0);
  assert.equal(unlimitedSelected.executableUnits.length, 2);
  assert.equal(unlimitedSelected.skippedCount, 1);
}

{
  const result = await runCommand("node", ["--import", "tsx", "src/cli.ts", "inventory", "--similar-count", "1"], {
    cwd: process.cwd(),
  });
  assert.notEqual(result.code, 0);
  assert.match(result.stderr, /改用 --task-count/);

  const repairResult = await runCommand("node", ["--import", "tsx", "src/cli.ts", "inventory", "--max-repair-rounds", "1"], {
    cwd: process.cwd(),
  });
  assert.notEqual(repairResult.code, 0);
  assert.match(repairResult.stderr, /max-repair-rounds 已拆分/);
}

{
  const stripped = stripSkillCopyLines("FROM ubuntu:24.04\nCOPY skills /root/.codex/skills\nRUN echo ok\n");
  assert.equal(stripped.removedCount, 1);
  assert.match(stripped.text, /RUN echo ok/);
  assert.equal(buildSkillEffectBucket("pass", "valid_reward_fail"), "with_skill_pass__no_skill_fail");
  assert.equal(buildSkillEffectBucket("pass", "invalid_fail"), "with_skill_pass__no_skill_invalid_fail");
  assert.equal(buildSkillEffectBucket("pass", "pass"), "with_skill_pass__no_skill_pass");
  assert.equal(isAcceptedSkillEffectBucket("with_skill_pass__no_skill_fail"), true);
  assert.equal(isAcceptedSkillEffectBucket("with_skill_pass__no_skill_invalid_fail"), false);
  assert.equal(isAcceptedSkillEffectBucket("with_skill_fail__no_skill_fail"), false);
  assert.equal(isRepairRequiredSkillEffectBucket("with_skill_fail__no_skill_fail"), true);
  assert.equal(isRepairRequiredSkillEffectBucket("with_skill_pass__no_skill_invalid_fail"), true);
  assert.equal(isRepairRequiredSkillEffectBucket("with_skill_fail__no_skill_pass"), true);
  assert.equal(
    buildAcceptanceFinalRoot("/tmp/output/final", "pf_success"),
    "/tmp/output/final/pf_success",
  );
}

{
  const outputRoot = path.join(fixtureRoot, "trace-archive-output");
  const sourceRoot = path.join(fixtureRoot, "trace-source");
  const withSkillResult = path.join(sourceRoot, "with_skill", "result.json");
  const withSkillTrajectory = path.join(sourceRoot, "with_skill", "trajectory.json");
  const noSkillResult = path.join(sourceRoot, "no_skill", "result.json");
  await writeText(withSkillResult, '{"agent_result":{"n_input_tokens":10},"started_at":"s","finished_at":"f"}\n');
  await writeText(withSkillTrajectory, '{"events":[]}\n');
  await writeText(noSkillResult, '{"verifier_result":{"rewards":{"reward":0}}}\n');
  await writeText(path.join(sourceRoot, "with_skill", "reward.txt"), "1\n");

  await archiveTracePairs({
    outputRoot,
    outcome: "pf_success",
    pairs: [
      {
        runId: "run-one",
        templateId: template.templateId,
        scopeSlug: nodeConnectSkill.dirName,
        derivedTaskId: "task1",
        attemptIndex: 2,
        cycle: 3,
        stage: "skill-effect",
        stageAttemptIndex: 4,
        pairRoot: sourceRoot,
        bucket: "with_skill_pass__no_skill_fail",
        withSkill: {
          status: "pass",
          passed: true,
          reward: 1,
          resultPath: withSkillResult,
          trajectoryPath: withSkillTrajectory,
        },
        noSkill: {
          status: "valid_reward_fail",
          passed: false,
          reward: 0,
          resultPath: noSkillResult,
        },
      },
    ],
  });

  const archivedPairDir = path.join(
    outputRoot,
    "trace_archive",
    "pf_success",
    template.templateId,
    nodeConnectSkill.dirName,
    "task1",
    "pair-run-run-one__attempt-2__cycle-3__skill-effect-4",
  );
  assert.equal(await pathExists(path.join(archivedPairDir, "with_skill", "result.json")), true);
  assert.equal(await pathExists(path.join(archivedPairDir, "with_skill", "trajectory.json")), true);
  assert.equal(await pathExists(path.join(archivedPairDir, "no_skill", "result.json")), true);
  assert.equal(await pathExists(path.join(archivedPairDir, "with_skill", "reward.txt")), false);
  const pairResult = JSON.parse(await readText(path.join(archivedPairDir, "pair_result.json"))) as {
    withSkill: { sourceResultPath: string };
  };
  assert.equal(pairResult.withSkill.sourceResultPath, withSkillResult);
}

{
  await ensureDir(path.join(template.sourceDir, "environment"));
  await ensureDir(path.join(template.sourceDir, "solution"));
  await ensureDir(path.join(template.sourceDir, "tests"));
  await writeText(path.join(template.sourceDir, "task.toml"), "x\n");
  await writeText(path.join(template.sourceDir, "instruction.md"), "x\n");
  await writeText(path.join(template.sourceDir, "environment", "Dockerfile"), "FROM ubuntu:24.04\nWORKDIR /root\n");

  const familyWorkspace = await createFamilyWorkspace(perSkillUnit, {
    rawRoot: path.join(fixtureRoot, "attempt-workspace-output", "raw"),
    runId: "run-attempts",
  });
  assert.equal(await pathExists(path.join(familyWorkspace.rootDir, "TASK_BUILDER_BRIEF.md")), false);
  const attemptOne = await createTaskAttemptWorkspace(familyWorkspace, perSkillUnit, plan, {
    attemptIndex: 1,
  });
  const attemptTwo = await createTaskAttemptWorkspace(familyWorkspace, perSkillUnit, plan, {
    attemptIndex: 2,
  });

  assert.equal(
    attemptOne.draftDir,
    path.join(familyWorkspace.rootDir, "task_attempts", plan.derivedTaskId, "attempt-1", "draft"),
  );
  assert.equal(
    attemptTwo.draftDir,
    path.join(familyWorkspace.rootDir, "task_attempts", plan.derivedTaskId, "attempt-2", "draft"),
  );

  await prepareAttemptDraftSkeleton(attemptOne, plan);
  assert.equal(await pathExists(path.join(attemptOne.draftDir, "plan.json")), true);
  assert.equal(await pathExists(path.join(attemptTwo.draftDir, "plan.json")), false);
  assert.equal(
    await pathExists(path.join(attemptOne.draftDir, "environment", "skills", nodeConnectSkill.dirName, "SKILL.md")),
    true,
  );
  assert.equal(await pathExists(attemptOne.briefPath), true);
  assert.match(await readText(attemptOne.briefPath), /当前 task: task1 \(Task 1\)/);
  assert.doesNotMatch(await readText(attemptOne.briefPath), /family 增量/);
}

{
  const sourceTaskDir = await fs.mkdtemp(path.join(os.tmpdir(), "codex-no-skill-source-"));
  const targetTaskDir = await fs.mkdtemp(path.join(os.tmpdir(), "codex-no-skill-target-"));
  const withSkillTargetDir = await fs.mkdtemp(path.join(os.tmpdir(), "codex-with-skill-target-"));
  try {
    await ensureDir(path.join(sourceTaskDir, "environment"));
    await writeText(
      path.join(sourceTaskDir, "environment", "Dockerfile"),
      "FROM ubuntu:24.04\nCOPY skills /root/.codex/skills\nRUN echo ok\n",
    );
    await writeText(path.join(sourceTaskDir, "task.toml"), "x\n");
    await writeText(path.join(sourceTaskDir, "instruction.md"), "x\n");
    await ensureDir(path.join(sourceTaskDir, "solution"));
    await ensureDir(path.join(sourceTaskDir, "tests"));
    await writeText(path.join(sourceTaskDir, "plan.json"), "{}\n");
    const withSkillPrepared = await prepareWithSkillVariant({
      sourceTaskDir,
      targetTaskDir: withSkillTargetDir,
    });
    assert.equal(await pathExists(path.join(withSkillPrepared.targetTaskDir, "task.toml")), true);
    const prepared = await prepareNoSkillVariant({
      sourceTaskDir: withSkillPrepared.targetTaskDir,
      targetTaskDir,
    });
    const dockerfile = await readText(path.join(prepared.targetTaskDir, "environment", "Dockerfile"));
    assert.equal(prepared.removedCopyLines, 1);
    assert.ok(!dockerfile.includes("COPY skills /root/.codex/skills"));
  } finally {
    await fs.rm(sourceTaskDir, { recursive: true, force: true });
    await fs.rm(targetTaskDir, { recursive: true, force: true });
    await fs.rm(withSkillTargetDir, { recursive: true, force: true });
  }
}
