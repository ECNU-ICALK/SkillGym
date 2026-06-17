import { promises as fs } from "node:fs";
import path from "node:path";
import {
  assertPathWithinRoots,
  buildFinalRoot,
  buildRawRoot,
  copyDir,
  copyFile,
  DEFAULT_OUTPUT_ROOT,
  ensureDir,
  pathExists,
} from "./utils.js";

const MATERIALIZE_ALLOWLIST = [
  "task.toml",
  "instruction.md",
  "plan.json",
  "environment",
  "solution",
  "tests",
] as const;

export const ACCEPTANCE_KINDS = ["pf_success", "oracle_fallback_success"] as const;
export type AcceptanceKind = (typeof ACCEPTANCE_KINDS)[number];

export function buildAcceptanceFinalRoot(finalRoot: string, acceptanceKind: AcceptanceKind): string {
  return path.join(finalRoot, acceptanceKind);
}

async function copySelectedEntry(sourcePath: string, targetPath: string): Promise<void> {
  if (!(await pathExists(sourcePath))) {
    return;
  }

  const stat = await fs.stat(sourcePath);
  if (stat.isDirectory()) {
    await copyDir(sourcePath, targetPath);
    return;
  }

  if (stat.isFile()) {
    await copyFile(sourcePath, targetPath);
  }
}

export function buildMaterializedTaskDir(args: {
  targetRoot: string;
  templateId: string;
  scopeSlug: string;
  taskName: string;
}): string {
  return path.join(args.targetRoot, args.templateId, args.scopeSlug, args.taskName);
}

export function buildPublishedVariantTaskDir(args: {
  targetRoot: string;
  templateId: string;
  scopeSlug: string;
  taskName: string;
  variant: "with_skill" | "no_skill";
}): string {
  return buildMaterializedTaskDir({
    targetRoot: args.targetRoot,
    templateId: args.templateId,
    scopeSlug: args.scopeSlug,
    taskName: `${args.taskName}__${args.variant}`,
  });
}

export type MaterializeResult = {
  targetTaskDir: string;
  disposition: "created" | "existing";
};

export async function sanitizeAndCopyTask(args: {
  sourceDraftDir: string;
  templateId: string;
  scopeSlug: string;
  taskName: string;
  rawRoot?: string;
  targetRoot?: string;
}): Promise<MaterializeResult> {
  const outputRoot = DEFAULT_OUTPUT_ROOT;
  const targetRoot = args.targetRoot ?? buildFinalRoot(outputRoot);
  const rawRoot = args.rawRoot ?? buildRawRoot(outputRoot);
  const targetTaskDir = buildMaterializedTaskDir({
    targetRoot,
    templateId: args.templateId,
    scopeSlug: args.scopeSlug,
    taskName: args.taskName,
  });

  assertPathWithinRoots(args.sourceDraftDir, [rawRoot], "raw task");
  assertPathWithinRoots(
    targetTaskDir,
    [buildFinalRoot(outputRoot), targetRoot],
    "发布目标",
  );

  await ensureDir(path.dirname(targetTaskDir));
  if (await pathExists(targetTaskDir)) {
    return {
      targetTaskDir,
      disposition: "existing",
    };
  }

  await ensureDir(targetTaskDir);
  for (const relativePath of MATERIALIZE_ALLOWLIST) {
    await copySelectedEntry(path.join(args.sourceDraftDir, relativePath), path.join(targetTaskDir, relativePath));
  }

  return {
    targetTaskDir,
    disposition: "created",
  };
}
