import path from "node:path";
import type { SkillEffectEvaluationResult } from "./skill_effect.js";
import { writeJson } from "./utils.js";

export function buildSkillEffectAttemptResultPath(
  artifactsDir: string,
  derivedTaskId: string,
  cycle: number,
  attemptIndex: number,
): string {
  return path.join(
    artifactsDir,
    `${derivedTaskId}.skill-effect.cycle-${cycle}.attempt-${attemptIndex}.json`,
  );
}

export async function writeSkillEffectResultArtifact(options: {
  artifactsDir: string;
  derivedTaskId: string;
  cycle: number;
  attemptIndex: number;
  result: SkillEffectEvaluationResult;
}): Promise<string> {
  const resultPath = buildSkillEffectAttemptResultPath(
    options.artifactsDir,
    options.derivedTaskId,
    options.cycle,
    options.attemptIndex,
  );
  await writeJson(resultPath, options.result);
  return resultPath;
}
