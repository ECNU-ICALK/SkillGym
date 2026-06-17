import { promises as fs } from "node:fs";
import path from "node:path";
import { buildTaskDisplayName } from "./prompts.js";
import { getVisibleSkills, type GenerationUnit } from "./discovery.js";
import type { BlockingReviewResult, DerivedTaskPlan } from "./schema.js";
import {
  canonicalTaskName,
  copyFile,
  ensureDir,
  pathExists,
  readText,
  runCommand,
  runStreamingCommand,
  slugify,
  writeJson,
} from "./utils.js";

export type ValidationIssue = {
  scope: "family" | "reviewer" | "static" | "runtime" | "skill-effect";
  message: string;
  taskId?: string;
};

export type RuntimeEnvironment = "e2b" | "daytona" | "docker";
export type RuntimeFailureKind = "harbor-preflight" | "harbor-task" | "harbor-reward";

export type RuntimePreflightResult = {
  ok: boolean;
  summary: string;
  details: string[];
};

export type RuntimeEvidence = {
  logsDir: string;
  runtimeDir: string;
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
  command: string[];
  reward?: number | null;
  summary: string;
};

export type RuntimeValidationResult = {
  passed: boolean;
  issues: ValidationIssue[];
  failureKind?: RuntimeFailureKind;
  evidence: RuntimeEvidence;
};

export type ReviewValidationResult = {
  taskIssuesById: Map<string, ValidationIssue[]>;
};

type CommandRunner = typeof runCommand;

type ParsedTaskSection = {
  stringValues: Map<string, string>;
  arrayValues: Map<string, string[]>;
  numberValues: Map<string, number>;
};

const PUBLIC_REGISTRY_ALLOWLIST = new Set([
  "docker.io",
  "ghcr.io",
  "quay.io",
  "mcr.microsoft.com",
  "public.ecr.aws",
]);

const AGENT_SKILL_DESTINATION_ALLOWLIST = new Set([
  "/root/.claude/skills",
  "/root/.claude/skills/",
  "/root/.codex/skills",
  "/root/.codex/skills/",
  "/root/.opencode/skill",
  "/root/.opencode/skill/",
  "/root/.goose/skills",
  "/root/.goose/skills/",
  "/root/.factory/skills",
  "/root/.factory/skills/",
  "/root/.agents/skills",
  "/root/.agents/skills/",
  "/root/.github/skills",
  "/root/.github/skills/",
]);

type RuntimeLogEntry = {
  label: string;
  path: string;
};

type RuntimeWorkspace = {
  runId: string;
  rootDir: string;
  artifactsDir: string;
};

function containsCjkCharacters(text: string): boolean {
  return /[\u3400-\u4dbf\u4e00-\u9fff\uf900-\ufaff]/u.test(text);
}

function escapeRegExp(text: string): string {
  return text.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
}

function detectSkillRuntimeCoupling(
  content: string,
  unit: GenerationUnit,
): string[] {
  const detections: string[] = [];
  const patterns: Array<{ regex: RegExp; label: string }> = [
    {
      regex: /\/root\/\.(?:codex|claude|agents|goose|factory|gemini)\/skills\b|\/root\/\.opencode\/skill\b/u,
      label: "引用已安装 skill 目录",
    },
    {
      regex: /\/(?:app|workspace|workdir|mnt)\/skills\b/u,
      label: "引用容器内 skills 目录",
    },
    {
      regex: /environment\/skills\b/u,
      label: "引用 environment/skills 目录",
    },
    {
      regex: /\b(?:sys\.path\.(?:append|insert)|PYTHONPATH=)[^\n]*skills\b/u,
      label: "通过 path 注入 skills 目录",
    },
    {
      regex: /\b(?:from|import)\s+skills\.[\w.]+|\bpython(?:3)?\s+-m\s+skills\.[\w.]+/u,
      label: "导入 skills.* 模块",
    },
  ];

  const visibleSkillDirNames = getVisibleSkills(unit)
    .map((skill) => skill.dirName.trim())
    .filter((dirName) => dirName.length > 0);
  if (visibleSkillDirNames.length > 0) {
    const joinedDirNames = visibleSkillDirNames.map((dirName) => escapeRegExp(dirName)).join("|");
    patterns.push({
      regex: new RegExp(String.raw`(?:^|[^A-Za-z0-9_])(?:\.\/)?skills\/(?:${joinedDirNames})(?:\/|\b)`, "u"),
      label: "引用 task 内 shipped skill 路径",
    });
  }

  for (const pattern of patterns) {
    if (pattern.regex.test(content)) {
      detections.push(pattern.label);
    }
  }

  return detections;
}

async function listFilesRecursive(rootDir: string): Promise<string[]> {
  if (!(await pathExists(rootDir))) {
    return [];
  }

  const entries = await fs.readdir(rootDir, { withFileTypes: true });
  const files: string[] = [];

  for (const entry of entries.sort((a, b) => a.name.localeCompare(b.name))) {
    const fullPath = path.join(rootDir, entry.name);
    if (entry.isDirectory()) {
      files.push(...(await listFilesRecursive(fullPath)));
      continue;
    }
    if (entry.isFile()) {
      files.push(fullPath);
    }
  }

  return files;
}

async function collectRelativeFiles(rootDir: string): Promise<string[]> {
  const files = await listFilesRecursive(rootDir);
  return files.map((filePath) => path.relative(rootDir, filePath)).sort((a, b) => a.localeCompare(b));
}

async function compareDirectoryContent(leftDir: string, rightDir: string): Promise<string[]> {
  const leftFiles = await collectRelativeFiles(leftDir);
  const rightFiles = await collectRelativeFiles(rightDir);
  const issues: string[] = [];

  const missingFiles = leftFiles.filter((relativePath) => !rightFiles.includes(relativePath));
  const unexpectedFiles = rightFiles.filter((relativePath) => !leftFiles.includes(relativePath));
  if (missingFiles.length > 0) {
    issues.push(`缺少文件: ${missingFiles.join(", ")}`);
  }
  if (unexpectedFiles.length > 0) {
    issues.push(`存在额外文件: ${unexpectedFiles.join(", ")}`);
  }

  const sharedFiles = leftFiles.filter((relativePath) => rightFiles.includes(relativePath));
  for (const relativePath of sharedFiles) {
    const [leftContent, rightContent] = await Promise.all([
      fs.readFile(path.join(leftDir, relativePath)),
      fs.readFile(path.join(rightDir, relativePath)),
    ]);
    if (!leftContent.equals(rightContent)) {
      issues.push(`文件内容已变更: ${relativePath}`);
    }
  }

  return issues;
}

function pushTaskIssue(
  taskIssuesById: Map<string, ValidationIssue[]>,
  taskId: string,
  issue: ValidationIssue,
): void {
  const issues = taskIssuesById.get(taskId) ?? [];
  issues.push(issue);
  taskIssuesById.set(taskId, issues);
}

function runtimeIssue(taskId: string, message: string): ValidationIssue {
  return {
    scope: "runtime",
    taskId,
    message,
  };
}

export function validateTaskPlans(
  taskPlans: DerivedTaskPlan[],
  options: {
    taskOrdinals: number[];
  },
): ValidationIssue[] {
  const issues: ValidationIssue[] = [];
  const ids = taskPlans.map((task) => task.derivedTaskId);

  if (new Set(ids).size !== ids.length) {
    issues.push({ scope: "family", message: "derivedTaskId 存在重复" });
  }

  if (taskPlans.length !== options.taskOrdinals.length) {
    issues.push({
      scope: "family",
      message: `task 任务数量错误，期望 ${options.taskOrdinals.length}，实际 ${taskPlans.length}`,
    });
  }

  for (const [index, task] of taskPlans.entries()) {
    const expectedOrdinal = options.taskOrdinals[index];
    if (!expectedOrdinal) {
      continue;
    }
    const expectedId = canonicalTaskName(expectedOrdinal);
    if (task.derivedTaskId !== expectedId) {
      issues.push({
        scope: "family",
        taskId: task.derivedTaskId,
        message: `任务短名应为 ${expectedId}，当前为 ${task.derivedTaskId}`,
      });
    }
    if (task.taskOrdinal !== expectedOrdinal) {
      issues.push({
        scope: "family",
        taskId: task.derivedTaskId,
        message: `task 任务序号应为 ${expectedOrdinal}，当前为 ${task.taskOrdinal}`,
      });
    }
  }

  return issues;
}

export function collectFamilyObservationIssues(
  taskPlans: DerivedTaskPlan[],
  options: {
    taskCount: number;
  },
): ValidationIssue[] {
  const issues: ValidationIssue[] = [];

  if (taskPlans.length !== options.taskCount) {
    issues.push({
      scope: "family",
      message: `family task 数量不是 ${options.taskCount} 个`,
    });
  }

  return issues;
}

export function validateBlockingReviewResult(
  taskPlans: DerivedTaskPlan[],
  review: BlockingReviewResult,
): ReviewValidationResult {
  const taskIssuesById = new Map<string, ValidationIssue[]>();
  const expectedTaskIds = new Set(taskPlans.map((task) => task.derivedTaskId));
  const seenTaskIds = new Set<string>();

  for (const taskId of expectedTaskIds) {
    taskIssuesById.set(taskId, []);
  }

  for (const taskResult of review.taskResults) {
    if (!expectedTaskIds.has(taskResult.derivedTaskId)) {
      continue;
    }

    seenTaskIds.add(taskResult.derivedTaskId);
    if (!taskResult.blockingPass || taskResult.blockingIssues.length > 0) {
      pushTaskIssue(taskIssuesById, taskResult.derivedTaskId, {
        scope: "reviewer",
        taskId: taskResult.derivedTaskId,
        message: taskResult.blockingIssues.join("; ") || "blocking reviewer 判定失败，但未提供原因",
      });
    }
  }

  for (const taskId of expectedTaskIds) {
    if (!seenTaskIds.has(taskId)) {
      pushTaskIssue(taskIssuesById, taskId, {
        scope: "reviewer",
        taskId,
        message: "blocking reviewer 未返回该任务的审查结果",
      });
    }
  }

  return {
    taskIssuesById,
  };
}

function extractSectionLines(taskToml: string, sectionName: string): string[] {
  const lines = taskToml.split(/\r?\n/);
  const sectionLines: string[] = [];
  let inSection = false;

  for (const line of lines) {
    const trimmed = line.trim();
    if (/^\[[^\]]+\]$/.test(trimmed)) {
      if (trimmed === `[${sectionName}]`) {
        inSection = true;
        continue;
      }
      if (inSection) {
        break;
      }
    }

    if (inSection) {
      sectionLines.push(line);
    }
  }

  return sectionLines;
}

function parseTomlStringArray(rawValue: string): string[] | null {
  const trimmed = rawValue.trim();
  if (!trimmed.startsWith("[") || !trimmed.endsWith("]")) {
    return null;
  }

  const values: string[] = [];
  const valuePattern = /"([^"]*)"/g;
  for (const match of trimmed.matchAll(valuePattern)) {
    values.push(match[1] ?? "");
  }
  return values;
}

function parseTaskSection(taskToml: string, sectionName: string): ParsedTaskSection {
  const stringValues = new Map<string, string>();
  const arrayValues = new Map<string, string[]>();
  const numberValues = new Map<string, number>();
  const lines = extractSectionLines(taskToml, sectionName);

  let pendingArrayKey: string | null = null;
  let pendingArrayValue = "";

  for (const line of lines) {
    const trimmed = line.trim();
    if (!trimmed || trimmed.startsWith("#")) {
      continue;
    }

    if (pendingArrayKey) {
      pendingArrayValue += trimmed;
      if (trimmed.includes("]")) {
        const parsed = parseTomlStringArray(pendingArrayValue);
        if (parsed) {
          arrayValues.set(pendingArrayKey, parsed);
        }
        pendingArrayKey = null;
        pendingArrayValue = "";
      }
      continue;
    }

    const entryMatch = trimmed.match(/^([A-Za-z0-9_]+)\s*=\s*(.+)$/);
    if (!entryMatch) {
      continue;
    }

    const [, key, rawValue] = entryMatch;
    const value = rawValue.trim();
    const stringMatch = value.match(/^"([^"]*)"$/);
    if (stringMatch) {
      stringValues.set(key, stringMatch[1] ?? "");
      continue;
    }

    if (value.startsWith("[")) {
      if (value.includes("]")) {
        const parsed = parseTomlStringArray(value);
        if (parsed) {
          arrayValues.set(key, parsed);
        }
      } else {
        pendingArrayKey = key;
        pendingArrayValue = value;
      }
      continue;
    }

    const numeric = Number(value);
    if (Number.isFinite(numeric)) {
      numberValues.set(key, numeric);
    }
  }

  return {
    stringValues,
    arrayValues,
    numberValues,
  };
}

function isPrivateRegistryHost(host: string): boolean {
  if (host === "localhost" || host.endsWith(".local") || host.endsWith(".internal")) {
    return true;
  }

  if (host.includes(":")) {
    return true;
  }

  return (
    /^127\./.test(host) ||
    /^10\./.test(host) ||
    /^192\.168\./.test(host) ||
    /^169\.254\./.test(host) ||
    /^172\.(1[6-9]|2\d|3[0-1])\./.test(host)
  );
}

function collectDockerfileInstructions(dockerfile: string): string[] {
  const instructions: string[] = [];
  let currentInstruction = "";

  for (const rawLine of dockerfile.split(/\r?\n/)) {
    const trimmed = rawLine.trim();
    if (!trimmed || trimmed.startsWith("#")) {
      continue;
    }

    const withoutTrailingContinuation = trimmed.endsWith("\\")
      ? trimmed.slice(0, -1).trimEnd()
      : trimmed;
    currentInstruction = currentInstruction.length === 0
      ? withoutTrailingContinuation
      : `${currentInstruction} ${withoutTrailingContinuation}`.trim();

    if (trimmed.endsWith("\\")) {
      continue;
    }

    instructions.push(currentInstruction);
    currentInstruction = "";
  }

  if (currentInstruction.length > 0) {
    instructions.push(currentInstruction);
  }

  return instructions;
}

function normalizeDockerToken(token: string): string {
  return token.trim().replace(/^['"]|['"]$/g, "");
}

function isBuildContextRootToken(token: string): boolean {
  const normalized = normalizeDockerToken(token);
  return normalized === "." || normalized === "./";
}

function isRootDestinationToken(token: string): boolean {
  const normalized = normalizeDockerToken(token);
  return normalized === "/root" || normalized === "/root/";
}

function isSkillsSourceToken(token: string): boolean {
  const normalized = normalizeDockerToken(token);
  return normalized === "skills" || normalized === "./skills";
}

type ParsedCopyAddInstruction = {
  keyword: "COPY" | "ADD";
  fromOtherStage: boolean;
  sources: string[];
  destination: string;
};

function parseCopyAddInstruction(instruction: string): ParsedCopyAddInstruction | null {
  const match = instruction.match(/^\s*(COPY|ADD)\b\s*(.*)$/i);
  if (!match) {
    return null;
  }

  const keyword = (match[1] ?? "").toUpperCase() as "COPY" | "ADD";
  const rest = (match[2] ?? "").trim();
  const jsonStart = rest.indexOf("[");
  if (jsonStart >= 0) {
    const flagsPart = rest.slice(0, jsonStart).trim();
    const jsonPart = rest.slice(jsonStart).trim();

    try {
      const parsed = JSON.parse(jsonPart);
      if (!Array.isArray(parsed) || parsed.length < 2 || parsed.some((value) => typeof value !== "string")) {
        return null;
      }

      return {
        keyword,
        fromOtherStage: /(?:^|\s)--from=\S+/i.test(flagsPart),
        sources: parsed.slice(0, -1) as string[],
        destination: parsed[parsed.length - 1] as string,
      };
    } catch {
      return null;
    }
  }

  const tokens = rest.split(/\s+/).filter((token) => token.length > 0);
  const sourcesAndDestination: string[] = [];
  let fromOtherStage = false;

  for (const token of tokens) {
    if (/^--from=/i.test(token)) {
      fromOtherStage = true;
      continue;
    }
    if (token.startsWith("--")) {
      continue;
    }
    sourcesAndDestination.push(token);
  }

  if (sourcesAndDestination.length < 2) {
    return null;
  }

  return {
    keyword,
    fromOtherStage,
    sources: sourcesAndDestination.slice(0, -1),
    destination: sourcesAndDestination[sourcesAndDestination.length - 1] ?? "",
  };
}

function validateDockerfileLayoutRules(dockerfile: string): string[] {
  const issues = new Set<string>();
  const instructions = collectDockerfileInstructions(dockerfile);

  if (!instructions.some((instruction) => /^\s*WORKDIR\b/i.test(instruction))) {
    issues.add("environment/Dockerfile 必须显式声明 WORKDIR");
  }

  for (const instruction of instructions) {
    const parsedInstruction = parseCopyAddInstruction(instruction);
    if (!parsedInstruction) {
      continue;
    }

    const { fromOtherStage, sources, destination } = parsedInstruction;
    const normalizedDestination = normalizeDockerToken(destination);

    if (
      !fromOtherStage &&
      sources.length === 1 &&
      isBuildContextRootToken(sources[0] ?? "") &&
      isRootDestinationToken(destination)
    ) {
      issues.add(
        "environment/Dockerfile 存在宽泛 COPY/ADD，会把整个 environment/ 上下文一并带入容器，属于实验污染",
      );
    }

    if (
      sources.length === 1 &&
      isSkillsSourceToken(sources[0] ?? "") &&
      !AGENT_SKILL_DESTINATION_ALLOWLIST.has(normalizedDestination)
    ) {
      issues.add(
        `environment/Dockerfile 把 skills 复制到了普通运行时路径 ${normalizedDestination}；这会把 skill 内容暴露到非 agent skill 路径，破坏有技能/无技能对照`,
      );
    }
  }

  return [...issues];
}

export function validateDockerfileBaseImages(dockerfile: string): string[] {
  const issues: string[] = [];
  const stageAliases = new Set<string>();
  const fromLines = collectDockerfileInstructions(dockerfile);

  for (const line of fromLines) {
    const match = line.match(/^\s*FROM(?:\s+--platform=\S+)?\s+([^\s]+)(?:\s+AS\s+([A-Za-z0-9._-]+))?/i);
    if (!match) {
      continue;
    }

    const imageRef = match[1] ?? "";
    const stageAlias = match[2]?.toLowerCase();
    const normalizedRef = imageRef.toLowerCase();
    if (normalizedRef === "scratch") {
      if (stageAlias) {
        stageAliases.add(stageAlias);
      }
      continue;
    }

    if (stageAliases.has(normalizedRef)) {
      if (stageAlias) {
        stageAliases.add(stageAlias);
      }
      continue;
    }

    if (!imageRef.includes("/")) {
      if (stageAlias) {
        stageAliases.add(stageAlias);
      }
      continue;
    }

    const firstSegment = imageRef.split("/")[0] ?? imageRef;
    const looksLikeRegistry =
      firstSegment === "localhost" || firstSegment.includes(".") || firstSegment.includes(":");

    if (!looksLikeRegistry) {
      if (stageAlias) {
        stageAliases.add(stageAlias);
      }
      continue;
    }

    if (isPrivateRegistryHost(firstSegment)) {
      issues.push(`Dockerfile 使用了私有或本地 registry: ${firstSegment}`);
    } else if (!PUBLIC_REGISTRY_ALLOWLIST.has(firstSegment.toLowerCase())) {
      issues.push(`Dockerfile 使用了未允许的 registry: ${firstSegment}`);
    }

    if (stageAlias) {
      stageAliases.add(stageAlias);
    }
  }

  return issues;
}

export async function validateDraftStatic(
  draftDir: string,
  plan: DerivedTaskPlan,
  unit: GenerationUnit,
): Promise<ValidationIssue[]> {
  const issues: ValidationIssue[] = [];
  const skillsDir = path.join(draftDir, "environment", "skills");
  const requiredFiles = [
    "plan.json",
    "task.toml",
    "instruction.md",
    path.join("environment", "Dockerfile"),
    path.join("solution", "solve.sh"),
    path.join("tests", "test.sh"),
    path.join("tests", "test_outputs.py"),
  ];

  for (const relativePath of requiredFiles) {
    if (!(await pathExists(path.join(draftDir, relativePath)))) {
      issues.push({
        scope: "static",
        taskId: plan.derivedTaskId,
        message: `缺少必备文件: ${relativePath}`,
      });
    }
  }

  const planJsonPath = path.join(draftDir, "plan.json");
  if (await pathExists(planJsonPath)) {
    try {
      const planJson = JSON.parse(await readText(planJsonPath)) as Partial<DerivedTaskPlan>;
      if (planJson.derivedTaskId !== plan.derivedTaskId) {
        issues.push({
          scope: "static",
          taskId: plan.derivedTaskId,
          message: `plan.json 中的 derivedTaskId=${planJson.derivedTaskId ?? "missing"} 与目录名不一致`,
        });
      }
    } catch {
      issues.push({
        scope: "static",
        taskId: plan.derivedTaskId,
        message: "plan.json 不是合法 JSON",
      });
    }
  }

  if (!(await pathExists(skillsDir))) {
    issues.push({
      scope: "static",
      taskId: plan.derivedTaskId,
      message: "缺少 environment/skills 目录",
    });
  } else {
    const skillDirNames = (await fs.readdir(skillsDir, { withFileTypes: true }))
      .filter((entry) => entry.isDirectory())
      .map((entry) => entry.name)
      .sort((a, b) => a.localeCompare(b));
    const expectedSkillDirNames =
      unit.skillMode === "per-skill"
        ? unit.targetSkill?.dirName
          ? [unit.targetSkill.dirName]
          : []
        : unit.inputSkills.map((skill) => skill.dirName).sort((a, b) => a.localeCompare(b));
    const missingSkillDirs = expectedSkillDirNames.filter((dirName) => !skillDirNames.includes(dirName));
    const unexpectedSkillDirs = skillDirNames.filter((dirName) => !expectedSkillDirNames.includes(dirName));

    if (plan.skillMode === "per-skill" && skillDirNames.length !== 1) {
      issues.push({
        scope: "static",
        taskId: plan.derivedTaskId,
        message: `per-skill 任务必须且只能包含 1 个 skill，当前检测到 ${skillDirNames.length} 个`,
      });
    }

    if (missingSkillDirs.length > 0) {
      issues.push({
        scope: "static",
        taskId: plan.derivedTaskId,
        message: `environment/skills 缺少预期 skill 目录: ${missingSkillDirs.join(", ")}`,
      });
    }

    if (unexpectedSkillDirs.length > 0) {
      issues.push({
        scope: "static",
        taskId: plan.derivedTaskId,
        message: `environment/skills 存在非预期 skill 目录: ${unexpectedSkillDirs.join(", ")}`,
      });
    }

    for (const visibleSkill of getVisibleSkills(unit)) {
      const draftSkillDir = path.join(skillsDir, visibleSkill.dirName);
      if (!(await pathExists(draftSkillDir))) {
        continue;
      }
      const immutableSkillIssues = await compareDirectoryContent(visibleSkill.sourceDir, draftSkillDir);
      for (const immutableSkillIssue of immutableSkillIssues) {
        issues.push({
          scope: "static",
          taskId: plan.derivedTaskId,
          message: `environment/skills/${visibleSkill.dirName} 与输入 skill 不一致: ${immutableSkillIssue}`,
        });
      }
    }
  }

  const taskTomlPath = path.join(draftDir, "task.toml");
  if (await pathExists(taskTomlPath)) {
    const taskToml = await readText(taskTomlPath);
    const metadata = parseTaskSection(taskToml, "metadata");
    const environment = parseTaskSection(taskToml, "environment");
    const metadataId = metadata.stringValues.get("id");
    const metadataName = metadata.stringValues.get("name") ?? "";
    const metadataDescription = metadata.stringValues.get("description");
    const metadataAuthorName = metadata.stringValues.get("author_name");
    const metadataAuthorEmail = metadata.stringValues.get("author_email");
    const metadataDifficulty = metadata.stringValues.get("difficulty");
    const metadataCategory = metadata.stringValues.get("category");
    const metadataSourceTemplateId = metadata.stringValues.get("source_template_id");
    const metadataTaskRole = metadata.stringValues.get("task_role");
    const metadataTags = metadata.arrayValues.get("tags");

    if (metadataId !== plan.derivedTaskId) {
      issues.push({
        scope: "static",
        taskId: plan.derivedTaskId,
        message: `task.toml metadata.id=${metadataId ?? "missing"} 与目录名不一致`,
      });
    }

    if (!metadataName.includes(buildTaskDisplayName(plan))) {
      issues.push({
        scope: "static",
        taskId: plan.derivedTaskId,
        message: `task.toml metadata.name 未显式包含 ${buildTaskDisplayName(plan)}`,
      });
    }

    if (containsCjkCharacters(metadataName)) {
      issues.push({
        scope: "static",
        taskId: plan.derivedTaskId,
        message: "task.toml metadata.name 必须使用英文描述，不能包含中文",
      });
    }

    const nonEmptyMetadataFields = [
      ["description", metadataDescription],
      ["author_name", metadataAuthorName],
      ["author_email", metadataAuthorEmail],
      ["difficulty", metadataDifficulty],
      ["category", metadataCategory],
    ] as const;

    for (const [fieldName, value] of nonEmptyMetadataFields) {
      if (!value || value.trim().length === 0) {
        issues.push({
          scope: "static",
          taskId: plan.derivedTaskId,
          message: `task.toml metadata.${fieldName} 缺失或为空`,
        });
      }
    }

    if (metadataDescription && containsCjkCharacters(metadataDescription)) {
      issues.push({
        scope: "static",
        taskId: plan.derivedTaskId,
        message: "task.toml metadata.description 必须使用英文描述，不能包含中文",
      });
    }

    if (metadataSourceTemplateId !== plan.templateId) {
      issues.push({
        scope: "static",
        taskId: plan.derivedTaskId,
        message: `task.toml metadata.source_template_id=${metadataSourceTemplateId ?? "missing"} 与 templateId 不一致`,
      });
    }

    if (metadataTaskRole && metadataTaskRole !== "task") {
      issues.push({
        scope: "static",
        taskId: plan.derivedTaskId,
        message: `task.toml metadata.task_role=${metadataTaskRole} 已废弃；如果保留只能是 task`,
      });
    }

    if (!metadataTags || metadataTags.length === 0) {
      issues.push({
        scope: "static",
        taskId: plan.derivedTaskId,
        message: "task.toml metadata.tags 缺失或为空数组",
      });
    }

    const expectedEnvironment = new Map<string, number>([
      ["cpus", 2],
      ["memory_mb", 2048],
      ["storage_mb", 5120],
      ["gpus", 0],
    ]);

    for (const [key, expected] of expectedEnvironment) {
      const actual = environment.numberValues.get(key);
      if (actual !== expected) {
        issues.push({
          scope: "static",
          taskId: plan.derivedTaskId,
          message: `task.toml [environment].${key}=${actual ?? "missing"}，期望 ${expected}`,
        });
      }
    }
  }

  const instructionPath = path.join(draftDir, "instruction.md");
  if (await pathExists(instructionPath)) {
    const instruction = await readText(instructionPath);
    if (containsCjkCharacters(instruction)) {
      issues.push({
        scope: "static",
        taskId: plan.derivedTaskId,
        message: "instruction.md 必须使用英文描述，不能包含中文",
      });
    }
  }

  const dockerfilePath = path.join(draftDir, "environment", "Dockerfile");
  if (await pathExists(dockerfilePath)) {
    const dockerfile = await readText(dockerfilePath);
    if (!dockerfile.includes("COPY skills /root/.codex/skills")) {
      issues.push({
        scope: "static",
        taskId: plan.derivedTaskId,
        message: "environment/Dockerfile 未保留 COPY skills /root/.codex/skills",
      });
    }

    for (const dockerIssue of validateDockerfileLayoutRules(dockerfile)) {
      issues.push({
        scope: "static",
        taskId: plan.derivedTaskId,
        message: dockerIssue,
      });
    }

    for (const dockerIssue of validateDockerfileBaseImages(dockerfile)) {
      issues.push({
        scope: "static",
        taskId: plan.derivedTaskId,
        message: dockerIssue,
      });
    }
  }

  const couplingScanPaths = [
    ...(await listFilesRecursive(path.join(draftDir, "solution"))),
    ...(await listFilesRecursive(path.join(draftDir, "tests"))),
  ];

  for (const fullPath of couplingScanPaths) {
    const relativePath = path.relative(draftDir, fullPath);
    const detections = detectSkillRuntimeCoupling(await readText(fullPath), unit);
    if (detections.length === 0) {
      continue;
    }

    issues.push({
      scope: "static",
      taskId: plan.derivedTaskId,
      message: `${relativePath} 直接依赖 skill 模块或路径（${detections.join("、")}）；参考解与 verifier 必须与 skill 解耦`,
    });
  }

  return issues;
}

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

function readEnvValue(env: NodeJS.ProcessEnv, key: string): string | null {
  const raw = env[key];
  if (typeof raw !== "string") {
    return null;
  }

  const trimmed = raw.trim();
  return trimmed.length > 0 ? trimmed : null;
}

export function resolveRuntimeEnvironment(env: NodeJS.ProcessEnv = process.env): RuntimeEnvironment {
  const rawValue = readEnvValue(env, "CODEX_TASK_BUILDER_RUNTIME_ENV");
  if (!rawValue) {
    return "e2b";
  }

  const normalized = rawValue.toLowerCase();
  if (normalized === "e2b" || normalized === "daytona" || normalized === "docker") {
    return normalized;
  }

  throw new Error(`不支持的 CODEX_TASK_BUILDER_RUNTIME_ENV: ${rawValue}；仅支持 e2b、daytona 或 docker`);
}

export function buildHarborRuntimeCommand(options: {
  taskDir: string;
  logsDir: string;
  jobName: string;
  runtimeEnvironment: RuntimeEnvironment;
}): string[] {
  return [
    "harbor",
    "run",
    "-p",
    options.taskDir,
    "-a",
    "oracle",
    "-e",
    options.runtimeEnvironment,
    "--force-build",
    "--jobs-dir",
    options.logsDir,
    "--job-name",
    options.jobName,
  ];
}

function shellEscape(value: string): string {
  return `'${value.replace(/'/g, `'\"'\"'`)}'`;
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

  candidates.sort((a, b) => b.mtimeMs - a.mtimeMs);
  return candidates[0]?.path ?? null;
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

export async function runRuntimePreflight(
  runtimeEnvironment: RuntimeEnvironment,
  env: NodeJS.ProcessEnv = process.env,
  commandRunner: CommandRunner = runCommand,
): Promise<RuntimePreflightResult> {
  const details: string[] = [];

  const harborCheck = await commandRunner("bash", ["-lc", "command -v harbor >/dev/null 2>&1"], { env });
  if (harborCheck.code !== 0) {
    return {
      ok: false,
      summary: "当前环境未检测到 harbor CLI",
      details: ["command -v harbor 失败"],
    };
  }

  const harborVersion = await commandRunner("bash", ["-lc", "harbor --version"], { env });
  if (harborVersion.code !== 0) {
    const summary = compactOutputSummary(`${harborVersion.stdout}\n${harborVersion.stderr}`);
    return {
      ok: false,
      summary: `harbor --version 失败: ${summary}`,
      details: ["harbor --version 返回非零退出码", summary],
    };
  }

  details.push(`runtime environment: ${runtimeEnvironment}`);
  details.push(`harbor --version: ${compactOutputSummary(`${harborVersion.stdout}\n${harborVersion.stderr}`)}`);

  if (runtimeEnvironment === "e2b") {
    if (!readEnvValue(env, "E2B_API_KEY")) {
      return {
        ok: false,
        summary: "当前环境未设置 E2B_API_KEY",
        details: ["E2B_API_KEY 缺失或为空"],
      };
    }

    return {
      ok: true,
      summary: "harbor + e2b preflight 通过",
      details,
    };
  }

  if (runtimeEnvironment === "daytona") {
    if (!readEnvValue(env, "DAYTONA_API_KEY")) {
      return {
        ok: false,
        summary: "当前环境未设置 DAYTONA_API_KEY",
        details: ["DAYTONA_API_KEY 缺失或为空"],
      };
    }

    return {
      ok: true,
      summary: "harbor + daytona preflight 通过",
      details,
    };
  }

  const dockerCheck = await commandRunner("bash", ["-lc", "command -v docker >/dev/null 2>&1"], { env });
  if (dockerCheck.code !== 0) {
    return {
      ok: false,
      summary: "当前环境未检测到 docker",
      details: ["command -v docker 失败"],
    };
  }

  const dockerInfo = await commandRunner("docker", ["info"], { env });
  if (dockerInfo.code !== 0) {
    const summary = compactOutputSummary(`${dockerInfo.stdout}\n${dockerInfo.stderr}`);
    return {
      ok: false,
      summary: `docker info 失败: ${summary}`,
      details: ["docker info 返回非零退出码", summary],
    };
  }

  return {
    ok: true,
    summary: "harbor + docker preflight 通过",
    details,
  };
}

export async function runRuntimeValidation(
  workspace: RuntimeWorkspace,
  plan: DerivedTaskPlan,
  runtimeEnvironment: RuntimeEnvironment,
  cycle: number,
  attemptIndex: number,
  draftTaskDir: string,
  env: NodeJS.ProcessEnv = process.env,
  signal?: AbortSignal,
  options: {
    logsDir?: string;
    jobNamePrefix?: string;
  } = {},
): Promise<RuntimeValidationResult> {
  const taskRuntimeRoot = path.join(workspace.artifactsDir, "runtime", plan.derivedTaskId);
  const logsDir = options.logsDir ?? path.join(taskRuntimeRoot, `cycle-${cycle}-attempt-${attemptIndex}`);
  const logFilePath = path.join(logsDir, "harbor-run.log");
  const runtimeLogIndexPath = path.join(logsDir, "log-index.json");
  const jobNamePrefix = options.jobNamePrefix ?? "harbor-oracle";
  const jobName = `${jobNamePrefix}-${slugify(workspace.runId)}-${slugify(plan.derivedTaskId)}-cycle-${cycle}-attempt-${attemptIndex}`;
  const command = buildHarborRuntimeCommand({
    taskDir: draftTaskDir,
    logsDir,
    jobName,
    runtimeEnvironment,
  });

  await ensureDir(logsDir);

  const baseEvidence: RuntimeEvidence = {
    logsDir,
    runtimeDir: logsDir,
    runtimeLogRoot: logsDir,
    runtimeLogIndexPath,
    logFilePath,
    jobDir: path.join(logsDir, jobName),
    command,
    summary: "未开始执行",
  };
  await writeRuntimeLogIndex(runtimeLogIndexPath, [
    { label: "runtime-dir", path: logsDir },
    { label: "harbor-run-log", path: logFilePath },
    { label: "job-dir", path: baseEvidence.jobDir },
  ]);

  const preflight = await runRuntimePreflight(runtimeEnvironment, env);
  if (!preflight.ok) {
    return {
      passed: false,
      issues: [runtimeIssue(plan.derivedTaskId, preflight.summary)],
      failureKind: "harbor-preflight",
      evidence: {
        ...baseEvidence,
        summary: preflight.summary,
      },
    };
  }

  const shellCommand = command.map(shellEscape).join(" ");
  const runResult = await runStreamingCommand("bash", ["-lc", shellCommand], {
    cwd: workspace.rootDir,
    env,
    logFilePath,
    heartbeatIntervalMs: 60_000,
    onHeartbeat: () => {
      console.log(`[oracle] ${plan.derivedTaskId} 仍在运行，继续等待`);
    },
    onStdout: (chunk) => {
      process.stdout.write(chunk);
    },
    onStderr: (chunk) => {
      process.stderr.write(chunk);
    },
    signal,
  });

  const jobDir = path.join(logsDir, jobName);
  const combinedOutput = `${runResult.stdout}\n${runResult.stderr}`;
  const summary = compactOutputSummary(combinedOutput);
  const trialResultPath = await findLatestTrialResultPath(jobDir);
  const trialDir = trialResultPath ? path.dirname(trialResultPath) : undefined;
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
  let stableResultPath: string | undefined;
  if (trialResultPath) {
    stableResultPath = path.join(logsDir, "result.json");
    await copyFile(trialResultPath, stableResultPath);
  }

  const baseRuntimeEvidence: RuntimeEvidence = {
    logsDir,
    runtimeDir: logsDir,
    runtimeLogRoot: logsDir,
    runtimeLogIndexPath,
    logFilePath,
    jobDir,
    jobLogPath,
    trialDir,
    trialLogPath,
    resultPath: stableResultPath,
    verifierStdoutPath,
    rewardPath,
    artifactManifestPath,
    command,
    summary,
  };
  await writeRuntimeLogIndex(runtimeLogIndexPath, [
    { label: "runtime-dir", path: logsDir },
    { label: "harbor-run-log", path: logFilePath },
    { label: "job-dir", path: jobDir },
    { label: "job-log", path: jobLogPath },
    ...(trialDir ? [{ label: "trial-dir", path: trialDir }] : []),
    ...(trialLogPath ? [{ label: "trial-log", path: trialLogPath }] : []),
    ...(trialResultPath ? [{ label: "trial-result", path: trialResultPath }] : []),
    ...(stableResultPath ? [{ label: "stable-result", path: stableResultPath }] : []),
    ...(verifierStdoutPath ? [{ label: "verifier-stdout", path: verifierStdoutPath }] : []),
    ...(rewardPath ? [{ label: "reward-file", path: rewardPath }] : []),
    ...(artifactManifestPath ? [{ label: "artifact-manifest", path: artifactManifestPath }] : []),
  ]);

  if (!trialResultPath) {
    return {
      passed: false,
      issues: [runtimeIssue(plan.derivedTaskId, `harbor run 未产出可解析的 result.json: ${summary}`)],
      failureKind: "harbor-task",
      evidence: baseRuntimeEvidence,
    };
  }

  let trialResult: unknown;
  try {
    trialResult = JSON.parse(await readText(trialResultPath)) as unknown;
  } catch {
    return {
      passed: false,
      issues: [runtimeIssue(plan.derivedTaskId, "harbor trial result.json 解析失败，详见 harbor-run.log")],
      failureKind: "harbor-task",
      evidence: baseRuntimeEvidence,
    };
  }

  if (!trialResult || typeof trialResult !== "object") {
    return {
      passed: false,
      issues: [runtimeIssue(plan.derivedTaskId, "harbor trial result.json 结构异常")],
      failureKind: "harbor-task",
      evidence: baseRuntimeEvidence,
    };
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
    return {
      passed: false,
      issues: [runtimeIssue(plan.derivedTaskId, `harbor oracle 运行异常: ${exceptionType}: ${exceptionMessage}`)],
      failureKind: "harbor-task",
      evidence: baseRuntimeEvidence,
    };
  }

  const verifierResult =
    resultRecord.verifier_result && typeof resultRecord.verifier_result === "object"
      ? (resultRecord.verifier_result as Record<string, unknown>)
      : null;
  const reward = extractPrimaryReward(verifierResult?.rewards);

  if (reward === null) {
    return {
      passed: false,
      issues: [runtimeIssue(plan.derivedTaskId, "harbor verifier 未产出 reward（reward.txt/reward.json）")],
      failureKind: "harbor-task",
      evidence: {
        ...baseRuntimeEvidence,
        reward,
      },
    };
  }

  if (reward < 1.0) {
    return {
      passed: false,
      issues: [runtimeIssue(plan.derivedTaskId, `harbor verifier reward=${reward} < 1.0`)],
      failureKind: "harbor-reward",
      evidence: {
        ...baseRuntimeEvidence,
        reward,
      },
    };
  }

  if (runResult.code !== 0) {
    return {
      passed: false,
      issues: [runtimeIssue(plan.derivedTaskId, `harbor run 返回非零退出码: ${summary}`)],
      failureKind: "harbor-task",
      evidence: {
        ...baseRuntimeEvidence,
        reward,
      },
    };
  }

  return {
    passed: true,
    issues: [],
    evidence: {
      ...baseRuntimeEvidence,
      reward,
      summary: `reward=${reward}`,
    },
  };
}
