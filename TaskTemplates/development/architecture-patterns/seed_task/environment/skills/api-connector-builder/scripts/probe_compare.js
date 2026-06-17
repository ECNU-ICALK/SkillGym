const fs = require("fs");
const path = require("path");
const { execFileSync } = require("child_process");

const workspaceRoot = process.env.WORKSPACE_ROOT || "/app/workspace";
const compareScript = path.join(workspaceRoot, "scripts", "provider_compare.sh");

execFileSync("bash", [compareScript], {
  cwd: workspaceRoot,
  stdio: "inherit",
  env: process.env,
});

const comparePath = path.join(workspaceRoot, "output", "provider_compare.json");
const payload = JSON.parse(fs.readFileSync(comparePath, "utf-8"));
console.log(JSON.stringify(payload, null, 2));
