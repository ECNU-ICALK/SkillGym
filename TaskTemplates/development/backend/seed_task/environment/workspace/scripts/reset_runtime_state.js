const fs = require("fs");
const path = require("path");

const dataDir = process.env.DATA_DIR || path.join("/app/workspace", "data");
const stateDir = process.env.STATE_DIR || path.join("/app/workspace", "state");

fs.mkdirSync(stateDir, { recursive: true });
const seed = fs.readFileSync(path.join(dataDir, "refund_requests.json"), "utf8");
fs.writeFileSync(path.join(stateDir, "runtime_state.json"), seed, "utf8");
