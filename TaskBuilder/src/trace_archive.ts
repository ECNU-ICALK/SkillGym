import path from "node:path";
import type { AcceptanceKind } from "./materialize.js";
import { copyFile, ensureDir, pathExists, slugify, writeJson } from "./utils.js";

export type TraceArchiveOutcome = AcceptanceKind | "failed";
export type TracePairStage = "skill-effect";

export type TraceVariantEvidence = {
  status: string;
  passed: boolean;
  reward?: number | null;
  resultPath?: string;
  trajectoryPath?: string;
  variantTaskDir?: string;
  summary?: string;
};

export type TraceArchivePair = {
  runId: string;
  templateId: string;
  scopeSlug: string;
  derivedTaskId: string;
  attemptIndex: number;
  cycle: number;
  stage: TracePairStage;
  stageAttemptIndex: number;
  pairRoot: string;
  bucket?: string;
  withSkill: TraceVariantEvidence;
  noSkill: TraceVariantEvidence;
};

function buildPairDirName(pair: TraceArchivePair): string {
  return [
    `pair-run-${slugify(pair.runId)}`,
    `attempt-${pair.attemptIndex}`,
    `cycle-${pair.cycle}`,
    `${pair.stage}-${pair.stageAttemptIndex}`,
  ].join("__");
}

async function copyIfPresent(sourcePath: string | undefined, targetPath: string): Promise<string | undefined> {
  if (!sourcePath || !(await pathExists(sourcePath))) {
    return undefined;
  }
  await copyFile(sourcePath, targetPath);
  return targetPath;
}

export async function archiveTracePairs(args: {
  outputRoot: string;
  outcome: TraceArchiveOutcome;
  pairs: TraceArchivePair[];
}): Promise<void> {
  for (const pair of args.pairs) {
    const pairDir = path.join(
      args.outputRoot,
      "trace_archive",
      args.outcome,
      pair.templateId,
      pair.scopeSlug,
      pair.derivedTaskId,
      buildPairDirName(pair),
    );
    const withSkillDir = path.join(pairDir, "with_skill");
    const noSkillDir = path.join(pairDir, "no_skill");
    await Promise.all([ensureDir(withSkillDir), ensureDir(noSkillDir)]);

    const copiedWithSkillResult = await copyIfPresent(pair.withSkill.resultPath, path.join(withSkillDir, "result.json"));
    const copiedWithSkillTrajectory = await copyIfPresent(
      pair.withSkill.trajectoryPath,
      path.join(withSkillDir, "trajectory.json"),
    );
    const copiedNoSkillResult = await copyIfPresent(pair.noSkill.resultPath, path.join(noSkillDir, "result.json"));
    const copiedNoSkillTrajectory = await copyIfPresent(
      pair.noSkill.trajectoryPath,
      path.join(noSkillDir, "trajectory.json"),
    );

    await writeJson(path.join(pairDir, "pair_result.json"), {
      outcome: args.outcome,
      stage: pair.stage,
      stageAttemptIndex: pair.stageAttemptIndex,
      runId: pair.runId,
      templateId: pair.templateId,
      scopeSlug: pair.scopeSlug,
      derivedTaskId: pair.derivedTaskId,
      attemptIndex: pair.attemptIndex,
      cycle: pair.cycle,
      pairRoot: pair.pairRoot,
      bucket: pair.bucket ?? null,
      withSkill: {
        status: pair.withSkill.status,
        passed: pair.withSkill.passed,
        reward: pair.withSkill.reward ?? null,
        sourceResultPath: pair.withSkill.resultPath ?? null,
        sourceTrajectoryPath: pair.withSkill.trajectoryPath ?? null,
        archivedResultPath: copiedWithSkillResult ?? null,
        archivedTrajectoryPath: copiedWithSkillTrajectory ?? null,
        variantTaskDir: pair.withSkill.variantTaskDir ?? null,
        summary: pair.withSkill.summary ?? null,
      },
      noSkill: {
        status: pair.noSkill.status,
        passed: pair.noSkill.passed,
        reward: pair.noSkill.reward ?? null,
        sourceResultPath: pair.noSkill.resultPath ?? null,
        sourceTrajectoryPath: pair.noSkill.trajectoryPath ?? null,
        archivedResultPath: copiedNoSkillResult ?? null,
        archivedTrajectoryPath: copiedNoSkillTrajectory ?? null,
        variantTaskDir: pair.noSkill.variantTaskDir ?? null,
        summary: pair.noSkill.summary ?? null,
      },
    });
  }
}
