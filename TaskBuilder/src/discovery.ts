import { promises as fs } from "node:fs";
import path from "node:path";
import { TEMPLATE_ROOT, listDirectories, pathExists, readText } from "./utils.js";

export type TaskMetadata = {
  id?: string;
  name?: string;
  difficulty?: string;
  category?: string;
  tags: string[];
};

export type SkillInfo = {
  name: string;
  dirName: string;
  relativeDir: string;
  sourceDir: string;
  skillMdPath: string;
};

export type SkillMode = "all" | "per-skill";

export type PublishedTaskInfo = {
  derivedTaskId: string;
  taskOrdinal: number;
  acceptanceKind?: "pf_success" | "oracle_fallback_success";
  taskDir: string;
  planPath: string;
  instructionPath: string;
  taskTomlPath: string;
  testOutputsPath: string;
  environmentDir: string;
};

export type TaskTemplate = {
  templateId: string;
  templateRelativePath: string;
  sourceDir: string;
  taskTomlPath: string;
  instructionPath: string;
  environmentDir: string;
  solutionDir: string;
  testsDir: string;
  templateSkillsDir: string;
  metadata: TaskMetadata;
  referenceSkills: SkillInfo[];
};

export type GenerationUnit = {
  template: TaskTemplate;
  inputSkills: SkillInfo[];
  skillMode: SkillMode;
  targetSkill: SkillInfo | null;
  scopeSlug: string;
  scopeLabel: string;
  taskCount: number;
  pendingTaskOrdinals: number[];
  finalFamilyDir: string;
  publishedTasks: PublishedTaskInfo[];
};

const REQUIRED_TEMPLATE_ENTRIES = ["task.toml", "instruction.md", "environment", "tests", "solution"] as const;

function extractTomlValue(text: string, key: string): string | undefined {
  const match = text.match(new RegExp(`^\\s*${key}\\s*=\\s*"([^"]+)"`, "m"));
  return match?.[1];
}

function extractTomlTags(text: string): string[] {
  const match = text.match(/^\s*tags\s*=\s*\[(.*?)\]/ms);
  if (!match) {
    return [];
  }
  return match[1]
    .split(",")
    .map((part) => part.trim().replace(/^"|"$/g, ""))
    .filter(Boolean);
}

function normalizeRelativePath(relativePath: string): string {
  return relativePath
    .split(/[\\/]+/u)
    .map((part) => part.trim())
    .filter(Boolean)
    .join("/");
}

export function templateIdFromRelativePath(relativePath: string): string {
  return normalizeRelativePath(relativePath).replaceAll("/", "__");
}

async function parseSkillName(skillMdPath: string, fallback: string): Promise<string> {
  const raw = await readText(skillMdPath);
  const frontmatterName = raw.match(/^name:\s*"?(.*?)"?$/m)?.[1];
  const yamlFrontmatterName = raw.match(/^---[\s\S]*?^name:\s*"?(.*?)"?$/m)?.[1];
  return (frontmatterName ?? yamlFrontmatterName ?? fallback).trim();
}

async function discoverSkills(skillsDir: string): Promise<SkillInfo[]> {
  if (!(await pathExists(skillsDir))) {
    return [];
  }

  const dirs = await listDirectories(skillsDir);
  const skills: SkillInfo[] = [];
  for (const dir of dirs) {
    const skillMdPath = path.join(dir, "SKILL.md");
    if (!(await pathExists(skillMdPath))) {
      continue;
    }
    const dirName = path.basename(dir);
    skills.push({
      name: await parseSkillName(skillMdPath, dirName),
      dirName,
      relativeDir: dirName,
      sourceDir: dir,
      skillMdPath,
    });
  }

  return skills.sort((a, b) => a.name.localeCompare(b.name));
}

async function assertTemplateShape(templateDir: string): Promise<void> {
  const missingEntries: string[] = [];
  for (const entry of REQUIRED_TEMPLATE_ENTRIES) {
    if (!(await pathExists(path.join(templateDir, entry)))) {
      missingEntries.push(entry);
    }
  }
  if (missingEntries.length > 0) {
    throw new Error(`template 缺少必需内容: ${missingEntries.join(", ")} (${templateDir})`);
  }
}

export async function discoverTaskTemplate(
  templateRelativePath: string,
  templateRoot = TEMPLATE_ROOT,
): Promise<TaskTemplate> {
  const normalizedRelativePath = normalizeRelativePath(templateRelativePath);
  if (!normalizedRelativePath) {
    throw new Error("template 路径不能为空");
  }

  const sourceDir = path.join(templateRoot, normalizedRelativePath);
  await assertTemplateShape(sourceDir);

  const taskTomlPath = path.join(sourceDir, "task.toml");
  const instructionPath = path.join(sourceDir, "instruction.md");
  const environmentDir = path.join(sourceDir, "environment");
  const solutionDir = path.join(sourceDir, "solution");
  const testsDir = path.join(sourceDir, "tests");
  const templateSkillsDir = path.join(environmentDir, "skills");

  const taskToml = await readText(taskTomlPath);
  const metadata: TaskMetadata = {
    id: extractTomlValue(taskToml, "id"),
    name: extractTomlValue(taskToml, "name"),
    difficulty: extractTomlValue(taskToml, "difficulty"),
    category: extractTomlValue(taskToml, "category"),
    tags: extractTomlTags(taskToml),
  };

  return {
    templateId: templateIdFromRelativePath(normalizedRelativePath),
    templateRelativePath: normalizedRelativePath,
    sourceDir,
    taskTomlPath,
    instructionPath,
    environmentDir,
    solutionDir,
    testsDir,
    templateSkillsDir,
    metadata,
    referenceSkills: await discoverSkills(templateSkillsDir),
  };
}

async function discoverTemplateDirs(rootDir: string, baseDir = rootDir): Promise<string[]> {
  if (!(await pathExists(rootDir))) {
    return [];
  }

  const entries = await fs.readdir(rootDir, { withFileTypes: true });
  const hasAllRequiredEntries = REQUIRED_TEMPLATE_ENTRIES.every((entry) =>
    entries.some((current) => current.name === entry),
  );
  if (hasAllRequiredEntries) {
    return [path.relative(baseDir, rootDir)];
  }

  const templateDirs: string[] = [];
  for (const entry of entries.sort((a, b) => a.name.localeCompare(b.name))) {
    if (!entry.isDirectory()) {
      continue;
    }
    templateDirs.push(...(await discoverTemplateDirs(path.join(rootDir, entry.name), baseDir)));
  }
  return templateDirs;
}

export async function discoverTaskTemplates(templateRoot = TEMPLATE_ROOT): Promise<TaskTemplate[]> {
  const relativePaths = await discoverTemplateDirs(templateRoot);
  const templates: TaskTemplate[] = [];
  for (const relativePath of relativePaths) {
    templates.push(await discoverTaskTemplate(relativePath, templateRoot));
  }
  return templates.sort((left, right) => left.templateId.localeCompare(right.templateId));
}

export async function discoverInputSkill(skillDir: string): Promise<SkillInfo> {
  const normalizedDir = path.resolve(skillDir);
  const skillMdPath = path.join(normalizedDir, "SKILL.md");
  if (!(await pathExists(skillMdPath))) {
    throw new Error(`skill 目录缺少 SKILL.md: ${normalizedDir}`);
  }

  const dirName = path.basename(normalizedDir);
  return {
    name: await parseSkillName(skillMdPath, dirName),
    dirName,
    relativeDir: dirName,
    sourceDir: normalizedDir,
    skillMdPath,
  };
}

export async function discoverInputSkills(skillDirs: string[]): Promise<SkillInfo[]> {
  const skills = await Promise.all(skillDirs.map((skillDir) => discoverInputSkill(skillDir)));
  const seenDirNames = new Set<string>();
  for (const skill of skills) {
    if (seenDirNames.has(skill.dirName)) {
      throw new Error(`重复的 skill 目录 basename: ${skill.dirName}；当前接口要求每个 --skill-dir 的 basename 唯一`);
    }
    seenDirNames.add(skill.dirName);
  }
  return skills;
}

export function buildGenerationUnits(
  template: TaskTemplate,
  inputSkills: SkillInfo[],
  options: {
    skillMode: SkillMode;
    taskCount: number;
  },
): GenerationUnit[] {
  if (inputSkills.length === 0) {
    throw new Error(`template ${template.templateId} 没有输入 skills，无法生成任务`);
  }

  const counts = {
    taskCount: options.taskCount,
    pendingTaskOrdinals: Array.from({ length: Math.max(0, options.taskCount) }, (_, index) => index + 1),
    finalFamilyDir: "",
    publishedTasks: [] as PublishedTaskInfo[],
  };

  if (options.skillMode === "all") {
    return [
      {
        template,
        inputSkills,
        skillMode: options.skillMode,
        targetSkill: null,
        scopeSlug: "all-skills",
        scopeLabel: "All input skills",
        ...counts,
      },
    ];
  }

  return inputSkills.map((skill) => ({
    template,
    inputSkills: [skill],
    skillMode: options.skillMode,
    targetSkill: skill,
    scopeSlug: skill.dirName,
    scopeLabel: skill.name,
    ...counts,
  }));
}

export function getVisibleSkills(unit: GenerationUnit): SkillInfo[] {
  return unit.targetSkill ? [unit.targetSkill] : unit.inputSkills;
}

export async function collectEnvironmentAssetPaths(template: TaskTemplate): Promise<string[]> {
  const assets: string[] = [];

  async function walk(currentDir: string): Promise<void> {
    const entries = await fs.readdir(currentDir, { withFileTypes: true });
    for (const entry of entries) {
      const fullPath = path.join(currentDir, entry.name);
      if (fullPath.startsWith(template.templateSkillsDir)) {
        continue;
      }
      if (entry.isDirectory()) {
        await walk(fullPath);
      } else if (entry.isFile()) {
        assets.push(path.relative(template.environmentDir, fullPath));
      }
    }
  }

  if (await pathExists(template.environmentDir)) {
    await walk(template.environmentDir);
  }

  return assets.sort((a, b) => a.localeCompare(b));
}
