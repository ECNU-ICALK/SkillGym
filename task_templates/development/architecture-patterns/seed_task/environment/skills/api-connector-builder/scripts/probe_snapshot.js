const fs = require("fs");
const path = require("path");
const { execFileSync } = require("child_process");

const workspaceRoot = process.env.WORKSPACE_ROOT || "/app/workspace";
const exportScript = path.join(workspaceRoot, "scripts", "export_snapshot.sh");

execFileSync("bash", [exportScript], {
  cwd: workspaceRoot,
  stdio: "inherit",
  env: process.env,
});

const snapshotPath = path.join(workspaceRoot, "output", "schedule_snapshot.json");
const payload = JSON.parse(fs.readFileSync(snapshotPath, "utf-8"));
console.log(JSON.stringify({
  provider_id: payload.provider_id,
  query_count: payload.query_count,
  kinds: payload.results.map((item) => item.kind),
}, null, 2));
