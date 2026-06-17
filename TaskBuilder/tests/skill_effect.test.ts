import assert from "node:assert/strict";
import { promises as fs } from "node:fs";
import os from "node:os";
import path from "node:path";
import {
  buildSkillEffectBucket,
  buildSkillEffectIssues,
  isAcceptedSkillEffectBucket,
  runSkillEffectEvaluation,
  type AgentRunEvidence,
  type AgentRunResult,
  type SkillEffectEvaluationResult,
} from "../src/skill_effect.js";
import { writeSkillEffectResultArtifact } from "../src/skill_effect_artifacts.js";
import { pathExists, readText } from "../src/utils.js";

function makeRunResult(
  variant: "with_skill" | "no_skill",
  comparisonStatus: AgentRunResult["comparisonStatus"],
  comparisonReason: string,
): AgentRunResult {
  return {
    variant,
    passed: comparisonStatus === "pass",
    comparisonStatus,
    comparisonReason,
    issues: comparisonStatus === "pass" ? [] : [`${variant}:${comparisonReason}`],
    failureKind: comparisonStatus === "valid_reward_fail" ? "harbor-reward" : comparisonStatus === "invalid_fail" ? "harbor-task" : undefined,
    evidence: {
      variant,
      variantTaskDir: `/tmp/${variant}`,
      logsDir: `/tmp/${variant}/logs`,
      runtimeLogRoot: `/tmp/${variant}/logs`,
      logFilePath: `/tmp/${variant}/logs/harbor-run.log`,
      jobDir: `/tmp/${variant}/logs/job`,
      command: ["harbor", "run"],
      reward: comparisonStatus === "pass" ? 1 : 0,
      summary: comparisonReason,
    },
  };
}

function createDeferred<T>(): {
  promise: Promise<T>;
  resolve: (value: T | PromiseLike<T>) => void;
  reject: (reason?: unknown) => void;
} {
  let resolve!: (value: T | PromiseLike<T>) => void;
  let reject!: (reason?: unknown) => void;
  const promise = new Promise<T>((res, rej) => {
    resolve = res;
    reject = rej;
  });
  return { promise, resolve, reject };
}

function nextTick(): Promise<void> {
  return new Promise((resolve) => {
    setImmediate(resolve);
  });
}

function makeEvaluation(
  withSkillStatus: AgentRunResult["comparisonStatus"],
  noSkillStatus: AgentRunResult["comparisonStatus"],
): SkillEffectEvaluationResult {
  const withSkill = makeRunResult("with_skill", withSkillStatus, `with:${withSkillStatus}`);
  const noSkill = makeRunResult("no_skill", noSkillStatus, `no:${noSkillStatus}`);
  const bucket = buildSkillEffectBucket(withSkill.comparisonStatus, noSkill.comparisonStatus);
  return {
    bucket,
    repairRequired: !isAcceptedSkillEffectBucket(bucket),
    pairRoot: "/tmp/pair",
    withSkill,
    noSkill,
  };
}

{
  const evaluation = makeEvaluation("pass", "valid_reward_fail");
  assert.equal(evaluation.bucket, "with_skill_pass__no_skill_fail");
  assert.equal(evaluation.repairRequired, false);
  assert.deepEqual(buildSkillEffectIssues("task1", evaluation), []);
}

{
  const evaluation = makeEvaluation("pass", "invalid_fail");
  assert.equal(evaluation.bucket, "with_skill_pass__no_skill_invalid_fail");
  assert.equal(evaluation.repairRequired, true);
  const issues = buildSkillEffectIssues("task1", evaluation);
  assert.ok(issues.some((issue) => issue.message.includes("no_skill invalid fail")));
}

{
  const evaluation = makeEvaluation("pass", "pass");
  assert.equal(evaluation.bucket, "with_skill_pass__no_skill_pass");
  assert.equal(evaluation.repairRequired, true);
}

{
  const evaluation = makeEvaluation("invalid_fail", "valid_reward_fail");
  assert.equal(evaluation.bucket, "with_skill_fail__no_skill_fail");
  assert.equal(evaluation.repairRequired, true);
}

{
  const evaluation = makeEvaluation("invalid_fail", "pass");
  assert.equal(evaluation.bucket, "with_skill_fail__no_skill_pass");
  assert.equal(evaluation.repairRequired, true);
}

{
  const artifactsDir = await fs.mkdtemp(path.join(os.tmpdir(), "skill-effect-artifacts-"));
  const evaluation = makeEvaluation("pass", "valid_reward_fail");
  const withSkillMetrics: NonNullable<AgentRunEvidence["metrics"]> = {
    totalDurationSec: 120,
    environmentSetupSec: 10,
    agentSetupSec: 5,
    agentExecutionSec: 90,
    verifierSec: 15,
    totalTokens: 1234,
  };
  const noSkillMetrics: NonNullable<AgentRunEvidence["metrics"]> = {
    totalDurationSec: 80,
    environmentSetupSec: 8,
    agentSetupSec: 4,
    agentExecutionSec: 60,
    verifierSec: 8,
    totalTokens: 567,
  };
  evaluation.withSkill.evidence.metrics = withSkillMetrics;
  evaluation.noSkill.evidence.metrics = noSkillMetrics;
  const resultPath = await writeSkillEffectResultArtifact({
    artifactsDir,
    derivedTaskId: "task1",
    cycle: 3,
    attemptIndex: 2,
    result: evaluation,
  });

  assert.equal(
    resultPath,
    path.join(artifactsDir, "task1.skill-effect.cycle-3.attempt-2.json"),
  );
  assert.equal(await pathExists(resultPath), true);
  assert.equal(
    await pathExists(path.join(artifactsDir, "task1.skill-effect.cycle-3.json")),
    false,
  );
  const saved = JSON.parse(await readText(resultPath)) as SkillEffectEvaluationResult;
  assert.deepEqual(saved.withSkill.evidence.metrics, withSkillMetrics);
  assert.deepEqual(saved.noSkill.evidence.metrics, noSkillMetrics);
  assert.deepEqual(
    saved,
    JSON.parse(JSON.stringify(evaluation)) as SkillEffectEvaluationResult,
  );
}

{
  const artifactsDir = await fs.mkdtemp(path.join(os.tmpdir(), "skill-effect-parallel-"));
  const events: string[] = [];
  const withSkillDeferred = createDeferred<AgentRunResult>();
  const noSkillDeferred = createDeferred<AgentRunResult>();
  const workspace = {
    artifactsDir,
    runId: "run-parallel",
  } as const;
  const plan = {
    derivedTaskId: "task1",
  } as const;

  const evaluationPromise = runSkillEffectEvaluation({
    workspace: workspace as never,
    plan: plan as never,
    runtimeEnvironment: "e2b",
    cycle: 2,
    attemptIndex: 1,
    draftTaskDir: "/tmp/draft",
    modelName: "openai/gpt-5.4",
    apiKey: "sk-test",
    deps: {
      prepareWithSkillVariant: async ({ targetTaskDir }) => {
        events.push("prepare_with_skill");
        return { targetTaskDir };
      },
      prepareNoSkillVariant: async ({ targetTaskDir }) => {
        events.push("prepare_no_skill");
        return { targetTaskDir, removedCopyLines: 1 };
      },
      runAgentVariant: async ({ variant }) => {
        events.push(`start_${variant}`);
        return variant === "with_skill" ? withSkillDeferred.promise : noSkillDeferred.promise;
      },
    },
  });

  let settled = false;
  void evaluationPromise.finally(() => {
    settled = true;
  });

  await nextTick();
  assert.deepEqual(events, [
    "prepare_with_skill",
    "prepare_no_skill",
    "start_with_skill",
    "start_no_skill",
  ]);

  withSkillDeferred.resolve(makeRunResult("with_skill", "pass", "with:pass"));
  await nextTick();
  assert.equal(settled, false);

  noSkillDeferred.resolve(makeRunResult("no_skill", "valid_reward_fail", "no:valid_reward_fail"));
  const evaluation = await evaluationPromise;
  assert.equal(evaluation.withSkill.variant, "with_skill");
  assert.equal(evaluation.noSkill.variant, "no_skill");
  assert.equal(evaluation.bucket, "with_skill_pass__no_skill_fail");
  assert.equal(evaluation.repairRequired, false);
}

{
  const artifactsDir = await fs.mkdtemp(path.join(os.tmpdir(), "skill-effect-parallel-reject-"));
  const events: string[] = [];
  const withSkillDeferred = createDeferred<AgentRunResult>();
  const noSkillDeferred = createDeferred<AgentRunResult>();
  const workspace = {
    artifactsDir,
    runId: "run-reject",
  } as const;
  const plan = {
    derivedTaskId: "task1",
  } as const;
  const withSkillError = new Error("with_skill failed");

  const evaluationPromise = runSkillEffectEvaluation({
    workspace: workspace as never,
    plan: plan as never,
    runtimeEnvironment: "e2b",
    cycle: 3,
    attemptIndex: 1,
    draftTaskDir: "/tmp/draft",
    modelName: "openai/gpt-5.4",
    apiKey: "sk-test",
    deps: {
      prepareWithSkillVariant: async ({ targetTaskDir }) => {
        events.push("prepare_with_skill");
        return { targetTaskDir };
      },
      prepareNoSkillVariant: async ({ targetTaskDir }) => {
        events.push("prepare_no_skill");
        return { targetTaskDir, removedCopyLines: 1 };
      },
      runAgentVariant: async ({ variant }) => {
        events.push(`start_${variant}`);
        return variant === "with_skill" ? withSkillDeferred.promise : noSkillDeferred.promise;
      },
    },
  });

  let state: "pending" | "fulfilled" | "rejected" = "pending";
  let rejection: unknown = undefined;
  void evaluationPromise.then(
    () => {
      state = "fulfilled";
    },
    (error) => {
      state = "rejected";
      rejection = error;
    },
  );

  await nextTick();
  assert.deepEqual(events, [
    "prepare_with_skill",
    "prepare_no_skill",
    "start_with_skill",
    "start_no_skill",
  ]);

  withSkillDeferred.reject(withSkillError);
  await nextTick();
  assert.equal(state, "pending");

  noSkillDeferred.resolve(makeRunResult("no_skill", "pass", "no:pass"));
  await assert.rejects(evaluationPromise, (error) => {
    assert.equal(error, withSkillError);
    return true;
  });
  assert.equal(state, "rejected");
  assert.equal(rejection, withSkillError);
}
