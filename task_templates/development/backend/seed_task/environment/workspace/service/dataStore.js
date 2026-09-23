const crypto = require("crypto");
const fs = require("fs");
const path = require("path");

function getDataDir() {
  return process.env.DATA_DIR || path.join("/app/workspace", "data");
}

function getStateDir() {
  return process.env.STATE_DIR || path.join("/app/workspace", "state");
}

function readJson(filePath) {
  return JSON.parse(fs.readFileSync(filePath, "utf8"));
}

function writeJson(filePath, value) {
  fs.writeFileSync(filePath, JSON.stringify(value, null, 2) + "\n", "utf8");
}

function runtimeStatePath() {
  return path.join(getStateDir(), "runtime_state.json");
}

function bootstrapRuntimeState() {
  fs.mkdirSync(getStateDir(), { recursive: true });
  const statePath = runtimeStatePath();
  if (!fs.existsSync(statePath)) {
    const seed = readJson(path.join(getDataDir(), "refund_requests.json"));
    writeJson(statePath, seed);
  }
  return statePath;
}

function loadReferenceData() {
  const dataDir = getDataDir();
  return {
    orders: readJson(path.join(dataDir, "orders_snapshot.json")),
    customers: readJson(path.join(dataDir, "customers_snapshot.json")),
    partnerKeys: readJson(path.join(dataDir, "partner_keys.json"))
  };
}

function loadRuntimeState() {
  return readJson(bootstrapRuntimeState());
}

function saveRuntimeState(state) {
  writeJson(runtimeStatePath(), state);
}

function fingerprintPayload(payload) {
  return crypto.createHash("sha256").update(JSON.stringify(payload)).digest("hex");
}

module.exports = {
  bootstrapRuntimeState,
  fingerprintPayload,
  getDataDir,
  getStateDir,
  loadReferenceData,
  loadRuntimeState,
  saveRuntimeState
};
