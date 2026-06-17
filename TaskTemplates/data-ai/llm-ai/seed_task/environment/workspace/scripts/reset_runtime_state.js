const fs = require("fs");
const path = require("path");

const stateDir = process.env.STATE_DIR || path.join(__dirname, "..", "state");
const runtimeStatePath = path.join(stateDir, "runtime_state.json");

fs.mkdirSync(stateDir, { recursive: true });
fs.writeFileSync(
  runtimeStatePath,
  JSON.stringify(
    {
      provider_requests: [],
      service_requests: []
    },
    null,
    2
  ) + "\n",
  "utf8"
);
