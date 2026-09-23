const fs = require("fs");
const path = require("path");
const { execFileSync } = require("child_process");

const workspaceRoot = process.env.WORKSPACE_ROOT || "/app/workspace";
const auditScript = path.join(workspaceRoot, "scripts", "provider_audit.sh");

execFileSync("bash", [auditScript], {
  cwd: workspaceRoot,
  stdio: "inherit",
  env: process.env,
});

const auditPath = path.join(workspaceRoot, "output", "provider_audit.json");
const payload = JSON.parse(fs.readFileSync(auditPath, "utf-8"));
console.log(JSON.stringify(payload, null, 2));
