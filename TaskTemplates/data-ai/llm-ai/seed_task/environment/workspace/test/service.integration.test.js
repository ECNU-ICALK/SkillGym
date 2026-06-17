const test = require("node:test");
const assert = require("node:assert/strict");
const { spawn } = require("node:child_process");
const { once } = require("node:events");
const fs = require("node:fs");
const net = require("node:net");
const path = require("node:path");

const workspaceDir = fs.existsSync("/app/workspace") ? "/app/workspace" : path.resolve(__dirname, "..");
const providerScript = fs.existsSync("/services/provider-sim/src/server.js")
  ? "/services/provider-sim/src/server.js"
  : path.resolve(workspaceDir, "..", "provider-sim", "src", "server.js");
let providerPort;
let servicePort;
let providerBaseUrl;
let serviceBaseUrl;
const triageKeys = ["ticket_id", "status", "queue", "intent", "recommended_action", "evidence", "escalation", "source"];
const reviewKeys = ["ticket_id", "disposition", "review_note", "evidence", "escalation_reason", "source"];

async function freePort() {
  const server = net.createServer();
  await once(server.listen(0, "127.0.0.1"), "listening");
  const { port } = server.address();
  await new Promise((resolve, reject) => server.close((error) => (error ? reject(error) : resolve())));
  return port;
}

async function waitForServer(url) {
  const deadline = Date.now() + 10000;
  while (Date.now() < deadline) {
    try {
      const response = await fetch(url);
      if (response.ok) {
        return;
      }
    } catch (_error) {
      // Server is still starting.
    }
    await new Promise((resolve) => setTimeout(resolve, 100));
  }
  throw new Error(`timed out waiting for ${url}`);
}

async function startNodeProcess(scriptPath, env) {
  const child = spawn(process.execPath, [scriptPath], {
    cwd: workspaceDir,
    env: {
      ...process.env,
      ...env
    },
    stdio: ["ignore", "pipe", "pipe"]
  });

  child.stdout.setEncoding("utf8");
  child.stderr.setEncoding("utf8");
  return child;
}

async function runNodeScript(scriptPath, env) {
  const child = await startNodeProcess(scriptPath, env);
  const [code] = await once(child, "exit");
  if (code !== 0) {
    throw new Error(`${scriptPath} exited with code ${code}`);
  }
}

async function stopProcess(child) {
  if (!child || child.exitCode !== null) {
    return;
  }
  child.kill("SIGTERM");
  await once(child, "exit");
}

async function requestJson(route, payload) {
  const response = await fetch(`${serviceBaseUrl}${route}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload)
  });
  return {
    status: response.status,
    body: await response.json()
  };
}

let providerProcess;
let serviceProcess;
test.before(async () => {
  await runNodeScript(`${workspaceDir}/scripts/reset_runtime_state.js`, {});
  providerPort = await freePort();
  servicePort = await freePort();
  providerBaseUrl = `http://127.0.0.1:${providerPort}`;
  serviceBaseUrl = `http://127.0.0.1:${servicePort}`;

  providerProcess = await startNodeProcess(providerScript, {
    PORT: String(providerPort),
    DATA_DIR: `${workspaceDir}/data`,
    STATE_DIR: `${workspaceDir}/state`
  });
  await waitForServer(`${providerBaseUrl}/health`);

  serviceProcess = await startNodeProcess(`${workspaceDir}/server.js`, {
    PORT: String(servicePort),
    PROVIDER_BASE_URL: providerBaseUrl,
    DATA_DIR: `${workspaceDir}/data`,
    STATE_DIR: `${workspaceDir}/state`
  });
  await waitForServer(`${serviceBaseUrl}/health`);
});

test.after(async () => {
  await stopProcess(serviceProcess);
  await stopProcess(providerProcess);
});

test("triage returns the expected contract shape in sandbox and live modes", async () => {
  const sandboxResponse = await requestJson("/api/v1/triage", { mode: "sandbox", ticket_id: "bank_003" });
  const liveResponse = await requestJson("/api/v1/triage", { mode: "live", ticket_id: "bank_003" });

  assert.equal(sandboxResponse.status, 200);
  assert.equal(liveResponse.status, 200);

  assert.deepEqual(Object.keys(sandboxResponse.body.data).sort(), triageKeys.slice().sort());
  assert.deepEqual(Object.keys(liveResponse.body.data).sort(), triageKeys.slice().sort());
});

test("live batch triage keeps every ticket in the response payload", async () => {
  const response = await requestJson("/api/v1/triage/batch", {
    mode: "live",
    ticket_ids: ["bank_001", "bank_003", "bank_005"]
  });

  assert.equal(response.status, 200);
  assert.equal(response.body.summary.total, 3);
  assert.equal(response.body.summary.processed, 3);
  assert.equal(response.body.summary.success_count, 1);
  assert.equal(response.body.summary.escalated_count, 1);
  assert.equal(response.body.summary.failed_count, 1);
  assert.equal(response.body.results.length, 3);
  assert.deepEqual(
    response.body.results.map((row) => [row.ticket_id, row.status]),
    [
      ["bank_001", "success"],
      ["bank_003", "escalated"],
      ["bank_005", "failed"]
    ]
  );
  assert.deepEqual(response.body.results[2].error, {
    code: "provider_temporarily_unavailable",
    message: "The downstream model is temporarily unavailable.",
    retryable: true,
    ticket_id: "bank_005"
  });
});

test("batch triage keeps missing tickets as explicit failed rows instead of aborting the whole request", async () => {
  const response = await requestJson("/api/v1/triage/batch", {
    mode: "live",
    ticket_ids: ["missing_ticket", "bank_001", "bank_005"]
  });

  assert.equal(response.status, 200);
  assert.equal(response.body.summary.total, 3);
  assert.equal(response.body.summary.processed, 3);
  assert.equal(response.body.summary.failed_count, 2);
  assert.equal(response.body.results.length, 3);
  assert.deepEqual(
    response.body.results.map((row) => [row.ticket_id, row.status]),
    [
      ["missing_ticket", "failed"],
      ["bank_001", "success"],
      ["bank_005", "failed"]
    ]
  );
  assert.deepEqual(response.body.results[0].error, {
    code: "ticket_not_found",
    message: "ticket missing_ticket was not found",
    retryable: false,
    ticket_id: "missing_ticket"
  });
  assert.deepEqual(response.body.results[2].error, {
    code: "provider_temporarily_unavailable",
    message: "The downstream model is temporarily unavailable.",
    retryable: true,
    ticket_id: "bank_005"
  });
});

test("review suggestion remains available even when live provider handling is unstable", async () => {
  const response = await requestJson("/api/v1/review-suggestion", { mode: "live", ticket_id: "bank_005" });

  assert.equal(response.status, 200);
  assert.equal(response.body.data.ticket_id, "bank_005");
  assert.equal(typeof response.body.data.review_note, "string");
  assert.equal(response.body.data.disposition, "manual_review");
  assert.deepEqual(response.body.data.evidence, []);
  assert.equal(response.body.data.escalation_reason, "provider_temporarily_unavailable");
});

test("live triage keeps a stable contract when provider results are malformed or partial", async () => {
  const firstResponse = await requestJson("/api/v1/triage", { mode: "live", ticket_id: "bank_003" });
  const secondResponse = await requestJson("/api/v1/triage", { mode: "live", ticket_id: "bank_004" });
  const malformedResponse = await requestJson("/api/v1/triage", { mode: "live", ticket_id: "bank_006" });
  const partialResponse = await requestJson("/api/v1/triage", { mode: "live", ticket_id: "bank_007" });

  assert.equal(firstResponse.status, 200);
  assert.equal(secondResponse.status, 200);
  assert.equal(malformedResponse.status, 200);
  assert.equal(partialResponse.status, 200);

  assert.deepEqual(secondResponse.body.data, {
    ticket_id: "bank_004",
    status: "success",
    queue: "profile-maintenance",
    intent: "beneficiary_not_defined",
    recommended_action: "guide_profile_update_steps",
    evidence: [],
    escalation: {
      required: false,
      reason: null
    },
    source: "live"
  });

  for (const [ticketId, payload] of [
    ["bank_006", malformedResponse.body.data],
    ["bank_007", partialResponse.body.data]
  ]) {
    assert.deepEqual(Object.keys(payload).sort(), triageKeys.slice().sort());
    assert.equal(payload.ticket_id, ticketId);
    assert.equal(payload.status, "success");
    assert.equal(typeof payload.queue, "string");
    assert.equal(typeof payload.intent, "string");
    assert.equal(typeof payload.recommended_action, "string");
    assert.deepEqual(payload.escalation, { required: false, reason: null });
    assert.ok(Array.isArray(payload.evidence));
    assert.equal(payload.source, "live");
  }
});

test("live review keeps a stable contract when provider results are malformed or partial", async () => {
  const malformedResponse = await requestJson("/api/v1/review-suggestion", { mode: "live", ticket_id: "bank_006" });
  const partialResponse = await requestJson("/api/v1/review-suggestion", { mode: "live", ticket_id: "bank_007" });

  assert.equal(malformedResponse.status, 200);
  assert.equal(partialResponse.status, 200);

  for (const [ticketId, payload] of [
    ["bank_006", malformedResponse.body.data],
    ["bank_007", partialResponse.body.data]
  ]) {
    assert.deepEqual(Object.keys(payload).sort(), reviewKeys.slice().sort());
    assert.equal(payload.ticket_id, ticketId);
    assert.equal(typeof payload.disposition, "string");
    assert.equal(typeof payload.review_note, "string");
    assert.ok(Array.isArray(payload.evidence));
    assert.equal(payload.escalation_reason, null);
    assert.equal(payload.source, "live");
  }
});

test("service recreates runtime state on demand when the state file is missing", async () => {
  const runtimeStatePath = path.join(workspaceDir, "state", "runtime_state.json");
  fs.rmSync(runtimeStatePath, { force: true });

  const response = await requestJson("/api/v1/triage", { mode: "sandbox", ticket_id: "bank_001" });

  assert.equal(response.status, 200);
  assert.equal(response.body.data.ticket_id, "bank_001");
  assert.equal(fs.existsSync(runtimeStatePath), true);
});
