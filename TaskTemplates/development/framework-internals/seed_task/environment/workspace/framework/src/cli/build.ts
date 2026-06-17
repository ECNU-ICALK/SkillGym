import fs from "node:fs";
import { spawnSync } from "node:child_process";

import { buildScenarioArtifacts, readBuildDiagnostics } from "../build/build-fixture.js";
import { parseCliArg } from "../shared/task-context.js";

const scenarioId = parseCliArg("--scenario");
const result = buildScenarioArtifacts(scenarioId);
const diagnostics = readBuildDiagnostics(result.scenarioId);
const skillProbePath = "/root/.codex/skills/flags/diagnose_runtime_define_scope.sh";

if (fs.existsSync(skillProbePath)) {
  spawnSync(skillProbePath, [result.scenarioId], {
    stdio: "inherit",
    env: process.env
  });
}

console.log(
  JSON.stringify(
    {
      ...result,
      diagnostics
    },
    null,
    2
  )
);
