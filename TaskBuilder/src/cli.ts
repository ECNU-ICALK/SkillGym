import path from "node:path";
import { CodexTaskBuilderClient } from "./codex.js";
import {
  buildGenerationUnits,
  collectEnvironmentAssetPaths,
  discoverInputSkills,
  discoverTaskTemplate,
  discoverTaskTemplates,
  type PublishedTaskInfo,
  type GenerationUnit,
  type SkillMode,
} from "./discovery.js";
import { appendManifest, writeRunSummary, type ManifestEntry } from "./manifest.js";
import {
  buildAcceptanceFinalRoot,
  buildPublishedVariantTaskDir,
  sanitizeAndCopyTask,
  type AcceptanceKind,
} from "./materialize.js";
import { applyPublishedFamilyState, inspectPublishedFamily, selectExecutableUnits } from "./published.js";
import type { DerivedTaskPlan, SingleTaskPlan, WriterSummary } from "./schema.js";
import {
  buildSkillEffectIssues,
  runSkillEffectEvaluation,
  runSkillEffectPreflight,
  type SkillEffectBucket,
  type SkillEffectEvaluationResult,
} from "./skill_effect.js";
import { writeSkillEffectResultArtifact } from "./skill_effect_artifacts.js";
import { archiveTracePairs, type TraceArchivePair } from "./trace_archive.js";
import {
  DEFAULT_OUTPUT_ROOT,
  TEMPLATE_ROOT,
  buildFinalRoot,
  buildRawRoot,
  ensureDir,
  parseNonNegativeInteger,
  parseNonNegativeNumber,
  writeJson,
} from "./utils.js";
import {
  createFamilyWorkspace,
  createTaskAttemptWorkspace,
  prepareAttemptDraftSkeleton,
  type FamilyWorkspace,
  type TaskAttemptWorkspace,
} from "./workspace.js";
import {
  resolveRuntimeEnvironment,
  runRuntimePreflight,
  runRuntimeValidation,
  validateBlockingReviewResult,
  validateDraftStatic,
  validateTaskPlans,
  type RuntimeEnvironment,
  type RuntimeEvidence,
  type ValidationIssue,
} from "./validate.js";

type OptionValue = string | string[] | boolean;
type Options = Record<string, OptionValue>;

type FamilyExecutionResult = {
  templateId: string;
  skillMode: SkillMode;
  scopeSlug: string;
  targetSkillDirName?: string;
  targetSkillName?: string;
  runtimeEnvironment?: RuntimeEnvironment;
  runId?: string;
  status: "completed" | "failed";
  issues: string[];
  publishedTaskIds: string[];
  failedTaskIds: string[];
  publishedVariantDirs: Array<{
    derivedTaskId: string;
    acceptanceKind: AcceptanceKind;
    withSkillDir: string;
    noSkillDir: string | null;
  }>;
  failedTaskRefs: Array<{
    derivedTaskId: string;
    draftDir: string;
    latestRuntimeResultPath?: string;
    latestSkillEffectResultPath?: string;
    latestSkillEffectPairRoot?: string;
  }>;
  skillEffectResults: Array<{
    derivedTaskId: string;
    bucket: SkillEffectBucket;
    repairRequired: boolean;
    withSkillPassed: boolean;
    withSkillReward: number | null;
    withSkillSummary: string;
    noSkillPassed: boolean;
    noSkillReward: number | null;
    noSkillSummary: string;
    noSkillComparisonStatus: string;
    noSkillComparisonReason: string;
    withSkillVariantDir: string;
    noSkillVariantDir: string;
  }>;
  skillEffectBucketCounts: Partial<Record<SkillEffectBucket, number>>;
  workspace?: FamilyWorkspace;
};

type RepairStage = "pre_runtime" | "runtime" | "skill_effect";

type SkillEffectFallbackCandidate = {
  cycle: number;
  stageAttemptIndex: number;
  evaluation: SkillEffectEvaluationResult;
  resultPath: string;
  withSkillVariantDir: string;
  noSkillVariantDir: string;
};

type TaskCycleState = {
  attemptWorkspace: TaskAttemptWorkspace;
  attemptIndex: number;
  plan: DerivedTaskPlan;
  draftDir: string;
  writerSummary?: WriterSummary;
  repairThreadId: string | null;
  repairRoundsUsed: number;
  preRuntimeRepairRoundsUsed: number;
  runtimeRepairRoundsUsed: number;
  skillEffectRepairRoundsUsed: number;
  runtimeAttemptCount: number;
  skillEffectAttemptCount: number;
  blockingIssues: ValidationIssue[];
  staticIssues: ValidationIssue[];
  runtimeIssues: ValidationIssue[];
  skillEffectIssues: ValidationIssue[];
  runtimeEvidence?: RuntimeEvidence;
  skillEffectEvaluation?: SkillEffectEvaluationResult;
  skillEffectResultPath?: string;
  latestSkillEffectFallbackCandidate?: SkillEffectFallbackCandidate;
  acceptedWithSkillVariantDir?: string;
  acceptedNoSkillVariantDir?: string;
  acceptanceKind?: AcceptanceKind;
  tracePairs: TraceArchivePair[];
  passed: boolean;
};

type ExecuteFamilyOptions = {
  outputRoot: string;
  rawRoot: string;
  finalRoot: string;
  runtimeEnvironment: RuntimeEnvironment;
  maxPreRuntimeRepairRounds: number;
  maxRuntimeRepairRounds: number;
  maxSkillEffectRepairRounds: number;
  codexRunRetries: number;
  taskAttemptTimeoutHours: number;
  maxTaskRestarts: number;
  skillEffectEnabled: boolean;
  skillEffectModel: string;
  skillEffectApiKey: string;
  skillEffectBaseUrl?: string;
};

type TaskSlot = Pick<DerivedTaskPlan, "derivedTaskId" | "taskOrdinal">;

type TaskAttemptResult =
  | {
      status: "published";
      taskState: TaskCycleState;
      attemptWorkspace: TaskAttemptWorkspace;
      issues: string[];
    }
  | {
      status: "timed_out" | "exhausted_repairs";
      taskState?: TaskCycleState;
      attemptWorkspace: TaskAttemptWorkspace;
      issues: string[];
    };

function parseArgs(argv: string[]): { command: string | undefined; options: Options } {
  const [command, ...rest] = argv;
  const options: Options = {};

  for (let index = 0; index < rest.length; index += 1) {
    const token = rest[index];
    if (!token.startsWith("--")) {
      continue;
    }
    const key = token.slice(2);
    const next = rest[index + 1];
    if (!next || next.startsWith("--")) {
      options[key] = true;
      continue;
    }

    const existing = options[key];
    if (typeof existing === "string") {
      options[key] = [existing, next];
    } else if (Array.isArray(existing)) {
      existing.push(next);
    } else {
      options[key] = next;
    }
    index += 1;
  }

  return { command, options };
}

function getStringOption(options: Options, key: string, fallback?: string): string | undefined {
  const value = options[key];
  if (typeof value === "string") {
    return value;
  }
  if (Array.isArray(value)) {
    return value[value.length - 1] ?? fallback;
  }
  return fallback;
}

function getStringArrayOption(options: Options, key: string): string[] {
  const value = options[key];
  if (typeof value === "string") {
    return [value];
  }
  if (Array.isArray(value)) {
    return value;
  }
  return [];
}

function getNumberOption(options: Options, key: string, fallback: number): number {
  const value = getStringOption(options, key);
  if (!value) {
    return fallback;
  }
  const parsed = Number(value);
  return Number.isFinite(parsed) ? parsed : fallback;
}

function getNonNegativeIntegerOption(options: Options, key: string, fallback: number): number {
  return parseNonNegativeInteger(getStringOption(options, key), `--${key}`, fallback);
}

function getFlagOption(options: Options, key: string): boolean {
  return options[key] === true;
}

function getSkillModeOption(options: Options): SkillMode {
  const value = getStringOption(options, "skill-mode", "all");
  if (value === "all" || value === "per-skill") {
    return value;
  }
  throw new Error(`不支持的 --skill-mode: ${value}`);
}

function issueMessages(issues: ValidationIssue[]): string[] {
  return issues.map((issue) => `${issue.scope}${issue.taskId ? `:${issue.taskId}` : ""} ${issue.message}`);
}

function uniqueStrings(values: string[]): string[] {
  return Array.from(new Set(values));
}

function recordSkillEffectBucketCount(
  counts: Partial<Record<SkillEffectBucket, number>>,
  bucket: SkillEffectBucket,
): void {
  counts[bucket] = (counts[bucket] ?? 0) + 1;
}

function getRepairRoundsUsed(taskState: TaskCycleState, stage: RepairStage): number {
  if (stage === "pre_runtime") {
    return taskState.preRuntimeRepairRoundsUsed;
  }
  if (stage === "runtime") {
    return taskState.runtimeRepairRoundsUsed;
  }
  return taskState.skillEffectRepairRoundsUsed;
}

function getRepairRoundBudget(options: ExecuteFamilyOptions, stage: RepairStage): number {
  if (stage === "pre_runtime") {
    return options.maxPreRuntimeRepairRounds;
  }
  if (stage === "runtime") {
    return options.maxRuntimeRepairRounds;
  }
  return options.maxSkillEffectRepairRounds;
}

function canRepair(taskState: TaskCycleState, options: ExecuteFamilyOptions, stage: RepairStage): boolean {
  return getRepairRoundsUsed(taskState, stage) < getRepairRoundBudget(options, stage);
}

function incrementRepairRounds(taskState: TaskCycleState, stage: RepairStage): void {
  taskState.repairRoundsUsed += 1;
  if (stage === "pre_runtime") {
    taskState.preRuntimeRepairRoundsUsed += 1;
  } else if (stage === "runtime") {
    taskState.runtimeRepairRoundsUsed += 1;
  } else if (stage === "skill_effect") {
    taskState.skillEffectRepairRoundsUsed += 1;
  }
}

function buildOrdinalRange(count: number): number[] {
  return Array.from({ length: Math.max(0, count) }, (_, index) => index + 1);
}

function resolvePendingOrdinals(unit: {
  taskCount: number;
  pendingTaskOrdinals?: number[];
}): { taskOrdinals: number[] } {
  const taskOrdinals = Array.isArray(unit.pendingTaskOrdinals) ? unit.pendingTaskOrdinals : buildOrdinalRange(unit.taskCount);
  return { taskOrdinals };
}

function buildScopeMetadata(
  unit: GenerationUnit,
  runtimeEnvironment?: RuntimeEnvironment,
): Record<string, unknown> {
  return {
    templateId: unit.template.templateId,
    templateRelativePath: unit.template.templateRelativePath,
    skillMode: unit.skillMode,
    scopeSlug: unit.scopeSlug,
    targetSkillDirName: unit.targetSkill?.dirName,
    targetSkillName: unit.targetSkill?.name,
    inputSkillDirNames: unit.inputSkills.map((skill) => skill.dirName),
    inputSkillNames: unit.inputSkills.map((skill) => skill.name),
    taskCount: unit.taskCount,
    pendingTaskOrdinals: unit.pendingTaskOrdinals,
    finalFamilyDir: unit.finalFamilyDir,
    publishedTaskIds: unit.publishedTasks.map((task) => task.derivedTaskId),
    ...(runtimeEnvironment ? { runtimeEnvironment } : {}),
  };
}

class TaskAttemptTimeoutError extends Error {
  constructor(
    derivedTaskId: string,
    attemptIndex: number,
    stepLabel: string,
  ) {
    super(`${derivedTaskId} attempt-${attemptIndex} 在 ${stepLabel} 阶段超时，已中断当前 attempt`);
    this.name = "TaskAttemptTimeoutError";
  }
}

function buildTaskSlots(unit: GenerationUnit): TaskSlot[] {
  return unit.pendingTaskOrdinals.map((ordinal) => ({
    derivedTaskId: `task${ordinal}`,
    taskOrdinal: ordinal,
  }));
}

function buildSingleTaskUnit(unit: GenerationUnit, slot: TaskSlot): GenerationUnit {
  return {
    ...unit,
    pendingTaskOrdinals: [slot.taskOrdinal],
  };
}

function buildDerivedTaskPlan(
  unit: GenerationUnit,
  slot: TaskSlot,
  plannedTask: SingleTaskPlan,
): DerivedTaskPlan {
  return {
    derivedTaskId: slot.derivedTaskId,
    taskOrdinal: slot.taskOrdinal,
    title: plannedTask.title,
    realWorldContext: plannedTask.realWorldContext,
    referenceData: plannedTask.referenceData,
    taskGoal: plannedTask.taskGoal,
    inputAssets: plannedTask.inputAssets,
    requiredOutputs: plannedTask.requiredOutputs,
    verifierFocus: plannedTask.verifierFocus,
    skillBenefitRationale: plannedTask.skillBenefitRationale,
    difficulty: plannedTask.difficulty,
    category: plannedTask.category,
    templateId: unit.template.templateId,
    skillMode: unit.skillMode,
    targetSkillDirName: unit.targetSkill?.dirName ?? "",
    targetSkillName: unit.targetSkill?.name ?? "",
  };
}

function buildTaskPlanValidationIssues(plan: DerivedTaskPlan, slot: TaskSlot): ValidationIssue[] {
  return validateTaskPlans([plan], {
    taskOrdinals: [slot.taskOrdinal],
  });
}

function removePendingSlot(unit: GenerationUnit, slot: TaskSlot): void {
  unit.pendingTaskOrdinals = unit.pendingTaskOrdinals.filter((ordinal) => ordinal !== slot.taskOrdinal);
}

function buildAttemptDeadlineAt(timeoutHours: number): number | null {
  if (timeoutHours <= 0) {
    return null;
  }
  return Date.now() + timeoutHours * 60 * 60 * 1000;
}

async function withAttemptDeadline<T>(
  taskId: string,
  attemptIndex: number,
  stepLabel: string,
  deadlineAt: number | null,
  run: (signal?: AbortSignal) => Promise<T>,
): Promise<T> {
  if (deadlineAt === null) {
    return run(undefined);
  }

  const remainingMs = deadlineAt - Date.now();
  if (remainingMs <= 0) {
    throw new TaskAttemptTimeoutError(taskId, attemptIndex, stepLabel);
  }

  const signal = AbortSignal.timeout(Math.max(1, Math.ceil(remainingMs)));
  try {
    return await run(signal);
  } catch (error) {
    if (signal.aborted) {
      throw new TaskAttemptTimeoutError(taskId, attemptIndex, stepLabel);
    }
    throw error;
  }
}

function buildPublishedTaskInfo(plan: DerivedTaskPlan, taskDir: string, acceptanceKind: AcceptanceKind): PublishedTaskInfo {
  return {
    derivedTaskId: plan.derivedTaskId,
    taskOrdinal: plan.taskOrdinal,
    acceptanceKind,
    taskDir,
    planPath: path.join(taskDir, "plan.json"),
    instructionPath: path.join(taskDir, "instruction.md"),
    taskTomlPath: path.join(taskDir, "task.toml"),
    testOutputsPath: path.join(taskDir, "tests", "test_outputs.py"),
    environmentDir: path.join(taskDir, "environment"),
  };
}

function upsertPublishedTask(unit: GenerationUnit, publishedTask: PublishedTaskInfo): void {
  const nextPublishedTasks = unit.publishedTasks.filter((task) => task.derivedTaskId !== publishedTask.derivedTaskId);
  nextPublishedTasks.push(publishedTask);
  nextPublishedTasks.sort((left, right) => left.taskOrdinal - right.taskOrdinal);
  unit.publishedTasks = nextPublishedTasks;
}

function buildFailedTaskRef(
  derivedTaskId: string,
  draftDir: string,
  taskState?: TaskCycleState,
): FamilyExecutionResult["failedTaskRefs"][number] {
  return {
    derivedTaskId,
    draftDir,
    latestRuntimeResultPath: taskState?.runtimeEvidence?.resultPath,
    latestSkillEffectResultPath: taskState?.skillEffectResultPath,
    latestSkillEffectPairRoot: taskState?.skillEffectEvaluation?.pairRoot,
  };
}

async function inventory(templateRoot: string): Promise<void> {
  const templates = await discoverTaskTemplates(templateRoot);
  const rows = await Promise.all(
    templates.map(async (template) => ({
      templateId: template.templateId,
      templateRelativePath: template.templateRelativePath,
      difficulty: template.metadata.difficulty ?? null,
      category: template.metadata.category ?? null,
      referenceSkillNames: template.referenceSkills.map((skill) => skill.name),
      environmentAssets: await collectEnvironmentAssetPaths(template),
    })),
  );
  console.log(JSON.stringify(rows, null, 2));
}

async function repairTaskDraft(
  codex: CodexTaskBuilderClient,
  unit: GenerationUnit,
  workspace: TaskAttemptWorkspace,
  taskState: TaskCycleState,
  cycle: number,
  repairStage: RepairStage,
  outputRoot: string,
  signal?: AbortSignal,
): Promise<void> {
  const repairResult = await codex.repairTask({
    unit,
    workspace,
    plan: taskState.plan,
    draftDirLabel: "draft/",
    blockingIssues: issueMessages(taskState.blockingIssues),
    staticIssues: issueMessages(taskState.staticIssues),
    runtimeIssues: issueMessages(taskState.runtimeIssues),
    skillEffectIssues: issueMessages(taskState.skillEffectIssues),
    runtimeDir: taskState.runtimeEvidence?.runtimeDir,
    runtimeLogRoot: taskState.runtimeEvidence?.runtimeLogRoot,
    runtimeLogIndexPath: taskState.runtimeEvidence?.runtimeLogIndexPath,
    runtimeLogPath: taskState.runtimeEvidence?.logFilePath,
    runtimeResultPath: taskState.runtimeEvidence?.resultPath,
    jobLogPath: taskState.runtimeEvidence?.jobLogPath,
    trialLogPath: taskState.runtimeEvidence?.trialLogPath,
    verifierStdoutPath: taskState.runtimeEvidence?.verifierStdoutPath,
    rewardPath: taskState.runtimeEvidence?.rewardPath,
    artifactManifestPath: taskState.runtimeEvidence?.artifactManifestPath,
    skillEffectEvidenceRoot: taskState.skillEffectEvaluation?.pairRoot,
    skillEffectResultPath: taskState.skillEffectResultPath,
    skillEffectBucket: taskState.skillEffectEvaluation?.bucket,
    threadId: taskState.repairThreadId,
    signal,
  });
  taskState.repairThreadId = repairResult.threadId;
  incrementRepairRounds(taskState, repairStage);
  taskState.acceptedWithSkillVariantDir = undefined;
  taskState.acceptedNoSkillVariantDir = undefined;
  taskState.acceptanceKind = undefined;
  taskState.passed = false;
  await writeJson(
    path.join(workspace.artifactsDir, `${taskState.plan.derivedTaskId}.repair.${taskState.repairRoundsUsed}.json`),
    repairResult.data,
  );
  await writeJson(
    path.join(workspace.artifactsDir, `${taskState.plan.derivedTaskId}.repair.${taskState.repairRoundsUsed}.raw.json`),
    {
      threadId: repairResult.threadId,
      raw: repairResult.raw,
    },
  );
  await appendManifest(
    {
      runId: workspace.runId,
      templateId: workspace.templateId,
      derivedTaskId: taskState.plan.derivedTaskId,
      phase: "repair",
      status: "completed",
      threadId: repairResult.threadId,
      draftDir: taskState.draftDir,
      issues: [
        ...issueMessages(taskState.blockingIssues),
        ...issueMessages(taskState.staticIssues),
        ...issueMessages(taskState.runtimeIssues),
        ...issueMessages(taskState.skillEffectIssues),
      ],
      metadata: {
        cycle,
        attemptIndex: taskState.attemptIndex,
        repairStage,
      },
    },
    outputRoot,
  );
}

function buildSkillEffectTracePair(args: {
  unit: GenerationUnit;
  runId: string;
  plan: DerivedTaskPlan;
  attemptIndex: number;
  cycle: number;
  stageAttemptIndex: number;
  evaluation: SkillEffectEvaluationResult;
}): TraceArchivePair {
  return {
    runId: args.runId,
    templateId: args.unit.template.templateId,
    scopeSlug: args.unit.scopeSlug,
    derivedTaskId: args.plan.derivedTaskId,
    attemptIndex: args.attemptIndex,
    cycle: args.cycle,
    stage: "skill-effect",
    stageAttemptIndex: args.stageAttemptIndex,
    pairRoot: args.evaluation.pairRoot,
    bucket: args.evaluation.bucket,
    withSkill: {
      status: args.evaluation.withSkill.comparisonStatus,
      passed: args.evaluation.withSkill.passed,
      reward: args.evaluation.withSkill.evidence.reward ?? null,
      resultPath: args.evaluation.withSkill.evidence.resultPath,
      trajectoryPath: args.evaluation.withSkill.evidence.trajectoryPath,
      variantTaskDir: args.evaluation.withSkill.evidence.variantTaskDir,
      summary: args.evaluation.withSkill.evidence.summary,
    },
    noSkill: {
      status: args.evaluation.noSkill.comparisonStatus,
      passed: args.evaluation.noSkill.passed,
      reward: args.evaluation.noSkill.evidence.reward ?? null,
      resultPath: args.evaluation.noSkill.evidence.resultPath,
      trajectoryPath: args.evaluation.noSkill.evidence.trajectoryPath,
      variantTaskDir: args.evaluation.noSkill.evidence.variantTaskDir,
      summary: args.evaluation.noSkill.evidence.summary,
    },
  };
}

function publishLatestSkillEffectFallback(taskState: TaskCycleState, reason: string): TaskAttemptResult | null {
  const candidate = taskState.latestSkillEffectFallbackCandidate;
  if (!candidate) {
    return null;
  }

  taskState.skillEffectEvaluation = candidate.evaluation;
  taskState.skillEffectIssues = buildSkillEffectIssues(taskState.plan.derivedTaskId, candidate.evaluation);
  taskState.skillEffectResultPath = candidate.resultPath;
  taskState.acceptedWithSkillVariantDir = candidate.withSkillVariantDir;
  taskState.acceptedNoSkillVariantDir = candidate.noSkillVariantDir;
  taskState.acceptanceKind = "oracle_fallback_success";
  taskState.passed = true;

  return {
    status: "published",
    taskState,
    attemptWorkspace: taskState.attemptWorkspace,
    issues: [reason],
  };
}

async function executeTaskAttempt(
  codex: CodexTaskBuilderClient,
  unit: GenerationUnit,
  familyWorkspace: FamilyWorkspace,
  slot: TaskSlot,
  attemptIndex: number,
  options: ExecuteFamilyOptions,
): Promise<TaskAttemptResult> {
  const taskUnit = buildSingleTaskUnit(unit, slot);
  const attemptWorkspace = await createTaskAttemptWorkspace(familyWorkspace, taskUnit, slot, {
    attemptIndex,
  });
  const deadlineAt = buildAttemptDeadlineAt(options.taskAttemptTimeoutHours);
  let taskState: TaskCycleState | undefined;

  await appendManifest(
    {
      runId: familyWorkspace.runId,
      templateId: unit.template.templateId,
      derivedTaskId: slot.derivedTaskId,
      phase: "task-attempt",
      status: "started",
      draftDir: attemptWorkspace.draftDir,
      metadata: {
        ...buildScopeMetadata(taskUnit, options.runtimeEnvironment),
        attemptIndex,
      },
    },
    options.outputRoot,
  );

  try {
    const plannerResult = await withAttemptDeadline(slot.derivedTaskId, attemptIndex, "planner", deadlineAt, (signal) =>
      codex.planTask(taskUnit, attemptWorkspace, slot, { signal }),
    );
    const plan = buildDerivedTaskPlan(taskUnit, slot, plannerResult.data);
    const plannerIssues = buildTaskPlanValidationIssues(plan, slot);

    await writeJson(path.join(attemptWorkspace.artifactsDir, `${slot.derivedTaskId}.planner.json`), plan);
    await writeJson(path.join(attemptWorkspace.artifactsDir, `${slot.derivedTaskId}.planner.raw.json`), {
      threadId: plannerResult.threadId,
      raw: plannerResult.raw,
    });
    await appendManifest(
      {
        runId: familyWorkspace.runId,
        templateId: unit.template.templateId,
        derivedTaskId: slot.derivedTaskId,
        phase: "planner",
        status: plannerIssues.length === 0 ? "completed" : "failed",
        threadId: plannerResult.threadId,
        draftDir: attemptWorkspace.draftDir,
        issues: issueMessages(plannerIssues),
        metadata: {
          ...buildScopeMetadata(taskUnit, options.runtimeEnvironment),
          attemptIndex,
        },
      },
      options.outputRoot,
    );

    if (plannerIssues.length > 0) {
      return {
        status: "exhausted_repairs",
        attemptWorkspace,
        issues: issueMessages(plannerIssues),
      };
    }

    const draftDir = await prepareAttemptDraftSkeleton(attemptWorkspace, plan);
    const writerResult = await withAttemptDeadline(slot.derivedTaskId, attemptIndex, "writer", deadlineAt, (signal) =>
      codex.writeTask(taskUnit, attemptWorkspace, plan, {
        signal,
        draftDirLabel: "draft/",
      }),
    );
    await writeJson(path.join(attemptWorkspace.artifactsDir, `${plan.derivedTaskId}.writer.json`), writerResult.data);
    await writeJson(path.join(attemptWorkspace.artifactsDir, `${plan.derivedTaskId}.writer.raw.json`), {
      threadId: writerResult.threadId,
      raw: writerResult.raw,
    });
    await appendManifest(
      {
        runId: familyWorkspace.runId,
        templateId: unit.template.templateId,
        derivedTaskId: plan.derivedTaskId,
        phase: "writer",
        status: "completed",
        threadId: writerResult.threadId,
        draftDir,
        metadata: {
          ...buildScopeMetadata(taskUnit, options.runtimeEnvironment),
          attemptIndex,
        },
      },
      options.outputRoot,
    );

    taskState = {
      attemptWorkspace,
      attemptIndex,
      plan,
      draftDir,
      writerSummary: writerResult.data,
      repairThreadId: null,
      repairRoundsUsed: 0,
      preRuntimeRepairRoundsUsed: 0,
      runtimeRepairRoundsUsed: 0,
      skillEffectRepairRoundsUsed: 0,
      runtimeAttemptCount: 0,
      skillEffectAttemptCount: 0,
      blockingIssues: [],
      staticIssues: [],
      runtimeIssues: [],
      skillEffectIssues: [],
      acceptedWithSkillVariantDir: undefined,
      acceptedNoSkillVariantDir: undefined,
      acceptanceKind: undefined,
      tracePairs: [],
      passed: false,
    };

    while (true) {
      const currentTaskState = taskState;
      const cycle = currentTaskState.repairRoundsUsed;
      const reviewResult = await withAttemptDeadline(plan.derivedTaskId, attemptIndex, "review", deadlineAt, (signal) =>
        codex.reviewTaskBlocking(taskUnit, attemptWorkspace, plan, {
          signal,
          draftDirLabel: "draft/",
        }),
      );
      const reviewValidation = validateBlockingReviewResult([plan], reviewResult.data);
      await writeJson(
        path.join(attemptWorkspace.artifactsDir, `${plan.derivedTaskId}.review.round-${cycle}.json`),
        reviewResult.data,
      );
      await writeJson(
        path.join(attemptWorkspace.artifactsDir, `${plan.derivedTaskId}.review.round-${cycle}.raw.json`),
        {
          threadId: reviewResult.threadId,
          raw: reviewResult.raw,
        },
      );

      currentTaskState.blockingIssues = reviewValidation.taskIssuesById.get(plan.derivedTaskId) ?? [];
      currentTaskState.staticIssues = await validateDraftStatic(currentTaskState.draftDir, plan, taskUnit);
      currentTaskState.runtimeIssues = [];
      currentTaskState.skillEffectIssues = [];
      currentTaskState.runtimeEvidence = undefined;
      currentTaskState.skillEffectEvaluation = undefined;
      currentTaskState.skillEffectResultPath = undefined;
      currentTaskState.acceptedWithSkillVariantDir = undefined;
      currentTaskState.acceptedNoSkillVariantDir = undefined;
      currentTaskState.acceptanceKind = undefined;
      currentTaskState.passed = false;

      const preRuntimeIssues = [...taskState.blockingIssues, ...taskState.staticIssues];
      await appendManifest(
        {
          runId: familyWorkspace.runId,
          templateId: unit.template.templateId,
          derivedTaskId: plan.derivedTaskId,
          phase: "validate",
          status: preRuntimeIssues.length === 0 ? "completed" : "failed",
          draftDir: currentTaskState.draftDir,
          issues: issueMessages(preRuntimeIssues),
          metadata: {
            ...buildScopeMetadata(taskUnit, options.runtimeEnvironment),
            attemptIndex,
            cycle,
          },
        },
        options.outputRoot,
      );

      if (preRuntimeIssues.length > 0) {
        if (canRepair(taskState, options, "pre_runtime")) {
          await withAttemptDeadline(plan.derivedTaskId, attemptIndex, "repair", deadlineAt, (signal) =>
            repairTaskDraft(codex, taskUnit, attemptWorkspace, currentTaskState, cycle, "pre_runtime", options.outputRoot, signal),
          );
          continue;
        }
        const fallbackResult = publishLatestSkillEffectFallback(
          taskState,
          `${plan.derivedTaskId} pre-runtime 修复预算耗尽，已保留最近一次完整 skill-effect 对照结果`,
        );
        if (fallbackResult) {
          return fallbackResult;
        }
        return {
          status: "exhausted_repairs",
          taskState,
          attemptWorkspace,
          issues: issueMessages(preRuntimeIssues),
        };
      }

      const runtimeAttemptIndex = taskState.runtimeAttemptCount + 1;
      const runtimeResult = await withAttemptDeadline(
        plan.derivedTaskId,
        attemptIndex,
        "runtime",
        deadlineAt,
        (signal) =>
          runRuntimeValidation(
            attemptWorkspace,
            plan,
            options.runtimeEnvironment,
            cycle,
            runtimeAttemptIndex,
            currentTaskState.draftDir,
            process.env,
            signal,
          ),
      );
      taskState.runtimeAttemptCount = runtimeAttemptIndex;
      taskState.runtimeIssues = runtimeResult.issues;
      taskState.runtimeEvidence = runtimeResult.evidence;
      await writeJson(
        path.join(attemptWorkspace.artifactsDir, `${plan.derivedTaskId}.runtime.cycle-${cycle}.attempt-${runtimeAttemptIndex}.json`),
        {
          passed: runtimeResult.passed,
          failureKind: runtimeResult.failureKind,
          issues: issueMessages(runtimeResult.issues),
          evidence: runtimeResult.evidence,
        },
      );
      await writeJson(path.join(attemptWorkspace.artifactsDir, `${plan.derivedTaskId}.runtime.cycle-${cycle}.json`), {
        passed: runtimeResult.passed,
        failureKind: runtimeResult.failureKind,
        issues: issueMessages(runtimeResult.issues),
        evidence: runtimeResult.evidence,
      });

      if (!runtimeResult.passed) {
        await appendManifest(
          {
            runId: familyWorkspace.runId,
            templateId: unit.template.templateId,
            derivedTaskId: plan.derivedTaskId,
            phase: "validate",
            status: "failed",
            draftDir: taskState.draftDir,
            issues: issueMessages(runtimeResult.issues),
            metadata: {
              ...buildScopeMetadata(taskUnit, options.runtimeEnvironment),
              attemptIndex,
              cycle,
              runtimeAttempt: runtimeAttemptIndex,
              runtimeFailureKind: runtimeResult.failureKind,
            },
          },
          options.outputRoot,
        );

        if (canRepair(taskState, options, "runtime")) {
          await withAttemptDeadline(plan.derivedTaskId, attemptIndex, "repair", deadlineAt, (signal) =>
            repairTaskDraft(codex, taskUnit, attemptWorkspace, currentTaskState, cycle, "runtime", options.outputRoot, signal),
          );
          continue;
        }
        const fallbackResult = publishLatestSkillEffectFallback(
          taskState,
          `${plan.derivedTaskId} runtime 修复预算耗尽，已保留最近一次完整 skill-effect 对照结果`,
        );
        if (fallbackResult) {
          return fallbackResult;
        }
        return {
          status: "exhausted_repairs",
          taskState,
          attemptWorkspace,
          issues: issueMessages(runtimeResult.issues),
        };
      }

      if (options.skillEffectEnabled) {
        const skillEffectAttemptIndex = taskState.skillEffectAttemptCount + 1;
        const skillEffectResult = await withAttemptDeadline(
          plan.derivedTaskId,
          attemptIndex,
          "skill-effect",
          deadlineAt,
          (signal) =>
            runSkillEffectEvaluation({
              workspace: attemptWorkspace,
              plan,
              runtimeEnvironment: options.runtimeEnvironment,
              cycle,
              attemptIndex: skillEffectAttemptIndex,
              draftTaskDir: currentTaskState.draftDir,
              modelName: options.skillEffectModel,
              apiKey: options.skillEffectApiKey,
              baseUrl: options.skillEffectBaseUrl,
              signal,
            }),
        );
        taskState.skillEffectAttemptCount = skillEffectAttemptIndex;
        taskState.skillEffectEvaluation = skillEffectResult;
        taskState.skillEffectIssues = buildSkillEffectIssues(plan.derivedTaskId, skillEffectResult);
        taskState.tracePairs.push(
          buildSkillEffectTracePair({
            unit,
            runId: familyWorkspace.runId,
            plan,
            attemptIndex,
            cycle,
            stageAttemptIndex: skillEffectAttemptIndex,
            evaluation: skillEffectResult,
          }),
        );
        taskState.acceptedWithSkillVariantDir = skillEffectResult.repairRequired
          ? undefined
          : skillEffectResult.withSkill.evidence.variantTaskDir;
        taskState.acceptedNoSkillVariantDir = skillEffectResult.repairRequired
          ? undefined
          : skillEffectResult.noSkill.evidence.variantTaskDir;
        taskState.skillEffectResultPath = await writeSkillEffectResultArtifact({
          artifactsDir: attemptWorkspace.artifactsDir,
          derivedTaskId: plan.derivedTaskId,
          cycle,
          attemptIndex: skillEffectAttemptIndex,
          result: skillEffectResult,
        });
        taskState.latestSkillEffectFallbackCandidate = {
          cycle,
          stageAttemptIndex: skillEffectAttemptIndex,
          evaluation: skillEffectResult,
          resultPath: taskState.skillEffectResultPath,
          withSkillVariantDir: skillEffectResult.withSkill.evidence.variantTaskDir,
          noSkillVariantDir: skillEffectResult.noSkill.evidence.variantTaskDir,
        };
        await appendManifest(
          {
            runId: familyWorkspace.runId,
            templateId: unit.template.templateId,
            derivedTaskId: plan.derivedTaskId,
            phase: "skill-effect",
            status: skillEffectResult.repairRequired ? "failed" : "completed",
            draftDir: taskState.draftDir,
            issues: issueMessages(taskState.skillEffectIssues),
            metadata: {
              ...buildScopeMetadata(taskUnit, options.runtimeEnvironment),
              attemptIndex,
              cycle,
              skillEffectAttempt: skillEffectAttemptIndex,
              skillEffectBucket: skillEffectResult.bucket,
            },
          },
          options.outputRoot,
        );

        if (!skillEffectResult.repairRequired) {
          taskState.acceptanceKind = "pf_success";
          taskState.passed = true;
          return {
            status: "published",
            taskState,
            attemptWorkspace,
            issues: [],
          };
        }

        if (canRepair(taskState, options, "skill_effect")) {
          await withAttemptDeadline(plan.derivedTaskId, attemptIndex, "repair", deadlineAt, (signal) =>
            repairTaskDraft(codex, taskUnit, attemptWorkspace, currentTaskState, cycle, "skill_effect", options.outputRoot, signal),
          );
          continue;
        }

        const fallbackResult = publishLatestSkillEffectFallback(
          taskState,
          `${plan.derivedTaskId} 未达到 PF，已保留最近一次完整 skill-effect 对照结果`,
        );
        if (fallbackResult) {
          return fallbackResult;
        }
      }

      return {
        status: "exhausted_repairs",
        taskState,
        attemptWorkspace,
        issues: options.skillEffectEnabled
          ? [`${plan.derivedTaskId} 没有可发布的完整 skill-effect 对照结果`]
          : [`${plan.derivedTaskId} 已跳过 skill-effect gate，无法产生 fallback 对照候选`],
      };
    }

    return {
      status: "exhausted_repairs",
      taskState,
      attemptWorkspace,
      issues: [`${slot.derivedTaskId} attempt-${attemptIndex} 在未通过的情况下耗尽了分阶段 repair 预算`],
    };
  } catch (error) {
    if (error instanceof TaskAttemptTimeoutError) {
      if (taskState) {
        const fallbackResult = publishLatestSkillEffectFallback(taskState, error.message);
        if (fallbackResult) {
          return fallbackResult;
        }
      }
      return {
        status: "timed_out",
        taskState,
        attemptWorkspace,
        issues: [error.message],
      };
    }
    throw error;
  }
}

async function executeFamilyGeneration(
  unit: GenerationUnit,
  options: ExecuteFamilyOptions,
): Promise<FamilyExecutionResult> {
  const workspace = await createFamilyWorkspace(unit, {
    rawRoot: options.rawRoot,
  });
  const codex = new CodexTaskBuilderClient({
    codexRunRetries: options.codexRunRetries,
  });
  const appendRunManifest = (entry: Omit<ManifestEntry, "timestamp">) => appendManifest(entry, options.outputRoot);
  const writeWorkspaceSummary = (summary: unknown) => writeRunSummary(workspace.runId, summary, options.outputRoot);
  const publishedTaskIds: string[] = [];
  const failedTaskIds: string[] = [];
  const publishedVariantDirs: FamilyExecutionResult["publishedVariantDirs"] = [];
  const failedTaskRefs: FamilyExecutionResult["failedTaskRefs"] = [];
  const finalIssues: string[] = [];
  const skillEffectResults: FamilyExecutionResult["skillEffectResults"] = [];
  const skillEffectBucketCounts: Partial<Record<SkillEffectBucket, number>> = {};

  await appendRunManifest({
    runId: workspace.runId,
    templateId: unit.template.templateId,
    phase: "workspace",
    status: "completed",
    metadata: { rootDir: workspace.rootDir, ...buildScopeMetadata(unit, options.runtimeEnvironment) },
  });

  try {
    const slots = buildTaskSlots(unit);

    for (const slot of slots) {
      let finalAttemptState: TaskCycleState | undefined;
      let finalAttemptWorkspace: TaskAttemptWorkspace | undefined;
      let finalAttemptIssues: string[] = [];
      const taskTracePairs: TraceArchivePair[] = [];

      for (let attemptIndex = 1; attemptIndex <= options.maxTaskRestarts + 1; attemptIndex += 1) {
        const attemptResult = await executeTaskAttempt(codex, unit, workspace, slot, attemptIndex, options);
        finalAttemptState = attemptResult.taskState;
        finalAttemptWorkspace = attemptResult.attemptWorkspace;
        finalAttemptIssues = attemptResult.issues;
        if (attemptResult.taskState) {
          taskTracePairs.push(...attemptResult.taskState.tracePairs);
        }

        await appendRunManifest({
          runId: workspace.runId,
          templateId: unit.template.templateId,
          derivedTaskId: slot.derivedTaskId,
          phase: "task-attempt",
          status: attemptResult.status === "published" ? "completed" : "failed",
          draftDir: attemptResult.taskState?.draftDir ?? attemptResult.attemptWorkspace.draftDir,
          issues: attemptResult.issues,
          metadata: {
            ...buildScopeMetadata(buildSingleTaskUnit(unit, slot), options.runtimeEnvironment),
            attemptIndex,
            attemptStatus: attemptResult.status,
          },
        });

        if (attemptResult.status === "published") {
          const taskState = attemptResult.taskState;
          const plan = taskState.plan;
          if (!taskState.acceptanceKind) {
            throw new Error(`${plan.derivedTaskId} published attempt 缺少 acceptanceKind`);
          }
          if (!taskState.acceptedNoSkillVariantDir) {
            throw new Error(`${plan.derivedTaskId} published attempt 缺少 no_skill 变体`);
          }
          const acceptanceKind = taskState.acceptanceKind;
          const acceptanceFinalRoot = buildAcceptanceFinalRoot(options.finalRoot, acceptanceKind);
          const withSkillSourceDir = taskState.acceptedWithSkillVariantDir ?? taskState.draftDir;
          const withSkillTargetDir = buildPublishedVariantTaskDir({
            targetRoot: acceptanceFinalRoot,
            templateId: unit.template.templateId,
            scopeSlug: unit.scopeSlug,
            taskName: plan.derivedTaskId,
            variant: "with_skill",
          });
          const withSkillResult = await sanitizeAndCopyTask({
            sourceDraftDir: withSkillSourceDir,
            templateId: unit.template.templateId,
            scopeSlug: unit.scopeSlug,
            taskName: `${plan.derivedTaskId}__with_skill`,
            rawRoot: options.rawRoot,
            targetRoot: acceptanceFinalRoot,
          });
          const noSkillTargetDir = buildPublishedVariantTaskDir({
            targetRoot: acceptanceFinalRoot,
            templateId: unit.template.templateId,
            scopeSlug: unit.scopeSlug,
            taskName: plan.derivedTaskId,
            variant: "no_skill",
          });
          await sanitizeAndCopyTask({
            sourceDraftDir: taskState.acceptedNoSkillVariantDir,
            templateId: unit.template.templateId,
            scopeSlug: unit.scopeSlug,
            taskName: `${plan.derivedTaskId}__no_skill`,
            rawRoot: options.rawRoot,
            targetRoot: acceptanceFinalRoot,
          });
          publishedTaskIds.push(plan.derivedTaskId);
          publishedVariantDirs.push({
            derivedTaskId: plan.derivedTaskId,
            acceptanceKind,
            withSkillDir: withSkillTargetDir,
            noSkillDir: noSkillTargetDir,
          });
          upsertPublishedTask(unit, buildPublishedTaskInfo(plan, withSkillResult.targetTaskDir, acceptanceKind));
          removePendingSlot(unit, slot);
          await appendRunManifest({
            runId: workspace.runId,
            templateId: unit.template.templateId,
            derivedTaskId: plan.derivedTaskId,
            phase: "publish",
            status: "completed",
            draftDir: taskState.draftDir,
            publishedDir: withSkillResult.targetTaskDir,
            metadata: {
              ...buildScopeMetadata(buildSingleTaskUnit(unit, slot), options.runtimeEnvironment),
              attemptIndex: taskState.attemptIndex,
              acceptanceKind,
              ...(acceptanceKind === "oracle_fallback_success"
                ? {
                    fallbackSource: "latest_completed_skill_effect",
                    skillEffectBucket: taskState.skillEffectEvaluation?.bucket,
                    skillEffectPairRoot: taskState.skillEffectEvaluation?.pairRoot,
                    skillEffectResultPath: taskState.skillEffectResultPath,
                    skillEffectFallbackCycle: taskState.latestSkillEffectFallbackCandidate?.cycle,
                    skillEffectFallbackAttempt: taskState.latestSkillEffectFallbackCandidate?.stageAttemptIndex,
                  }
                : {}),
              publishDisposition: withSkillResult.disposition,
              publishedNoSkillDir: noSkillTargetDir,
              withSkillVariantSourceDir: withSkillSourceDir,
              noSkillVariantSourceDir: taskState.acceptedNoSkillVariantDir,
            },
          });
          await archiveTracePairs({
            outputRoot: options.outputRoot,
            outcome: acceptanceKind,
            pairs: taskTracePairs,
          });
          break;
        }

        if (attemptIndex <= options.maxTaskRestarts) {
          continue;
        }

        failedTaskIds.push(slot.derivedTaskId);
        failedTaskRefs.push(
          buildFailedTaskRef(
            slot.derivedTaskId,
            finalAttemptState?.draftDir ?? finalAttemptWorkspace?.draftDir ?? workspace.rootDir,
            finalAttemptState,
          ),
        );
        await archiveTracePairs({
          outputRoot: options.outputRoot,
          outcome: "failed",
          pairs: taskTracePairs,
        });
        finalIssues.push(...finalAttemptIssues);
        await appendRunManifest({
          runId: workspace.runId,
          templateId: unit.template.templateId,
          derivedTaskId: slot.derivedTaskId,
          phase: "publish",
          status: "failed",
          draftDir: finalAttemptState?.draftDir ?? finalAttemptWorkspace?.draftDir,
          issues: finalAttemptIssues,
          metadata: {
            ...buildScopeMetadata(buildSingleTaskUnit(unit, slot), options.runtimeEnvironment),
            attemptIndex,
            latestRuntimeResultPath: finalAttemptState?.runtimeEvidence?.resultPath,
            latestSkillEffectResultPath: finalAttemptState?.skillEffectResultPath,
            latestSkillEffectPairRoot: finalAttemptState?.skillEffectEvaluation?.pairRoot,
          },
        });
      }

      if (finalAttemptState?.skillEffectEvaluation) {
        const evaluation = finalAttemptState.skillEffectEvaluation;
        skillEffectResults.push({
          derivedTaskId: finalAttemptState.plan.derivedTaskId,
          bucket: evaluation.bucket,
          repairRequired: evaluation.repairRequired,
          withSkillPassed: evaluation.withSkill.passed,
          withSkillReward: evaluation.withSkill.evidence.reward ?? null,
          withSkillSummary: evaluation.withSkill.evidence.summary,
          noSkillPassed: evaluation.noSkill.passed,
          noSkillReward: evaluation.noSkill.evidence.reward ?? null,
          noSkillSummary: evaluation.noSkill.evidence.summary,
          noSkillComparisonStatus: evaluation.noSkill.comparisonStatus,
          noSkillComparisonReason: evaluation.noSkill.comparisonReason,
          withSkillVariantDir: evaluation.withSkill.evidence.variantTaskDir,
          noSkillVariantDir: evaluation.noSkill.evidence.variantTaskDir,
        });
        recordSkillEffectBucketCount(skillEffectBucketCounts, evaluation.bucket);
      }
    }

    const status: FamilyExecutionResult["status"] = failedTaskIds.length === 0 ? "completed" : "failed";
    const summary = {
      templateId: unit.template.templateId,
      templateRelativePath: unit.template.templateRelativePath,
      skillMode: unit.skillMode,
      scopeSlug: unit.scopeSlug,
      targetSkillDirName: unit.targetSkill?.dirName,
      targetSkillName: unit.targetSkill?.name,
      runtimeEnvironment: options.runtimeEnvironment,
      status,
      issues: uniqueStrings(finalIssues),
      publishedTaskIds,
      failedTaskIds,
      publishedVariantDirs,
      failedTaskRefs,
      skillEffectResults,
      skillEffectBucketCounts,
      outputRoot: options.outputRoot,
      workspace,
    };
    await writeWorkspaceSummary(summary);

    return {
      templateId: unit.template.templateId,
      skillMode: unit.skillMode,
      scopeSlug: unit.scopeSlug,
      targetSkillDirName: unit.targetSkill?.dirName,
      targetSkillName: unit.targetSkill?.name,
      runtimeEnvironment: options.runtimeEnvironment,
      runId: workspace.runId,
      status,
      issues: summary.issues,
      publishedTaskIds,
      failedTaskIds,
      publishedVariantDirs,
      failedTaskRefs,
      skillEffectResults,
      skillEffectBucketCounts,
      workspace,
    };
  } catch (error) {
    const message = error instanceof Error ? error.stack ?? error.message : String(error);
    await appendRunManifest({
      runId: workspace.runId,
      templateId: unit.template.templateId,
      phase: "family",
      status: "failed",
      issues: [message],
      metadata: buildScopeMetadata(unit, options.runtimeEnvironment),
    });
    await writeWorkspaceSummary({
      templateId: unit.template.templateId,
      status: "failed",
      issues: uniqueStrings([...finalIssues, message]),
      publishedTaskIds,
      failedTaskIds,
      publishedVariantDirs,
      failedTaskRefs,
      skillEffectResults,
      skillEffectBucketCounts,
      outputRoot: options.outputRoot,
      workspace,
    });
    return {
      templateId: unit.template.templateId,
      skillMode: unit.skillMode,
      scopeSlug: unit.scopeSlug,
      targetSkillDirName: unit.targetSkill?.dirName,
      targetSkillName: unit.targetSkill?.name,
      runtimeEnvironment: options.runtimeEnvironment,
      runId: workspace.runId,
      status: "failed",
      issues: uniqueStrings([...finalIssues, message]),
      publishedTaskIds,
      failedTaskIds,
      publishedVariantDirs,
      failedTaskRefs,
      skillEffectResults,
      skillEffectBucketCounts,
      workspace,
    };
  }
}

async function runPool<T, R>(items: T[], concurrency: number, worker: (item: T, index: number) => Promise<R>): Promise<R[]> {
  const results: R[] = new Array(items.length);
  let nextIndex = 0;

  async function loop(): Promise<void> {
    while (true) {
      const index = nextIndex;
      nextIndex += 1;
      if (index >= items.length) {
        return;
      }
      results[index] = await worker(items[index] as T, index);
    }
  }

  await Promise.all(Array.from({ length: Math.max(1, concurrency) }, () => loop()));
  return results;
}

function assertNoLegacyOptions(options: Options): void {
  if (options["similar-count"] !== undefined || options["transfer-count"] !== undefined) {
    throw new Error("similar-count 和 transfer-count 已移除，请改用 --task-count");
  }
  if (options["max-repair-rounds"] !== undefined) {
    throw new Error(
      "max-repair-rounds 已拆分，请改用 --max-pre-runtime-repair-rounds、--max-runtime-repair-rounds、--max-skill-effect-repair-rounds；--max-oracle-fallback-repair-rounds 已废弃且当前为 no-op",
    );
  }

  const legacyKeys = [
    "source-root",
    "source-task-id",
    "target-skill-dir",
    "raw-root",
    "final-root",
    "quarantine-root",
    "runs-root",
  ].filter((key) => key in options);
  if (legacyKeys.length > 0) {
    throw new Error(`检测到旧参数 ${legacyKeys.map((key) => `--${key}`).join(", ")}；当前版本只支持 template + skill-dir + output-root 模式`);
  }
}

async function loadUnitsForCommand(
  options: Options,
  finalRoot: string,
): Promise<{
  units: GenerationUnit[];
  discoveredUnitCount: number;
  skippedCount: number;
}> {
  const templateRoot = getStringOption(options, "template-root", TEMPLATE_ROOT)!;
  const templateRelativePath = getStringOption(options, "template");
  if (!templateRelativePath) {
    throw new Error("generate-family 命令需要 --template <relative-path>");
  }

  const skillDirs = getStringArrayOption(options, "skill-dir");
  if (skillDirs.length === 0) {
    throw new Error("generate-family 命令至少需要一个 --skill-dir <path>");
  }

  const skillMode = getSkillModeOption(options);
  const taskCount = getNumberOption(options, "task-count", 4);
  if (taskCount < 0) {
    throw new Error("task-count 不能小于 0");
  }
  if (taskCount === 0) {
    throw new Error("task-count 不能为 0");
  }

  const template = await discoverTaskTemplate(templateRelativePath, templateRoot);
  const inputSkills = await discoverInputSkills(skillDirs);
  let units = buildGenerationUnits(template, inputSkills, {
    skillMode,
    taskCount,
  });

  const scopeSlug = getStringOption(options, "scope-slug");
  if (scopeSlug) {
    units = units.filter((unit) => unit.scopeSlug === scopeSlug);
  }

  const hydratedUnits = await Promise.all(
    units.map(async (unit) => {
      const publishedState = await inspectPublishedFamily(unit, finalRoot);
      return applyPublishedFamilyState(unit, publishedState);
    }),
  );
  const limit = getNumberOption(options, "limit", 0);
  const selected = selectExecutableUnits(hydratedUnits, limit);
  return {
    units: selected.executableUnits,
    discoveredUnitCount: hydratedUnits.length,
    skippedCount: selected.skippedCount,
  };
}

async function ensureRoots(options: ExecuteFamilyOptions): Promise<void> {
  await ensureDir(options.outputRoot);
  await ensureDir(options.rawRoot);
  await ensureDir(options.finalRoot);
  await ensureDir(buildAcceptanceFinalRoot(options.finalRoot, "pf_success"));
  await ensureDir(buildAcceptanceFinalRoot(options.finalRoot, "oracle_fallback_success"));
  await ensureDir(path.join(options.outputRoot, "trace_archive"));
}

async function main(): Promise<void> {
  const { command, options } = parseArgs(process.argv.slice(2));

  if (command === "inventory") {
    assertNoLegacyOptions(options);
    await inventory(getStringOption(options, "template-root", TEMPLATE_ROOT)!);
    return;
  }

  if (command === "batch") {
    throw new Error("batch 已移除；当前版本只支持显式的 template + --skill-dir 输入。后续如需批处理，请通过配置文件模式支持。");
  }

  if (command === "review") {
    throw new Error("review 已移除；当前版本聚焦从 template + skills 直接生成任务，不再保留旧 workspace reviewer 重跑入口。");
  }

  if (command !== "generate-family") {
    throw new Error(`不支持的命令: ${command ?? "(missing)"}`);
  }

  assertNoLegacyOptions(options);
  const runtimeEnvironment = resolveRuntimeEnvironment();
  const skillEffectEnabled = !getFlagOption(options, "skip-skill-effect-gate");
  const skillEffectModel = getStringOption(options, "skill-effect-model", "openai/gpt-5.4")!;
  const outputRoot = getStringOption(options, "output-root", DEFAULT_OUTPUT_ROOT)!;
  getNonNegativeIntegerOption(options, "max-oracle-fallback-repair-rounds", 2);
  const executeOptions: ExecuteFamilyOptions = {
    outputRoot,
    rawRoot: buildRawRoot(outputRoot),
    finalRoot: buildFinalRoot(outputRoot),
    runtimeEnvironment,
    maxPreRuntimeRepairRounds: getNonNegativeIntegerOption(options, "max-pre-runtime-repair-rounds", 12),
    maxRuntimeRepairRounds: getNonNegativeIntegerOption(options, "max-runtime-repair-rounds", 5),
    maxSkillEffectRepairRounds: getNonNegativeIntegerOption(options, "max-skill-effect-repair-rounds", 6),
    codexRunRetries: getNonNegativeIntegerOption(options, "codex-run-retries", 3),
    taskAttemptTimeoutHours: parseNonNegativeNumber(
      getStringOption(options, "task-attempt-timeout-hours"),
      "--task-attempt-timeout-hours",
      2,
    ),
    maxTaskRestarts: getNonNegativeIntegerOption(options, "max-task-restarts", 1),
    skillEffectEnabled,
    skillEffectModel,
    skillEffectApiKey: process.env.OPENAI_API_KEY?.trim() ?? "",
    skillEffectBaseUrl: process.env.OPENAI_BASE_URL?.trim() || undefined,
  };
  await ensureRoots(executeOptions);

  const preflight = await runRuntimePreflight(runtimeEnvironment);
  if (!preflight.ok) {
    throw new Error(preflight.summary);
  }

  if (executeOptions.skillEffectEnabled) {
    const skillEffectPreflight = await runSkillEffectPreflight(runtimeEnvironment);
    if (!skillEffectPreflight.ok) {
      throw new Error(skillEffectPreflight.summary);
    }
  }

  const loaded = await loadUnitsForCommand(options, executeOptions.finalRoot);
  const units = loaded.units;
  if (units.length === 0) {
    console.log(
      JSON.stringify(
        {
          status: "empty",
          units: 0,
          discoveredUnitCount: loaded.discoveredUnitCount,
          skippedCount: loaded.skippedCount,
          outputRoot: executeOptions.outputRoot,
          rawRoot: executeOptions.rawRoot,
          finalRoot: executeOptions.finalRoot,
        },
        null,
        2,
      ),
    );
    return;
  }

  const concurrency = getNumberOption(options, "concurrency", 1);
  const results = await runPool(units, concurrency, async (unit, index) => {
    console.log(
      `[${index + 1}/${units.length}] 开始 ${unit.template.templateId}/${unit.scopeSlug} pending-task=${unit.pendingTaskOrdinals.length}/${unit.taskCount}`,
    );
    const result = await executeFamilyGeneration(unit, executeOptions);
    console.log(`[${index + 1}/${units.length}] 完成 ${unit.template.templateId}/${unit.scopeSlug} status=${result.status}`);
    return result;
  });

  const skillEffectBucketCounts: Partial<Record<SkillEffectBucket, number>> = {};
  for (const result of results) {
    for (const [bucket, count] of Object.entries(result.skillEffectBucketCounts)) {
      const typedBucket = bucket as SkillEffectBucket;
      skillEffectBucketCounts[typedBucket] = (skillEffectBucketCounts[typedBucket] ?? 0) + (count ?? 0);
    }
  }

  const summary = {
    runtimeEnvironment,
    unitCount: results.length,
    discoveredUnitCount: loaded.discoveredUnitCount,
    successCount: results.filter((result) => result.status === "completed").length,
    failedCount: results.filter((result) => result.status === "failed").length,
    skippedCount: loaded.skippedCount,
    publishedTaskCount: results.reduce((sum, result) => sum + result.publishedTaskIds.length, 0),
    failedTaskCount: results.reduce((sum, result) => sum + result.failedTaskIds.length, 0),
    skillEffectEnabled: executeOptions.skillEffectEnabled,
    skillEffectModel: executeOptions.skillEffectModel,
    skillEffectBucketCounts,
    outputRoot: executeOptions.outputRoot,
    rawRoot: executeOptions.rawRoot,
    finalRoot: executeOptions.finalRoot,
    results,
  };
  console.log(JSON.stringify(summary, null, 2));
}

void main().catch((error) => {
  const message = error instanceof Error ? error.stack ?? error.message : String(error);
  console.error(message);
  process.exitCode = 1;
});
