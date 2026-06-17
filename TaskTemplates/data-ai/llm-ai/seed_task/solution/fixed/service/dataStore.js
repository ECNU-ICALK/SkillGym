const fs = require("fs");
const path = require("path");

const dataDir = process.env.DATA_DIR || path.join(__dirname, "..", "data");
const stateDir = process.env.STATE_DIR || path.join(__dirname, "..", "state");

function readJson(filePath) {
  return JSON.parse(fs.readFileSync(filePath, "utf8"));
}

function readJsonl(filePath) {
  return fs
    .readFileSync(filePath, "utf8")
    .split("\n")
    .map((line) => line.trim())
    .filter(Boolean)
    .map((line) => JSON.parse(line));
}

function writeJson(filePath, payload) {
  fs.writeFileSync(filePath, JSON.stringify(payload, null, 2) + "\n", "utf8");
}

function runtimeStatePath() {
  return path.join(stateDir, "runtime_state.json");
}

function ensureRuntimeState() {
  fs.mkdirSync(stateDir, { recursive: true });
  const filePath = runtimeStatePath();
  if (!fs.existsSync(filePath)) {
    writeJson(filePath, {
      provider_requests: [],
      service_requests: []
    });
  }
}

function loadTicketCatalog() {
  const rows = [
    ...readJsonl(path.join(dataDir, "tickets", "banking77_curated.jsonl")),
    ...readJsonl(path.join(dataDir, "tickets", "clinc150_oos_curated.jsonl"))
  ];
  const byId = new Map();
  for (const row of rows) {
    byId.set(row.id, row);
  }
  return byId;
}

function getTicket(ticketId) {
  return loadTicketCatalog().get(ticketId) || null;
}

function getPolicies() {
  return readJson(path.join(dataDir, "policies", "queue_policies.json"));
}

function getSandboxTriageCases() {
  return readJson(path.join(dataDir, "sandbox_cases", "triage_cases.json"));
}

function getSandboxReviewCases() {
  return readJson(path.join(dataDir, "sandbox_cases", "review_cases.json"));
}

function getRuntimeState() {
  ensureRuntimeState();
  return readJson(runtimeStatePath());
}

function updateRuntimeState(mutator) {
  const current = getRuntimeState();
  const next = mutator(current);
  writeJson(runtimeStatePath(), next);
}

function recordServiceRequest(entry) {
  updateRuntimeState((state) => ({
    ...state,
    service_requests: [
      ...state.service_requests,
      {
        at: new Date().toISOString(),
        ...entry
      }
    ]
  }));
}

module.exports = {
  getPolicies,
  getSandboxReviewCases,
  getSandboxTriageCases,
  getTicket,
  getRuntimeState,
  recordServiceRequest,
  stateDir,
  updateRuntimeState
};
