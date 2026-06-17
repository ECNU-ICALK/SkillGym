import { pathExists, readText } from "./utils.js";

export type HarborTrialMetrics = {
  totalDurationSec: number | null;
  environmentSetupSec: number | null;
  agentSetupSec: number | null;
  agentExecutionSec: number | null;
  verifierSec: number | null;
  totalTokens: number | null;
};

type JsonRecord = Record<string, unknown>;

function emptyMetrics(): HarborTrialMetrics {
  return {
    totalDurationSec: null,
    environmentSetupSec: null,
    agentSetupSec: null,
    agentExecutionSec: null,
    verifierSec: null,
    totalTokens: null,
  };
}

function asRecord(value: unknown): JsonRecord | null {
  if (!value || typeof value !== "object" || Array.isArray(value)) {
    return null;
  }
  return value as JsonRecord;
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

function parseIsoTimestamp(value: unknown): number | null {
  if (typeof value !== "string") {
    return null;
  }
  const millis = Date.parse(value);
  return Number.isFinite(millis) ? millis : null;
}

function computeDurationSec(startedAt: unknown, finishedAt: unknown): number | null {
  const startMs = parseIsoTimestamp(startedAt);
  const endMs = parseIsoTimestamp(finishedAt);
  if (startMs === null || endMs === null) {
    return null;
  }
  return (endMs - startMs) / 1000;
}

function extractStageDuration(resultRecord: JsonRecord | null, stageKey: string): number | null {
  const stageRecord = asRecord(resultRecord?.[stageKey]);
  return computeDurationSec(stageRecord?.started_at, stageRecord?.finished_at);
}

function extractTotalTokens(trajectoryRecord: JsonRecord | null): number | null {
  const finalMetrics = asRecord(trajectoryRecord?.final_metrics);
  const extra = asRecord(finalMetrics?.extra);
  const extraTotalTokens = parseFiniteNumber(extra?.total_tokens);
  if (extraTotalTokens !== null) {
    return extraTotalTokens;
  }

  const totalPromptTokens = parseFiniteNumber(finalMetrics?.total_prompt_tokens);
  const totalCompletionTokens = parseFiniteNumber(finalMetrics?.total_completion_tokens);
  if (totalPromptTokens === null || totalCompletionTokens === null) {
    return null;
  }
  return totalPromptTokens + totalCompletionTokens;
}

async function readJsonRecord(filePath?: string): Promise<JsonRecord | null> {
  if (!filePath || !(await pathExists(filePath))) {
    return null;
  }
  try {
    return asRecord(JSON.parse(await readText(filePath)));
  } catch {
    return null;
  }
}

export async function extractHarborTrialMetrics(
  resultPath?: string,
  trajectoryPath?: string,
): Promise<HarborTrialMetrics> {
  const metrics = emptyMetrics();
  const resultRecord = await readJsonRecord(resultPath);
  const trajectoryRecord = await readJsonRecord(trajectoryPath);

  metrics.totalDurationSec = computeDurationSec(resultRecord?.started_at, resultRecord?.finished_at);
  metrics.environmentSetupSec = extractStageDuration(resultRecord, "environment_setup");
  metrics.agentSetupSec = extractStageDuration(resultRecord, "agent_setup");
  metrics.agentExecutionSec = extractStageDuration(resultRecord, "agent_execution");
  metrics.verifierSec = extractStageDuration(resultRecord, "verifier");
  metrics.totalTokens = extractTotalTokens(trajectoryRecord);

  return metrics;
}
