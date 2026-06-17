import assert from "node:assert/strict";
import { CodexTaskBuilderClient } from "../src/codex.js";
import { parseNonNegativeInteger, parseNonNegativeNumber } from "../src/utils.js";

const RETRY_BACKOFF = {
  fifteenMinutes: 15 * 60_000,
  thirtyMinutes: 30 * 60_000,
  sixtyMinutes: 60 * 60_000,
} as const;

type FakeThreadBehavior = {
  threadId?: string | null;
  finalResponse?: string;
  error?: Error;
};

function buildFakeCodex(args: {
  startBehaviors?: FakeThreadBehavior[];
  resumeBehaviors?: FakeThreadBehavior[];
}): {
  codex: {
    startThread: (_options?: unknown) => {
      id: string | null;
      run: (input?: string) => Promise<{ items: unknown[]; finalResponse: string; usage: null }>;
    };
    resumeThread: (
      threadId: string,
      _options?: unknown,
    ) => { id: string | null; run: (input?: string) => Promise<{ items: unknown[]; finalResponse: string; usage: null }> };
  };
  startCallCount: () => number;
  resumeThreadIds: () => string[];
  runInputs: () => string[];
} {
  const startBehaviors = [...(args.startBehaviors ?? [])];
  const resumeBehaviors = [...(args.resumeBehaviors ?? [])];
  let startCalls = 0;
  const resumeIds: string[] = [];
  const runInputs: string[] = [];

  function buildThread(behavior: FakeThreadBehavior | undefined, fallbackThreadId: string | null) {
    assert.ok(behavior, "缺少 fake thread behavior");
    return {
      id: behavior.threadId ?? fallbackThreadId,
      async run(input?: string) {
        if (input) {
          runInputs.push(input);
        }
        if (behavior.error) {
          throw behavior.error;
        }
        return {
          items: [],
          finalResponse: behavior.finalResponse ?? "",
          usage: null,
        };
      },
    };
  }

  return {
    codex: {
      startThread() {
        startCalls += 1;
        return buildThread(startBehaviors.shift(), `start-thread-${startCalls}`);
      },
      resumeThread(threadId: string) {
        resumeIds.push(threadId);
        return buildThread(resumeBehaviors.shift(), threadId);
      },
    },
    startCallCount: () => startCalls,
    resumeThreadIds: () => [...resumeIds],
    runInputs: () => [...runInputs],
  };
}

const unit = {
  template: {
    templateId: "tools__debugging",
    templateRelativePath: "tools/debugging",
    metadata: {
      difficulty: "hard",
      category: "debugging",
      tags: ["network"],
    },
  },
  inputSkills: [
    {
      name: "node-connect",
      dirName: "01__node-connect",
    },
  ],
  skillMode: "per-skill",
  targetSkill: {
    name: "node-connect",
    dirName: "01__node-connect",
  },
  scopeSlug: "01__node-connect",
  taskCount: 1,
  pendingTaskOrdinals: [1],
  finalFamilyDir: "/tmp/final/tools__debugging/01__node-connect",
  publishedTasks: [],
} as const;

const workspace = {
  rootDir: "/tmp/codex-task-builder-workspace",
} as const;

const plan = {
  derivedTaskId: "task1",
  taskOrdinal: 1,
  title: "Investigate connection failures",
  realWorldContext: "A support engineering team is triaging real-world TCP connection failures.",
  referenceData: "Reference data:\n\n- Node.js net documentation: https://nodejs.org/api/net.html",
  taskGoal: "Fix the connection issue",
  inputAssets: "Provide offline connection logs and a broken service configuration.",
  requiredOutputs: "The agent must update the configuration and write a diagnosis summary.",
  verifierFocus: "Check that the service connects correctly and the summary matches the observed failure.",
  skillBenefitRationale: "The skill helps narrow the root cause quickly",
  difficulty: "medium",
  category: "debugging",
  templateId: "tools__debugging",
  skillMode: "per-skill",
  targetSkillDirName: "01__node-connect",
  targetSkillName: "node-connect",
} as const;

const originalWarn = console.warn;
console.warn = () => {};

try {
  assert.equal(parseNonNegativeInteger(undefined, "--codex-run-retries", 3), 3);
  assert.equal(parseNonNegativeInteger("0", "--codex-run-retries", 3), 0);
  assert.equal(parseNonNegativeInteger("3", "--codex-run-retries", 3), 3);
  assert.throws(
    () => parseNonNegativeInteger("-1", "--codex-run-retries", 3),
    /--codex-run-retries 必须是 >= 0 的整数/,
  );
  assert.throws(
    () => parseNonNegativeInteger("1.5", "--codex-run-retries", 3),
    /--codex-run-retries 必须是 >= 0 的整数/,
  );
  assert.equal(parseNonNegativeNumber(undefined, "--task-attempt-timeout-hours", 2), 2);
  assert.equal(parseNonNegativeNumber("0", "--task-attempt-timeout-hours", 2), 0);
  assert.equal(parseNonNegativeNumber("1.5", "--task-attempt-timeout-hours", 2), 1.5);
  assert.throws(
    () => parseNonNegativeNumber("-1", "--task-attempt-timeout-hours", 2),
    /--task-attempt-timeout-hours 必须是 >= 0 的数字/,
  );

  {
    const fakeCodex = buildFakeCodex({
      startBehaviors: [{ error: new Error("plan failure") }],
    });
    const sleeps: number[] = [];
    const client = new CodexTaskBuilderClient({
      codexRunRetries: 0,
      codex: fakeCodex.codex,
      sleep: async (ms) => {
        sleeps.push(ms);
      },
    });

    await assert.rejects(
      () =>
        client.planTask(unit as never, workspace as never, {
          derivedTaskId: "task1",
          taskOrdinal: 1,
        }),
      /plan failure/,
    );
    assert.equal(fakeCodex.startCallCount(), 1);
    assert.deepEqual(sleeps, []);
  }

  {
    const fakeCodex = buildFakeCodex({
      startBehaviors: [
        { error: new Error("plan failure 1") },
        { error: new Error("plan failure 2") },
        { error: new Error("plan failure 3") },
        {
          threadId: "plan-thread-4",
          finalResponse: JSON.stringify({
            title: "Investigate connection failures",
            realWorldContext: "A support engineering team is triaging real-world TCP connection failures.",
            referenceData: "Reference data:\n\n- Node.js net documentation: https://nodejs.org/api/net.html",
            taskGoal: "Fix the connection issue",
            inputAssets: "Provide offline connection logs and a broken service configuration.",
            requiredOutputs: "The agent must update the configuration and write a diagnosis summary.",
            verifierFocus: "Check that the service connects correctly and the summary matches the observed failure.",
            skillBenefitRationale: "The skill helps narrow the root cause quickly",
            difficulty: "medium",
            category: "debugging",
          }),
        },
      ],
    });
    const sleeps: number[] = [];
    const client = new CodexTaskBuilderClient({
      codexRunRetries: 3,
      codex: fakeCodex.codex,
      sleep: async (ms) => {
        sleeps.push(ms);
      },
    });

    const result = await client.planTask(unit as never, workspace as never, {
      derivedTaskId: "task1",
      taskOrdinal: 1,
    });
    assert.equal(result.threadId, "plan-thread-4");
    assert.equal("primaryOutputFile" in result.data, false);
    assert.equal(fakeCodex.startCallCount(), 4);
    assert.deepEqual(sleeps, [
      RETRY_BACKOFF.fifteenMinutes,
      RETRY_BACKOFF.thirtyMinutes,
      RETRY_BACKOFF.sixtyMinutes,
    ]);
  }

  {
    const fakeCodex = buildFakeCodex({
      startBehaviors: [
        { error: new Error("plan failure 1") },
        { error: new Error("plan failure 2") },
        { error: new Error("plan failure 3") },
        { error: new Error("plan failure 4") },
        {
          threadId: "plan-thread-5",
          finalResponse: JSON.stringify({
            title: "Investigate connection failures",
            realWorldContext: "A support engineering team is triaging real-world TCP connection failures.",
            referenceData: "Reference data:\n\n- Node.js net documentation: https://nodejs.org/api/net.html",
            taskGoal: "Fix the connection issue",
            inputAssets: "Provide offline connection logs and a broken service configuration.",
            requiredOutputs: "The agent must update the configuration and write a diagnosis summary.",
            verifierFocus: "Check that the service connects correctly and the summary matches the observed failure.",
            skillBenefitRationale: "The skill helps narrow the root cause quickly",
            difficulty: "medium",
            category: "debugging",
          }),
        },
      ],
    });
    const sleeps: number[] = [];
    const client = new CodexTaskBuilderClient({
      codexRunRetries: 4,
      codex: fakeCodex.codex,
      sleep: async (ms) => {
        sleeps.push(ms);
      },
    });

    const result = await client.planTask(unit as never, workspace as never, {
      derivedTaskId: "task1",
      taskOrdinal: 1,
    });
    assert.equal(result.threadId, "plan-thread-5");
    assert.equal(fakeCodex.startCallCount(), 5);
    assert.deepEqual(sleeps, [
      RETRY_BACKOFF.fifteenMinutes,
      RETRY_BACKOFF.thirtyMinutes,
      RETRY_BACKOFF.sixtyMinutes,
      RETRY_BACKOFF.sixtyMinutes,
    ]);
  }

  {
    const fakeCodex = buildFakeCodex({
      startBehaviors: [
        {
          threadId: "task-plan-thread-1",
          finalResponse: JSON.stringify({
            title: "Investigate connection failures",
            realWorldContext: "A support engineering team is triaging real-world TCP connection failures.",
            referenceData: "Reference data:\n\n- Node.js net documentation: https://nodejs.org/api/net.html",
            taskGoal: "Fix the connection issue",
            inputAssets: "Provide offline connection logs and a broken service configuration.",
            requiredOutputs: "The agent must update the configuration and write a diagnosis summary.",
            verifierFocus: "Check that the service connects correctly and the summary matches the observed failure.",
            skillBenefitRationale: "The skill helps narrow the root cause quickly",
            difficulty: "medium",
            category: "debugging",
          }),
        },
      ],
    });
    const client = new CodexTaskBuilderClient({
      codexRunRetries: 0,
      codex: fakeCodex.codex,
    });

    const result = await client.planTask(
      unit as never,
      workspace as never,
      {
        derivedTaskId: "task1",
        taskOrdinal: 1,
      },
    );
    assert.equal(result.threadId, "task-plan-thread-1");
    assert.equal("primaryOutputFile" in result.data, false);
    assert.equal(fakeCodex.startCallCount(), 1);
  }

  {
    const fakeCodex = buildFakeCodex({
      startBehaviors: [
        { error: new Error("write failure 1") },
        { error: new Error("write failure 2") },
        { error: new Error("write failure 3") },
        { error: new Error("write failure 4") },
      ],
    });
    const sleeps: number[] = [];
    const client = new CodexTaskBuilderClient({
      codexRunRetries: 3,
      codex: fakeCodex.codex,
      sleep: async (ms) => {
        sleeps.push(ms);
      },
    });

    await assert.rejects(() => client.writeTask(unit as never, workspace as never, plan as never), /write failure 4/);
    assert.equal(fakeCodex.startCallCount(), 4);
    assert.deepEqual(sleeps, [
      RETRY_BACKOFF.fifteenMinutes,
      RETRY_BACKOFF.thirtyMinutes,
      RETRY_BACKOFF.sixtyMinutes,
    ]);
  }

  {
    const fakeCodex = buildFakeCodex({
      startBehaviors: [
        { error: new Error("review failure") },
        {
          threadId: "review-thread-2",
          finalResponse: JSON.stringify({
            taskResults: [
              {
                derivedTaskId: "task1",
                blockingPass: true,
                blockingIssues: [],
              },
            ],
          }),
        },
      ],
    });
    const sleeps: number[] = [];
    const client = new CodexTaskBuilderClient({
      codexRunRetries: 3,
      codex: fakeCodex.codex,
      sleep: async (ms) => {
        sleeps.push(ms);
      },
    });

    const result = await client.reviewTaskBlocking(unit as never, workspace as never, plan as never);
    assert.equal(result.threadId, "review-thread-2");
    assert.equal(result.data.taskResults[0]?.blockingPass, true);
    assert.equal(fakeCodex.startCallCount(), 2);
    assert.deepEqual(sleeps, [RETRY_BACKOFF.fifteenMinutes]);
  }

  {
    const fakeCodex = buildFakeCodex({
      resumeBehaviors: [
        { error: new Error("repair failure") },
        {
          threadId: "persisted-thread",
          finalResponse: JSON.stringify({
            summary: "Fixed the draft",
            repairReason: "Retry succeeded",
            changedFiles: ["instruction.md"],
          }),
        },
      ],
    });
    const sleeps: number[] = [];
    const client = new CodexTaskBuilderClient({
      codexRunRetries: 3,
      codex: fakeCodex.codex,
      sleep: async (ms) => {
        sleeps.push(ms);
      },
    });

    const result = await client.repairTask({
      unit: unit as never,
      workspace: workspace as never,
      plan: plan as never,
      blockingIssues: [],
      staticIssues: [],
      runtimeIssues: [],
      skillEffectIssues: [],
      skillEffectEvidenceRoot: "/tmp/artifacts/skill_effect/task1/cycle-0-attempt-1",
      skillEffectResultPath: "/tmp/artifacts/task1.skill-effect.cycle-0.attempt-1.json",
      threadId: "persisted-thread",
    });
    assert.equal(result.threadId, "persisted-thread");
    assert.equal(result.data.changedFiles[0], "instruction.md");
    assert.deepEqual(fakeCodex.resumeThreadIds(), ["persisted-thread", "persisted-thread"]);
    assert.match(fakeCodex.runInputs()[0] ?? "", /Skill-effect evidence root: \/tmp\/artifacts\/skill_effect\/task1\/cycle-0-attempt-1/);
    assert.doesNotMatch(fakeCodex.runInputs()[0] ?? "", /Oracle fallback evidence root/);
    assert.doesNotMatch(fakeCodex.runInputs()[0] ?? "", /with_skill 日志根目录/);
    assert.equal(fakeCodex.startCallCount(), 0);
    assert.deepEqual(sleeps, [RETRY_BACKOFF.fifteenMinutes]);
  }
} finally {
  console.warn = originalWarn;
}
