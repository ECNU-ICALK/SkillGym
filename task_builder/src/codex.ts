import { promises as fs } from "node:fs";
import path from "node:path";
import { Codex, type ThreadOptions, type TurnOptions } from "@openai/codex-sdk";
import { z } from "zod";
import type { GenerationUnit } from "./discovery.js";
import type {
  BlockingReviewResult,
  BlockingReviewerTaskResult,
  DerivedTaskPlan,
  SingleTaskPlan,
  RepairTurnResult,
  WriterSummary,
} from "./schema.js";
import {
  blockingReviewResultJsonSchema,
  blockingReviewResultSchema,
  repairTurnResultJsonSchema,
  repairTurnResultSchema,
  singleTaskPlanJsonSchema,
  singleTaskPlanSchema,
  writerSummaryJsonSchema,
  writerSummarySchema,
} from "./schema.js";
import { parseJsonWithFallback, pathExists } from "./utils.js";
import {
  buildBlockingReviewerPrompt,
  buildRepairPrompt,
  buildSingleTaskPlannerPrompt,
  buildTaskWriterPrompt,
  relativeDraftPath,
} from "./prompts.js";

type StructuredRunResult<T> = {
  data: T;
  threadId: string | null;
  raw: string;
};

type WorkspaceRootProvider = {
  rootDir: string;
};

type CodexThreadRunner = {
  id: string | null;
  run: (input: string, turnOptions?: TurnOptions) => Promise<{
    items: unknown[];
    finalResponse: string;
    usage: unknown | null;
  }>;
};

type CodexThreadFactory = {
  startThread: (options?: ThreadOptions) => CodexThreadRunner;
  resumeThread: (id: string, options?: ThreadOptions) => CodexThreadRunner;
};

const CODEX_RETRY_BACKOFF_MS = [15 * 60_000, 30 * 60_000, 60 * 60_000] as const;

function getCodexRetryDelayMs(retryCount: number): number {
  return CODEX_RETRY_BACKOFF_MS[Math.min(retryCount - 1, CODEX_RETRY_BACKOFF_MS.length - 1)]!;
}

const writerSummaryPartialSchema = z
  .object({
    derivedTaskId: z.string().optional(),
    draftRelativePath: z.string().optional(),
    filesWritten: z.array(z.string()).optional(),
    summary: z.string().optional(),
  })
  .passthrough();

function stringifyUnknownValue(value: unknown): string {
  if (typeof value === "string") {
    return value;
  }
  try {
    return JSON.stringify(value);
  } catch {
    return String(value);
  }
}

function toIssueList(value: unknown): string[] {
  if (Array.isArray(value)) {
    return value
      .map((item) => stringifyUnknownValue(item).trim())
      .filter((item) => item.length > 0);
  }
  if (typeof value === "string") {
    const trimmed = value.trim();
    return trimmed ? [trimmed] : [];
  }
  if (value === undefined || value === null) {
    return [];
  }
  const normalized = stringifyUnknownValue(value).trim();
  return normalized ? [normalized] : [];
}

function buildBlockingReviewerFallbackResult(taskPlans: DerivedTaskPlan[], message: string): BlockingReviewResult {
  return {
    taskResults: taskPlans.map((plan) => ({
      derivedTaskId: plan.derivedTaskId,
      blockingPass: false,
      blockingIssues: [message],
    })),
  };
}

function buildIndexedRawTaskResults(
  taskPlans: DerivedTaskPlan[],
  rawTaskResultsValue: unknown,
  normalizationIssues: string[],
): {
  rawTaskById: Map<string, unknown>;
  positionalFallbacks: unknown[];
} {
  const expectedTaskIds = new Set(taskPlans.map((plan) => plan.derivedTaskId));
  const rawTaskResults = Array.isArray(rawTaskResultsValue) ? rawTaskResultsValue : [];
  if (!Array.isArray(rawTaskResultsValue)) {
    normalizationIssues.push("reviewer 未返回 taskResults 数组，已回退为逐任务失败结果");
  }

  const rawTaskById = new Map<string, unknown>();
  const positionalFallbacks: unknown[] = [];
  for (const rawTask of rawTaskResults) {
    if (!rawTask || typeof rawTask !== "object" || Array.isArray(rawTask)) {
      positionalFallbacks.push(rawTask);
      continue;
    }
    const record = rawTask as Record<string, unknown>;
    const rawTaskId = typeof record.derivedTaskId === "string" ? record.derivedTaskId.trim() : "";
    if (rawTaskId && expectedTaskIds.has(rawTaskId) && !rawTaskById.has(rawTaskId)) {
      rawTaskById.set(rawTaskId, rawTask);
      continue;
    }
    if (rawTaskId && !expectedTaskIds.has(rawTaskId)) {
      normalizationIssues.push(`reviewer 返回了未知任务结果: ${rawTaskId}`);
      continue;
    }
    positionalFallbacks.push(rawTask);
  }

  return { rawTaskById, positionalFallbacks };
}

function normalizeBlockingReviewerTaskResult(
  rawValue: unknown,
  plan: DerivedTaskPlan,
  normalizationIssues: string[],
  options: {
    fallbackByPosition: boolean;
  },
): BlockingReviewerTaskResult {
  if (!rawValue || typeof rawValue !== "object" || Array.isArray(rawValue)) {
    return {
      derivedTaskId: plan.derivedTaskId,
      blockingPass: false,
      blockingIssues: ["reviewer 返回的 taskResult 结构异常"],
    };
  }

  const record = rawValue as Record<string, unknown>;
  const normalizedIssues = toIssueList(record.blockingIssues ?? record.issues);
  const rawTaskId = typeof record.derivedTaskId === "string" ? record.derivedTaskId.trim() : "";
  if (!rawTaskId && options.fallbackByPosition) {
    normalizationIssues.push(`reviewer 未返回 ${plan.derivedTaskId} 的 derivedTaskId，已按位置映射`);
  } else if (rawTaskId && rawTaskId !== plan.derivedTaskId) {
    normalizationIssues.push(`reviewer 返回 derivedTaskId=${rawTaskId}，已映射到 ${plan.derivedTaskId}`);
  }

  const blockingPass =
    typeof record.blockingPass === "boolean"
      ? record.blockingPass
      : typeof record.pass === "boolean"
        ? record.pass
        : normalizedIssues.length === 0;
  if (typeof record.blockingPass !== "boolean") {
    normalizationIssues.push(`reviewer 未返回 ${plan.derivedTaskId} 的 blockingPass，已按 issues 推导`);
  }

  return {
    derivedTaskId: plan.derivedTaskId,
    blockingPass,
    blockingIssues: normalizedIssues,
  };
}

export function normalizeBlockingReviewResultFromRaw(
  taskPlans: DerivedTaskPlan[],
  rawResponse: string,
): BlockingReviewResult {
  let parsedValue: unknown;
  try {
    parsedValue = parseJsonWithFallback<unknown>(rawResponse);
  } catch (error) {
    return buildBlockingReviewerFallbackResult(
      taskPlans,
      `reviewer structured output 无法解析，已回退为全任务失败: ${compactErrorMessage(error)}`,
    );
  }

  if (!parsedValue || typeof parsedValue !== "object" || Array.isArray(parsedValue)) {
    return buildBlockingReviewerFallbackResult(taskPlans, "reviewer structured output 不是合法对象，已回退为全任务失败");
  }

  const normalizationIssues: string[] = [];
  const root = parsedValue as Record<string, unknown>;
  const { rawTaskById, positionalFallbacks } = buildIndexedRawTaskResults(taskPlans, root.taskResults, normalizationIssues);

  const normalizedTaskResults: BlockingReviewerTaskResult[] = [];
  for (const plan of taskPlans) {
    const directMatch = rawTaskById.get(plan.derivedTaskId);
    if (directMatch) {
      normalizedTaskResults.push(
        normalizeBlockingReviewerTaskResult(directMatch, plan, normalizationIssues, {
          fallbackByPosition: false,
        }),
      );
      continue;
    }

    const positionalMatch = positionalFallbacks.shift();
    if (positionalMatch !== undefined) {
      normalizedTaskResults.push(
        normalizeBlockingReviewerTaskResult(positionalMatch, plan, normalizationIssues, {
          fallbackByPosition: true,
        }),
      );
      continue;
    }

    normalizationIssues.push(`reviewer 未返回 ${plan.derivedTaskId} 的审查结果，已补为失败`);
    normalizedTaskResults.push({
      derivedTaskId: plan.derivedTaskId,
      blockingPass: false,
      blockingIssues: ["reviewer 未返回该任务的审查结果"],
    });
  }

  if (positionalFallbacks.length > 0) {
    normalizationIssues.push(`reviewer 返回了 ${positionalFallbacks.length} 条无法匹配到当前任务的额外结果，已忽略`);
  }

  if (normalizationIssues.length > 0 && normalizedTaskResults.length > 0) {
    normalizedTaskResults[0] = {
      ...normalizedTaskResults[0],
      blockingPass: false,
      blockingIssues: [...normalizedTaskResults[0].blockingIssues, ...normalizationIssues],
    };
  }

  return blockingReviewResultSchema.parse({
    taskResults: normalizedTaskResults,
  });
}

export function normalizeRepairTurnResultFromRaw(rawResponse: string): RepairTurnResult {
  return repairTurnResultSchema.parse(parseJsonWithFallback<RepairTurnResult>(rawResponse));
}

function toPosixPath(value: string): string {
  return value.split(path.sep).join(path.posix.sep);
}

function compactErrorMessage(error: unknown, maxLength = 240): string {
  const message = error instanceof Error ? error.message : String(error);
  return message.length > maxLength ? `${message.slice(0, maxLength)}...` : message;
}

async function listFilesRecursively(
  dirPath: string,
  options: {
    rootRelativePrefix: string;
    ignoreDirNames?: Set<string>;
    ignorePathPrefixes?: string[];
    ignoreFileExtensions?: Set<string>;
    ignoreFileNames?: Set<string>;
    limit?: number;
  },
): Promise<string[]> {
  const results: string[] = [];
  const ignoreDirNames = options.ignoreDirNames ?? new Set<string>();
  const ignorePathPrefixes = options.ignorePathPrefixes ?? [];
  const ignoreFileExtensions = options.ignoreFileExtensions ?? new Set<string>();
  const ignoreFileNames = options.ignoreFileNames ?? new Set<string>();
  const limit = options.limit ?? 200;

  async function walk(currentDir: string, relativeDir: string): Promise<void> {
    if (results.length >= limit) {
      return;
    }
    const entries = await fs.readdir(currentDir, { withFileTypes: true });
    for (const entry of entries) {
      if (results.length >= limit) {
        return;
      }
      if (entry.isDirectory() && ignoreDirNames.has(entry.name)) {
        continue;
      }
      const relativePath = relativeDir ? path.join(relativeDir, entry.name) : entry.name;
      const posixRelativePath = toPosixPath(relativePath);
      if (ignorePathPrefixes.some((prefix) => posixRelativePath.startsWith(prefix))) {
        continue;
      }
      const fullPath = path.join(currentDir, entry.name);
      if (entry.isDirectory()) {
        await walk(fullPath, relativePath);
        continue;
      }
      if (!entry.isFile()) {
        continue;
      }
      if (ignoreFileNames.has(entry.name)) {
        continue;
      }
      const extension = path.extname(entry.name);
      if (extension && ignoreFileExtensions.has(extension)) {
        continue;
      }
      results.push(path.posix.join(options.rootRelativePrefix, posixRelativePath));
    }
  }

  await walk(dirPath, "");
  return results.sort((a, b) => a.localeCompare(b));
}

async function inferWriterFilesWritten(
  workspace: WorkspaceRootProvider,
  derivedTaskId: string,
  draftRelativePathValue: string,
): Promise<string[]> {
  const draftRelativePathNormalized = draftRelativePathValue || relativeDraftPath(derivedTaskId);
  const draftDir = path.join(workspace.rootDir, draftRelativePathNormalized);
  const required: string[] = [
    "plan.json",
    "task.toml",
    "instruction.md",
    path.posix.join("environment", "Dockerfile"),
    path.posix.join("solution", "solve.sh"),
    path.posix.join("tests", "test.sh"),
    path.posix.join("tests", "test_outputs.py"),
  ];

  const filesWritten: string[] = [];
  const prefix = toPosixPath(draftRelativePathNormalized);
  for (const rel of required) {
    if (await pathExists(path.join(draftDir, rel))) {
      filesWritten.push(path.posix.join(prefix, rel));
    }
  }

  const envDir = path.join(draftDir, "environment");
  if (await pathExists(envDir)) {
    const envFiles = await listFilesRecursively(envDir, {
      rootRelativePrefix: path.posix.join(prefix, "environment"),
      ignoreDirNames: new Set(["skills", "__pycache__", ".pytest_cache"]),
      ignoreFileExtensions: new Set([".pyc"]),
      ignoreFileNames: new Set(["Dockerfile"]),
      limit: 80,
    });
    filesWritten.push(...envFiles);
  }

  const unique = Array.from(new Set(filesWritten));
  return unique.length > 0 ? unique : required.map((rel) => path.posix.join(prefix, rel));
}

export class CodexTaskBuilderClient {
  private readonly codex: CodexThreadFactory;
  private readonly threadBaseOptions: ThreadOptions;
  private readonly codexRunRetries: number;
  private readonly sleep: (ms: number) => Promise<void>;

  constructor(
    options: {
      codexRunRetries?: number;
      sleep?: (ms: number) => Promise<void>;
      codex?: CodexThreadFactory;
    } = {},
  ) {
    this.codex =
      options.codex ??
      new Codex({
        codexPathOverride: process.env.CODEX_PATH,
      });

    const sandboxMode =
      process.env.CODEX_TASK_BUILDER_SANDBOX_MODE === "workspace-write" ? "workspace-write" : "danger-full-access";
    const networkAccessEnabled = process.env.CODEX_TASK_BUILDER_NETWORK_ACCESS !== "0";

    this.threadBaseOptions = {
      model: process.env.CODEX_TASK_BUILDER_MODEL,
      sandboxMode,
      approvalPolicy: "never",
      skipGitRepoCheck: true,
      networkAccessEnabled,
      modelReasoningEffort: "high",
    };

    this.codexRunRetries = options.codexRunRetries ?? 0;
    this.sleep =
      options.sleep ??
      ((ms: number) =>
        new Promise((resolve) => {
          setTimeout(resolve, ms);
        }));
  }

  private makeThread(workingDirectory: string, threadId?: string | null): CodexThreadRunner {
    const options: ThreadOptions = {
      ...this.threadBaseOptions,
      workingDirectory,
    };
    return threadId ? this.codex.resumeThread(threadId, options) : this.codex.startThread(options);
  }

  private async sleepWithSignal(ms: number, signal?: AbortSignal): Promise<void> {
    if (!signal) {
      await this.sleep(ms);
      return;
    }
    if (signal.aborted) {
      throw signal.reason instanceof Error ? signal.reason : new Error("操作已中断");
    }
    let abortListener: (() => void) | undefined;
    await Promise.race([
      this.sleep(ms),
      new Promise<never>((_, reject) => {
        abortListener = () => {
          reject(signal.reason instanceof Error ? signal.reason : new Error("操作已中断"));
        };
        signal.addEventListener("abort", abortListener, {
          once: true,
        });
      }),
    ]);
    if (abortListener) {
      signal.removeEventListener("abort", abortListener);
    }
  }

  private async runThreadWithRetries<T>(
    label: string,
    createThread: () => CodexThreadRunner,
    execute: (thread: CodexThreadRunner) => Promise<T>,
    options: {
      signal?: AbortSignal;
    } = {},
  ): Promise<{ result: T; threadId: string | null }> {
    let retryCount = 0;

    while (true) {
      const thread = createThread();
      try {
        const result = await execute(thread);
        return {
          result,
          threadId: thread.id,
        };
      } catch (error) {
        if (options.signal?.aborted || (error instanceof Error && error.name === "AbortError")) {
          throw error;
        }
        if (retryCount >= this.codexRunRetries) {
          throw error;
        }

        retryCount += 1;
        const delayMs = getCodexRetryDelayMs(retryCount);
        console.warn(
          `[codex-retry:${label}] 第 ${retryCount}/${this.codexRunRetries} 次重试，${delayMs / 1000}s 后重试：${compactErrorMessage(error)}`,
        );
        await this.sleepWithSignal(delayMs, options.signal);
      }
    }
  }

  async planTask(
    unit: GenerationUnit,
    workspace: WorkspaceRootProvider,
    plan: Pick<DerivedTaskPlan, "derivedTaskId" | "taskOrdinal">,
    options: {
      signal?: AbortSignal;
    } = {},
  ): Promise<StructuredRunResult<SingleTaskPlan>> {
    const { result: turn, threadId } = await this.runThreadWithRetries(
      "plan-task",
      () => this.makeThread(workspace.rootDir),
      async (thread) =>
        thread.run(buildSingleTaskPlannerPrompt(unit, plan), {
          outputSchema: singleTaskPlanJsonSchema,
          signal: options.signal,
        }),
      options,
    );
    const parsed = singleTaskPlanSchema.parse(parseJsonWithFallback<SingleTaskPlan>(turn.finalResponse));
    return {
      data: parsed,
      threadId,
      raw: turn.finalResponse,
    };
  }

  async writeTask(
    unit: GenerationUnit,
    workspace: WorkspaceRootProvider,
    plan: DerivedTaskPlan,
    options: {
      signal?: AbortSignal;
      draftDirLabel?: string;
    } = {},
  ): Promise<StructuredRunResult<WriterSummary>> {
    const { result: turn, threadId } = await this.runThreadWithRetries(
      "write-task",
      () => this.makeThread(workspace.rootDir),
      async (thread) =>
        thread.run(buildTaskWriterPrompt(unit, plan, { draftDirLabel: options.draftDirLabel }), {
          outputSchema: writerSummaryJsonSchema,
          signal: options.signal,
        }),
      options,
    );

    let parsedValue: unknown | null = null;
    let parseFailure: string | null = null;
    try {
      parsedValue = parseJsonWithFallback<unknown>(turn.finalResponse);
    } catch (error) {
      parseFailure = compactErrorMessage(error);
    }

    if (parsedValue) {
      const strict = writerSummarySchema.safeParse(parsedValue);
      if (strict.success) {
        return {
          data: strict.data,
          threadId,
          raw: turn.finalResponse,
        };
      }
    }

    const partial = parsedValue ? writerSummaryPartialSchema.safeParse(parsedValue) : null;
    const derivedTaskId = partial?.success && partial.data.derivedTaskId ? partial.data.derivedTaskId : plan.derivedTaskId;
    const draftRelativePathValue =
      partial?.success && partial.data.draftRelativePath
        ? partial.data.draftRelativePath
        : options.draftDirLabel?.replace(/\/$/, "") || relativeDraftPath(derivedTaskId);
    const filesWritten =
      partial?.success && partial.data.filesWritten && partial.data.filesWritten.length > 0
        ? partial.data.filesWritten
        : await inferWriterFilesWritten(workspace, derivedTaskId, draftRelativePathValue);
    const summary =
      partial?.success && partial.data.summary
        ? partial.data.summary
        : `writer structured output 未通过校验${parseFailure ? `（${parseFailure}）` : ""}，已回退为从磁盘推断 filesWritten`;

    return {
      data: {
        derivedTaskId,
        draftRelativePath: draftRelativePathValue,
        filesWritten,
        summary,
      },
      threadId,
      raw: turn.finalResponse,
    };
  }

  async reviewTaskBlocking(
    unit: GenerationUnit,
    workspace: WorkspaceRootProvider,
    plan: DerivedTaskPlan,
    options: {
      signal?: AbortSignal;
      draftDirLabel?: string;
    } = {},
  ): Promise<StructuredRunResult<BlockingReviewResult>> {
    const { result: turn, threadId } = await this.runThreadWithRetries(
      "review-task-blocking",
      () => this.makeThread(workspace.rootDir),
      async (thread) =>
        thread.run(buildBlockingReviewerPrompt(unit, plan, { draftDirLabel: options.draftDirLabel }), {
          outputSchema: blockingReviewResultJsonSchema,
          signal: options.signal,
        }),
      options,
    );
    const parsed = normalizeBlockingReviewResultFromRaw([plan], turn.finalResponse);
    return {
      data: parsed,
      threadId,
      raw: turn.finalResponse,
    };
  }

  async repairTask(args: {
    unit: GenerationUnit;
    workspace: WorkspaceRootProvider;
    plan: DerivedTaskPlan;
    draftDirLabel?: string;
    blockingIssues: string[];
    staticIssues: string[];
    runtimeIssues: string[];
    skillEffectIssues: string[];
    runtimeDir?: string;
    runtimeLogRoot?: string;
    runtimeLogIndexPath?: string;
    runtimeLogPath?: string;
    runtimeResultPath?: string;
    jobLogPath?: string;
    trialLogPath?: string;
    verifierStdoutPath?: string;
    rewardPath?: string;
    artifactManifestPath?: string;
    skillEffectEvidenceRoot?: string;
    skillEffectResultPath?: string;
    skillEffectBucket?: string;
    threadId?: string | null;
    signal?: AbortSignal;
  }): Promise<StructuredRunResult<RepairTurnResult>> {
    const { result: turn, threadId } = await this.runThreadWithRetries(
      "repair-task",
      () => this.makeThread(args.workspace.rootDir, args.threadId),
      async (thread) =>
        thread.run(
          buildRepairPrompt({
            unit: args.unit,
            plan: args.plan,
            draftDirLabel: args.draftDirLabel,
            blockingIssues: args.blockingIssues,
            staticIssues: args.staticIssues,
            runtimeIssues: args.runtimeIssues,
            skillEffectIssues: args.skillEffectIssues,
            runtimeDir: args.runtimeDir,
            runtimeLogRoot: args.runtimeLogRoot,
            runtimeLogIndexPath: args.runtimeLogIndexPath,
            runtimeLogPath: args.runtimeLogPath,
            runtimeResultPath: args.runtimeResultPath,
            jobLogPath: args.jobLogPath,
            trialLogPath: args.trialLogPath,
            verifierStdoutPath: args.verifierStdoutPath,
            rewardPath: args.rewardPath,
            artifactManifestPath: args.artifactManifestPath,
            skillEffectEvidenceRoot: args.skillEffectEvidenceRoot,
            skillEffectResultPath: args.skillEffectResultPath,
            skillEffectBucket: args.skillEffectBucket,
          }),
          {
            outputSchema: repairTurnResultJsonSchema,
            signal: args.signal,
          },
        ),
      {
        signal: args.signal,
      },
    );
    const parsed = normalizeRepairTurnResultFromRaw(turn.finalResponse);
    return {
      data: parsed,
      threadId,
      raw: turn.finalResponse,
    };
  }
}
