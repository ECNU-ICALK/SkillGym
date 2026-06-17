import assert from "node:assert/strict";
import { promises as fs } from "node:fs";
import os from "node:os";
import path from "node:path";
import { extractHarborTrialMetrics } from "../src/harbor_metrics.js";
import { writeText } from "../src/utils.js";

async function writeJsonFixture(filePath: string, value: unknown): Promise<void> {
  await writeText(filePath, `${JSON.stringify(value, null, 2)}\n`);
}

async function makeTrialFixture(options: {
  result: unknown;
  trajectory?: unknown;
}): Promise<{ resultPath: string; trajectoryPath?: string }> {
  const root = await fs.mkdtemp(path.join(os.tmpdir(), "harbor-metrics-"));
  const resultPath = path.join(root, "result.json");
  await writeJsonFixture(resultPath, options.result);

  if (options.trajectory === undefined) {
    return { resultPath };
  }

  const trajectoryPath = path.join(root, "agent", "trajectory.json");
  await writeJsonFixture(trajectoryPath, options.trajectory);
  return { resultPath, trajectoryPath };
}

{
  const fixture = await makeTrialFixture({
    result: {
      started_at: "2026-04-17T19:27:10.000Z",
      finished_at: "2026-04-17T19:55:59.500Z",
      environment_setup: {
        started_at: "2026-04-17T19:27:10.000Z",
        finished_at: "2026-04-17T19:27:32.500Z",
      },
      agent_setup: {
        started_at: "2026-04-17T19:27:32.500Z",
        finished_at: "2026-04-17T19:27:50.000Z",
      },
      agent_execution: {
        started_at: "2026-04-17T19:27:50.000Z",
        finished_at: "2026-04-17T19:33:49.250Z",
      },
      verifier: {
        started_at: "2026-04-17T19:55:15.000Z",
        finished_at: "2026-04-17T19:55:56.500Z",
      },
    },
    trajectory: {
      final_metrics: {
        total_prompt_tokens: 100,
        total_completion_tokens: 20,
        extra: {
          total_tokens: 130,
        },
      },
    },
  });

  const metrics = await extractHarborTrialMetrics(fixture.resultPath, fixture.trajectoryPath);
  assert.deepEqual(metrics, {
    totalDurationSec: 1729.5,
    environmentSetupSec: 22.5,
    agentSetupSec: 17.5,
    agentExecutionSec: 359.25,
    verifierSec: 41.5,
    totalTokens: 130,
  });
}

{
  const fixture = await makeTrialFixture({
    result: {
      started_at: "2026-04-17T19:27:10.000Z",
      finished_at: "2026-04-17T19:27:20.000Z",
      environment_setup: {
        started_at: "2026-04-17T19:27:10.000Z",
        finished_at: "2026-04-17T19:27:11.000Z",
      },
      agent_setup: {
        started_at: "2026-04-17T19:27:11.000Z",
        finished_at: "2026-04-17T19:27:12.000Z",
      },
      agent_execution: {
        started_at: "2026-04-17T19:27:12.000Z",
        finished_at: "2026-04-17T19:27:18.000Z",
      },
      verifier: {
        started_at: "2026-04-17T19:27:18.000Z",
        finished_at: "2026-04-17T19:27:20.000Z",
      },
    },
    trajectory: {
      final_metrics: {
        total_prompt_tokens: 800,
        total_completion_tokens: 120,
        extra: {},
      },
    },
  });

  const metrics = await extractHarborTrialMetrics(fixture.resultPath, fixture.trajectoryPath);
  assert.equal(metrics.totalTokens, 920);
}

{
  const fixture = await makeTrialFixture({
    result: {
      started_at: "2026-04-17T19:27:10.000Z",
      finished_at: "2026-04-17T19:27:20.000Z",
      environment_setup: {
        started_at: "2026-04-17T19:27:10.000Z",
        finished_at: "2026-04-17T19:27:11.000Z",
      },
      agent_setup: {
        started_at: "2026-04-17T19:27:11.000Z",
        finished_at: "2026-04-17T19:27:12.000Z",
      },
      agent_execution: {
        started_at: "2026-04-17T19:27:12.000Z",
        finished_at: "2026-04-17T19:27:18.000Z",
      },
      verifier: {
        started_at: "2026-04-17T19:27:18.000Z",
        finished_at: "2026-04-17T19:27:20.000Z",
      },
    },
    trajectory: {},
  });

  const metrics = await extractHarborTrialMetrics(fixture.resultPath, fixture.trajectoryPath);
  assert.equal(metrics.totalDurationSec, 10);
  assert.equal(metrics.totalTokens, null);
}

{
  const fixture = await makeTrialFixture({
    result: {
      started_at: "2026-04-17T19:27:10.000Z",
      finished_at: "2026-04-17T19:27:20.000Z",
      environment_setup: {
        started_at: "2026-04-17T19:27:10.000Z",
      },
      agent_setup: {
        finished_at: "2026-04-17T19:27:12.000Z",
      },
      agent_execution: {
        started_at: "2026-04-17T19:27:12.000Z",
        finished_at: "2026-04-17T19:27:18.000Z",
      },
    },
    trajectory: {
      final_metrics: {
        total_prompt_tokens: 10,
        total_completion_tokens: 5,
      },
    },
  });

  const metrics = await extractHarborTrialMetrics(fixture.resultPath, fixture.trajectoryPath);
  assert.deepEqual(metrics, {
    totalDurationSec: 10,
    environmentSetupSec: null,
    agentSetupSec: null,
    agentExecutionSec: 6,
    verifierSec: null,
    totalTokens: 15,
  });
}
