import path from "node:path";
import { promises as fs } from "node:fs";
import { extractHarborTrialMetrics, type HarborTrialMetrics } from "./harbor_metrics.js";
import type { DerivedTaskPlan } from "./schema.js";
import type { RuntimeEnvironment, RuntimeFailureKind, RuntimePreflightResult, ValidationIssue } from "./validate.js";
import { runRuntimePreflight } from "./validate.js";
import {
  copyDir,
  copyFile,
  ensureDir,
  pathExists,
  readText,
  runCommand,
  runStreamingCommand,
  slugify,
  writeJson,
  writeText,
} from "./utils.js";

export type SkillEffectBucket =
  | "with_skill_pass__no_skill_fail"
  | "with_skill_pass__no_skill_invalid_fail"
  | "with_skill_fail__no_skill_fail"
  | "with_skill_pass__no_skill_pass"
  | "with_skill_fail__no_skill_pass";

export type SkillEffectVariant = "with_skill" | "no_skill";
export type AgentComparisonStatus = "pass" | "valid_reward_fail" | "invalid_fail";

export type AgentRunEvidence = {
  variant: SkillEffectVariant;
  variantTaskDir: string;
  logsDir: string;
  runtimeLogRoot: string;
  runtimeLogIndexPath?: string;
  logFilePath: string;
  jobDir: string;
  jobLogPath?: string;
  trialDir?: string;
  trialLogPath?: string;
  resultPath?: string;
  verifierStdoutPath?: string;
  rewardPath?: string;
  artifactManifestPath?: string;
  trajectoryPath?: string;
  metrics?: HarborTrialMetrics;
  command: string[];
  reward?: number | null;
  summary: string;
};

export type AgentRunResult = {
  variant: SkillEffectVariant;
  passed: boolean;
  comparisonStatus: AgentComparisonStatus;
  comparisonReason: string;
  issues: string[];
  failureKind?: RuntimeFailureKind;
  evidence: AgentRunEvidence;
};

export type SkillEffectEvaluationResult = {
  bucket: SkillEffectBucket;
  repairRequired: boolean;
  pairRoot: string;
  withSkill: AgentRunResult;
  noSkill: AgentRunResult;
};

type CommandRunner = typeof runCommand;

type RuntimeLogEntry = {
  label: string;
  path: string;
};

type SkillEffectWorkspace = {
  runId: string;
  rootDir: string;
  artifactsDir: string;
};

type SkillEffectDeps = {
  prepareWithSkillVariant: typeof prepareWithSkillVariant;
  prepareNoSkillVariant: typeof prepareNoSkillVariant;
  runAgentVariant: typeof runAgentVariant;
};

const DEFAULT_SKILL_EFFECT_DEPS: SkillEffectDeps = {
  prepareWithSkillVariant,
  prepareNoSkillVariant,
  runAgentVariant,
};

const SKILL_COPY_RE = /^\s*COPY(?:\s+--[A-Za-z0-9_-]+(?:=[^\s]+)?)*\s+(?:\.\/*)?skills\/?\s+/i;

function compactOutputSummary(text: string): string {
  const lines = text
    .split("\n")
    .map((line) => line.trim())
    .filter((line) => line.length > 0);
  if (lines.length === 0) {
    return "未提供错误输出";
  }
  return lines.slice(0, 4).join(" | ").slice(0, 500);
}

function shellEscape(value: string): string {
  return `'${value.replace(/'/g, `'\"'\"'`)}'`;
}

function readEnvValue(env: NodeJS.ProcessEnv, key: string): string | null {
  const raw = env[key];
  if (typeof raw !== "string") {
    return null;
  }

  const trimmed = raw.trim();
  return trimmed.length > 0 ? trimmed : null;
}

function parseFiniteNumber(value: unknown): number | null {
  if (typeof value === "number" && Number.isFinite(value)) {
    return value;
  }
  if (typeof value === "string") {
    const parsed = Number(value);
    return Number.isFinite(parsed) ? parsed : null;
  }
  return null;
}

function extractPrimaryReward(rewards: unknown): number | null {
  if (!rewards || typeof rewards !== "object") {
    return null;
  }
  const record = rewards as Record<string, unknown>;
  if ("reward" in record) {
    return parseFiniteNumber(record.reward);
  }

  const numericValues: number[] = [];
  for (const value of Object.values(record)) {
    const parsed = parseFiniteNumber(value);
    if (parsed !== null) {
      numericValues.push(parsed);
    }
  }

  return numericValues.length === 1 ? numericValues[0] ?? null : null;
}

async function existingRuntimeLogEntries(entries: RuntimeLogEntry[]): Promise<RuntimeLogEntry[]> {
  const existing: RuntimeLogEntry[] = [];
  for (const entry of entries) {
    if (await pathExists(entry.path)) {
      existing.push(entry);
    }
  }
  return existing;
}

async function writeRuntimeLogIndex(logIndexPath: string, entries: RuntimeLogEntry[]): Promise<void> {
  await writeJson(logIndexPath, {
    entries: await existingRuntimeLogEntries(entries),
  });
}

async function findLatestTrialResultPath(jobDir: string): Promise<string | null> {
  if (!(await pathExists(jobDir))) {
    return null;
  }

  const entries = await fs.readdir(jobDir, { withFileTypes: true });
  const candidates: Array<{ path: string; mtimeMs: number }> = [];

  for (const entry of entries) {
    if (!entry.isDirectory()) {
      continue;
    }
    const resultPath = path.join(jobDir, entry.name, "result.json");
    if (!(await pathExists(resultPath))) {
      continue;
    }
    const stat = await fs.stat(resultPath);
    candidates.push({ path: resultPath, mtimeMs: stat.mtimeMs });
  }

  candidates.sort((left, right) => right.mtimeMs - left.mtimeMs);
  return candidates[0]?.path ?? null;
}

export function buildHarborAgentCommand(options: {
  taskDir: string;
  logsDir: string;
  jobName: string;
  runtimeEnvironment: RuntimeEnvironment;
  apiKey: string;
  modelName: string;
  baseUrl?: string;
}): string[] {
  const command = [
    "harbor",
    "run",
    "-p",
    options.taskDir,
    "-a",
    "codex",
    "-m",
    options.modelName,
    "--ak",
    `api_key=${options.apiKey}`,
    "-e",
    options.runtimeEnvironment,
    "--force-build",
    "--jobs-dir",
    options.logsDir,
    "--job-name",
    options.jobName,
  ];
  if (options.baseUrl) {
    command.splice(10, 0, "--ak", `base_url=${options.baseUrl}`);
  }
  return command;
}

export async function runSkillEffectPreflight(
  runtimeEnvironment: RuntimeEnvironment,
  env: NodeJS.ProcessEnv = process.env,
  commandRunner: CommandRunner = runCommand,
): Promise<RuntimePreflightResult> {
  const runtimePreflight = await runRuntimePreflight(runtimeEnvironment, env, commandRunner);
  if (!runtimePreflight.ok) {
    return runtimePreflight;
  }

  if (!readEnvValue(env, "OPENAI_API_KEY")) {
    return {
      ok: false,
      summary: "当前环境未设置 OPENAI_API_KEY，无法执行 skill-effect gate",
      details: [...runtimePreflight.details, "OPENAI_API_KEY 缺失或为空"],
    };
  }

  return {
    ok: true,
    summary: `harbor + ${runtimeEnvironment} + codex skill-effect preflight 通过`,
    details: runtimePreflight.details,
  };
}

export function stripSkillCopyLines(dockerfileText: string): { text: string; removedCount: number } {
  const keptLines: string[] = [];
  let removedCount = 0;
  for (const line of dockerfileText.split(/(?<=\n)/u)) {
    if (SKILL_COPY_RE.test(line)) {
      removedCount += 1;
      continue;
    }
    keptLines.push(line);
  }
  return {
    text: keptLines.join(""),
    removedCount,
  };
}

export async function prepareNoSkillVariant(options: {
  sourceTaskDir: string;
  targetTaskDir: string;
}): Promise<{ targetTaskDir: string; removedCopyLines: number }> {
  await copyDir(options.sourceTaskDir, options.targetTaskDir);

  const dockerfilePath = path.join(options.targetTaskDir, "environment", "Dockerfile");
  if (!(await pathExists(dockerfilePath))) {
    throw new Error(`no_skill 变体缺少 Dockerfile: ${dockerfilePath}`);
  }

  const dockerfileText = await readText(dockerfilePath);
  const stripped = stripSkillCopyLines(dockerfileText);
  await writeText(dockerfilePath, stripped.text);

  return {
    targetTaskDir: options.targetTaskDir,
    removedCopyLines: stripped.removedCount,
  };
}

export async function prepareWithSkillVariant(options: {
  sourceTaskDir: string;
  targetTaskDir: string;
}): Promise<{ targetTaskDir: string }> {
  await copyDir(options.sourceTaskDir, options.targetTaskDir);
  return {
    targetTaskDir: options.targetTaskDir,
  };
}

function buildVariantLogRoot(
  workspace: SkillEffectWorkspace,
  plan: DerivedTaskPlan,
  cycle: number,
  attemptIndex: number,
): string {
  return path.join(workspace.artifactsDir, "skill_effect", plan.derivedTaskId, `cycle-${cycle}-attempt-${attemptIndex}`);
}

async function runAgentVariant(options: {
  variant: SkillEffectVariant;
  workspace: SkillEffectWorkspace;
  plan: DerivedTaskPlan;
  taskDir: string;
  logsDir: string;
  runtimeEnvironment: RuntimeEnvironment;
  modelName: string;
  apiKey: string;
  baseUrl?: string;
  env?: NodeJS.ProcessEnv;
  signal?: AbortSignal;
}): Promise<AgentRunResult> {
  const jobName = `harbor-${options.variant}-${slugify(options.workspace.runId)}-${slugify(options.plan.derivedTaskId)}`;
  const logFilePath = path.join(options.logsDir, "harbor-run.log");
  const runtimeLogIndexPath = path.join(options.logsDir, "log-index.json");
  const command = buildHarborAgentCommand({
    taskDir: options.taskDir,
    logsDir: options.logsDir,
    jobName,
    runtimeEnvironment: options.runtimeEnvironment,
    apiKey: options.apiKey,
    modelName: options.modelName,
    baseUrl: options.baseUrl,
  });

  await ensureDir(options.logsDir);

  const baseEvidence: AgentRunEvidence = {
    variant: options.variant,
    variantTaskDir: options.taskDir,
    logsDir: options.logsDir,
    runtimeLogRoot: options.logsDir,
    runtimeLogIndexPath,
    logFilePath,
    jobDir: path.join(options.logsDir, jobName),
    command,
    summary: "未开始执行",
  };

  await writeRuntimeLogIndex(runtimeLogIndexPath, [
    { label: "variant-task-dir", path: options.taskDir },
    { label: "logs-dir", path: options.logsDir },
    { label: "harbor-run-log", path: logFilePath },
    { label: "job-dir", path: baseEvidence.jobDir },
  ]);

  const shellCommand = command.map(shellEscape).join(" ");
  const runResult = await runStreamingCommand("bash", ["-lc", shellCommand], {
    cwd: options.workspace.rootDir,
    env: options.env,
    logFilePath,
    heartbeatIntervalMs: 60_000,
    onHeartbeat: () => {
      console.log(`[skill-effect:${options.variant}] ${options.plan.derivedTaskId} 仍在运行，继续等待`);
    },
    onStdout: (chunk) => {
      process.stdout.write(chunk);
    },
    onStderr: (chunk) => {
      process.stderr.write(chunk);
    },
    signal: options.signal,
  });

  const jobDir = path.join(options.logsDir, jobName);
  const combinedOutput = `${runResult.stdout}\n${runResult.stderr}`;
  const summary = compactOutputSummary(combinedOutput);
  const trialResultPath = await findLatestTrialResultPath(jobDir);
  const trialDir = trialResultPath ? path.dirname(trialResultPath) : undefined;
  const stableResultPath = trialResultPath ? path.join(options.logsDir, "result.json") : undefined;
  if (trialResultPath && stableResultPath) {
    await copyFile(trialResultPath, stableResultPath);
  }
  const jobLogPath = path.join(jobDir, "job.log");
  const trialLogPath = trialDir ? path.join(trialDir, "trial.log") : undefined;
  const verifierStdoutPath = trialDir ? path.join(trialDir, "verifier", "test-stdout.txt") : undefined;
  const rewardTxtPath = trialDir ? path.join(trialDir, "verifier", "reward.txt") : undefined;
  const rewardJsonPath = trialDir ? path.join(trialDir, "verifier", "reward.json") : undefined;
  const rewardPath =
    rewardTxtPath && (await pathExists(rewardTxtPath))
      ? rewardTxtPath
      : rewardJsonPath && (await pathExists(rewardJsonPath))
        ? rewardJsonPath
        : rewardTxtPath ?? rewardJsonPath;
  const artifactManifestPath = trialDir ? path.join(trialDir, "artifacts", "manifest.json") : undefined;
  const trajectoryPath = trialDir ? path.join(trialDir, "agent", "trajectory.json") : undefined;
  const stableTrajectoryPath = trajectoryPath && (await pathExists(trajectoryPath)) ? trajectoryPath : undefined;
  const metrics = await extractHarborTrialMetrics(stableResultPath, stableTrajectoryPath);

  const evidence: AgentRunEvidence = {
    ...baseEvidence,
    jobDir,
    jobLogPath,
    trialDir,
    trialLogPath,
    resultPath: stableResultPath,
    verifierStdoutPath,
    rewardPath,
    artifactManifestPath,
    trajectoryPath: stableTrajectoryPath,
    metrics,
    summary,
  };

  await writeRuntimeLogIndex(runtimeLogIndexPath, [
    { label: "variant-task-dir", path: options.taskDir },
    { label: "logs-dir", path: options.logsDir },
    { label: "harbor-run-log", path: logFilePath },
    { label: "job-dir", path: jobDir },
    ...(trialDir ? [{ label: "trial-dir", path: trialDir }] : []),
    ...(trialLogPath ? [{ label: "trial-log", path: trialLogPath }] : []),
    ...(trialResultPath ? [{ label: "trial-result", path: trialResultPath }] : []),
    ...(stableResultPath ? [{ label: "stable-result", path: stableResultPath }] : []),
    ...(verifierStdoutPath ? [{ label: "verifier-stdout", path: verifierStdoutPath }] : []),
    ...(rewardPath ? [{ label: "reward-file", path: rewardPath }] : []),
    ...(artifactManifestPath ? [{ label: "artifact-manifest", path: artifactManifestPath }] : []),
    ...(evidence.trajectoryPath ? [{ label: "trajectory", path: evidence.trajectoryPath }] : []),
  ]);

  const finalizeResult = (result: {
    comparisonStatus: AgentComparisonStatus;
    comparisonReason: string;
    issues: string[];
    failureKind?: RuntimeFailureKind;
  }): AgentRunResult => ({
    variant: options.variant,
    passed: result.comparisonStatus === "pass",
    comparisonStatus: result.comparisonStatus,
    comparisonReason: result.comparisonReason,
    issues: result.issues,
    failureKind: result.failureKind,
    evidence,
  });

  if (!trialResultPath) {
    evidence.summary = "missing result.json";
    return finalizeResult({
      comparisonStatus: "invalid_fail",
      comparisonReason: "missing result.json",
      issues: [`harbor run 未产出可解析的 result.json: ${summary}`],
      failureKind: "harbor-task",
    });
  }

  let trialResult: unknown;
  try {
    trialResult = JSON.parse(await readText(trialResultPath)) as unknown;
  } catch {
    evidence.summary = "result.json parse failed";
    return finalizeResult({
      comparisonStatus: "invalid_fail",
      comparisonReason: "result.json parse failed",
      issues: ["harbor trial result.json 解析失败，详见 harbor-run.log"],
      failureKind: "harbor-task",
    });
  }

  if (!trialResult || typeof trialResult !== "object") {
    evidence.summary = "invalid result.json structure";
    return finalizeResult({
      comparisonStatus: "invalid_fail",
      comparisonReason: "invalid result.json structure",
      issues: ["harbor trial result.json 结构异常"],
      failureKind: "harbor-task",
    });
  }

  const resultRecord = trialResult as Record<string, unknown>;
  const exceptionInfo = resultRecord.exception_info;
  if (exceptionInfo && typeof exceptionInfo === "object") {
    const exception = exceptionInfo as Record<string, unknown>;
    const exceptionType = typeof exception.exception_type === "string" ? exception.exception_type : "Unknown";
    const exceptionMessage =
      typeof exception.exception_message === "string"
        ? exception.exception_message.slice(0, 300)
        : "未提供 exception_message";
    evidence.summary = `${exceptionType}: ${exceptionMessage}`;
    return finalizeResult({
      comparisonStatus: "invalid_fail",
      comparisonReason: `exception_info: ${exceptionType}`,
      issues: [`harbor agent 运行异常: ${exceptionType}: ${exceptionMessage}`],
      failureKind: "harbor-task",
    });
  }

  const verifierResult =
    resultRecord.verifier_result && typeof resultRecord.verifier_result === "object"
      ? (resultRecord.verifier_result as Record<string, unknown>)
      : null;
  const reward = extractPrimaryReward(verifierResult?.rewards);
  evidence.reward = reward;

  if (reward === null) {
    evidence.summary = "missing reward";
    return finalizeResult({
      comparisonStatus: "invalid_fail",
      comparisonReason: "missing reward",
      issues: ["harbor verifier 未产出 reward（reward.txt/reward.json）"],
      failureKind: "harbor-task",
    });
  }

  if (reward < 1.0) {
    evidence.summary = `reward=${reward}`;
    return finalizeResult({
      comparisonStatus: "valid_reward_fail",
      comparisonReason: `reward=${reward} < 1.0`,
      issues: [`harbor verifier reward=${reward} < 1.0`],
      failureKind: "harbor-reward",
    });
  }

  if (runResult.code !== 0) {
    evidence.summary = `reward=${reward}, exit_code=${runResult.code}`;
    return finalizeResult({
      comparisonStatus: "invalid_fail",
      comparisonReason: `non-zero exit code ${runResult.code}`,
      issues: [`harbor run 返回非零退出码: ${summary}`],
      failureKind: "harbor-task",
    });
  }

  evidence.summary = `reward=${reward}`;
  return finalizeResult({
    comparisonStatus: "pass",
    comparisonReason: `reward=${reward}`,
    issues: [],
  });
}

export function buildSkillEffectBucket(
  withSkillStatus: AgentComparisonStatus,
  noSkillStatus: AgentComparisonStatus,
): SkillEffectBucket {
  if (withSkillStatus === "pass" && noSkillStatus === "valid_reward_fail") {
    return "with_skill_pass__no_skill_fail";
  }
  if (withSkillStatus === "pass" && noSkillStatus === "invalid_fail") {
    return "with_skill_pass__no_skill_invalid_fail";
  }
  if (withSkillStatus === "pass" && noSkillStatus === "pass") {
    return "with_skill_pass__no_skill_pass";
  }
  if (noSkillStatus === "pass") {
    return "with_skill_fail__no_skill_pass";
  }
  if (noSkillStatus === "valid_reward_fail" || noSkillStatus === "invalid_fail") {
    return "with_skill_fail__no_skill_fail";
  }
  return "with_skill_fail__no_skill_fail";
}

export function isRepairRequiredSkillEffectBucket(bucket: SkillEffectBucket): boolean {
  return bucket !== "with_skill_pass__no_skill_fail";
}

export function isAcceptedSkillEffectBucket(bucket: SkillEffectBucket): boolean {
  return !isRepairRequiredSkillEffectBucket(bucket);
}

export function buildSkillEffectIssues(taskId: string, evaluation: SkillEffectEvaluationResult): ValidationIssue[] {
  if (!evaluation.repairRequired) {
    return [];
  }

  const issues: ValidationIssue[] = [];
  if (evaluation.bucket === "with_skill_pass__no_skill_invalid_fail") {
    issues.push({
      scope: "skill-effect",
      taskId,
      message: "真实对照结果为 with_skill pass / no_skill invalid fail；当前 no_skill 不是有效 reward 失败，必须继续修复 verifier、variant 构造或任务可用性问题",
    });
  } else if (evaluation.bucket === "with_skill_pass__no_skill_pass") {
    issues.push({
      scope: "skill-effect",
      taskId,
      message: "真实对照结果为 with_skill pass / no_skill pass；说明 no_skill 也能通过，当前任务未形成稳定的 skill bottleneck",
    });
  } else if (evaluation.bucket === "with_skill_fail__no_skill_pass") {
    issues.push({
      scope: "skill-effect",
      taskId,
      message: "真实对照结果为 with_skill fail / no_skill pass；出现 with_skill 反向劣势，必须修复",
    });
  } else {
    issues.push({
      scope: "skill-effect",
      taskId,
      message: "真实对照结果为 with_skill fail / no_skill fail；当前任务只在 with_skill_pass__no_skill_fail 时才可接受，必须继续排查 verifier、variant 构造或任务可用性问题",
    });
  }

  issues.push({
    scope: "skill-effect",
    taskId,
    message: `with_skill 实跑摘要: ${evaluation.withSkill.evidence.summary}`,
  });
  issues.push({
    scope: "skill-effect",
    taskId,
    message: `with_skill 判定: ${evaluation.withSkill.comparisonStatus} (${evaluation.withSkill.comparisonReason})`,
  });
  issues.push({
    scope: "skill-effect",
    taskId,
    message: `no_skill 实跑摘要: ${evaluation.noSkill.evidence.summary}`,
  });
  issues.push({
    scope: "skill-effect",
    taskId,
    message: `no_skill 判定: ${evaluation.noSkill.comparisonStatus} (${evaluation.noSkill.comparisonReason})`,
  });
  return issues;
}


export async function runSkillEffectEvaluation(args: {
  workspace: SkillEffectWorkspace;
  plan: DerivedTaskPlan;
  runtimeEnvironment: RuntimeEnvironment;
  cycle: number;
  attemptIndex: number;
  draftTaskDir: string;
  modelName: string;
  apiKey: string;
  baseUrl?: string;
  env?: NodeJS.ProcessEnv;
  signal?: AbortSignal;
  deps?: Partial<SkillEffectDeps>;
}): Promise<SkillEffectEvaluationResult> {
  const deps: SkillEffectDeps = {
    ...DEFAULT_SKILL_EFFECT_DEPS,
    ...args.deps,
  };
  const pairRoot = buildVariantLogRoot(args.workspace, args.plan, args.cycle, args.attemptIndex);
  const withSkillLogsDir = path.join(pairRoot, "with_skill");
  const noSkillLogsDir = path.join(pairRoot, "no_skill");
  const withSkillTaskDir = path.join(pairRoot, "variants", "with_skill");
  const noSkillTaskDir = path.join(pairRoot, "variants", "no_skill");

  await deps.prepareWithSkillVariant({
    sourceTaskDir: args.draftTaskDir,
    targetTaskDir: withSkillTaskDir,
  });

  await deps.prepareNoSkillVariant({
    sourceTaskDir: withSkillTaskDir,
    targetTaskDir: noSkillTaskDir,
  });

  const withSkillPromise = deps.runAgentVariant({
    variant: "with_skill",
    workspace: args.workspace,
    plan: args.plan,
    taskDir: withSkillTaskDir,
    logsDir: withSkillLogsDir,
    runtimeEnvironment: args.runtimeEnvironment,
    modelName: args.modelName,
    apiKey: args.apiKey,
    baseUrl: args.baseUrl,
    env: args.env,
    signal: args.signal,
  });

  const noSkillPromise = deps.runAgentVariant({
    variant: "no_skill",
    workspace: args.workspace,
    plan: args.plan,
    taskDir: noSkillTaskDir,
    logsDir: noSkillLogsDir,
    runtimeEnvironment: args.runtimeEnvironment,
    modelName: args.modelName,
    apiKey: args.apiKey,
    baseUrl: args.baseUrl,
    env: args.env,
    signal: args.signal,
  });

  const [withSkillSettled, noSkillSettled] = await Promise.allSettled([withSkillPromise, noSkillPromise]);
  if (withSkillSettled.status === "rejected") {
    throw withSkillSettled.reason;
  }
  if (noSkillSettled.status === "rejected") {
    throw noSkillSettled.reason;
  }

  const withSkill = withSkillSettled.value;
  const noSkill = noSkillSettled.value;

  const bucket = buildSkillEffectBucket(withSkill.comparisonStatus, noSkill.comparisonStatus);
  return {
    bucket,
    repairRequired: isRepairRequiredSkillEffectBucket(bucket),
    pairRoot,
    withSkill,
    noSkill,
  };
}
