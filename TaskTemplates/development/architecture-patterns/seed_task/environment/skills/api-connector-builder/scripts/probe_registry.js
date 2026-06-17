const path = require("path");
const { createRegistry } = require("/app/workspace/schedule_gateway/registry");

const workspaceRoot = process.env.WORKSPACE_ROOT || "/app/workspace";
const dataRoot = process.env.SCHEDULE_DATA_ROOT || path.join(workspaceRoot, "data");
const registry = createRegistry({ dataRoot });

for (const provider of registry.listProviders()) {
  console.log(`${provider.id}\t${provider.label}\t${provider.kind}\t${provider.timezone}\t${dataRoot}`);
}
