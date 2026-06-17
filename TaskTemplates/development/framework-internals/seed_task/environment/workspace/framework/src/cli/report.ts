import path from "node:path";

import { buildScenarioArtifacts } from "../build/build-fixture.js";
import {
  OUTPUT_ROOT,
  loadFixtureMatrix,
  writeJsonFile
} from "../shared/task-context.js";

const matrix = loadFixtureMatrix();
const scenarios = matrix.scenarios.map((scenario) => buildScenarioArtifacts(scenario.id));

writeJsonFile(path.join(OUTPUT_ROOT, "segment_cache_report.json"), {
  generatedAt: new Date().toISOString(),
  scenarios
});

console.log(JSON.stringify({ scenarios }, null, 2));
