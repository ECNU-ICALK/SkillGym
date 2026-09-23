import { promises as fs } from "node:fs";
import path from "node:path";
import { DEFAULT_OUTPUT_ROOT, ensureDir, writeText } from "./utils.js";

export type ManifestEntry = {
  timestamp: string;
  runId: string;
  templateId: string;
  phase: string;
  status: "started" | "completed" | "failed" | "skipped";
  derivedTaskId?: string;
  threadId?: string | null;
  draftDir?: string;
  publishedDir?: string;
  issues?: string[];
  metadata?: Record<string, unknown>;
};

export function buildManifestPath(outputRoot: string): string {
  return path.join(outputRoot, "manifest.jsonl");
}

export function buildRunSummaryPath(outputRoot: string, runId: string): string {
  return path.join(outputRoot, `${runId}.json`);
}

export async function appendManifest(
  entry: Omit<ManifestEntry, "timestamp">,
  outputRoot: string = DEFAULT_OUTPUT_ROOT,
): Promise<void> {
  await ensureDir(outputRoot);
  const line = `${JSON.stringify({
    timestamp: new Date().toISOString(),
    ...entry,
  })}\n`;
  await fs.appendFile(buildManifestPath(outputRoot), line, "utf-8");
}

export async function writeRunSummary(
  runId: string,
  summary: unknown,
  outputRoot: string = DEFAULT_OUTPUT_ROOT,
): Promise<void> {
  const summaryPath = buildRunSummaryPath(outputRoot, runId);
  await writeText(summaryPath, `${JSON.stringify(summary, null, 2)}\n`);
}
