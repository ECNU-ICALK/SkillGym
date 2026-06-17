const express = require("express");
const fs = require("fs");
const path = require("path");

const app = express();
app.use(express.json());

const dataDir = process.env.DATA_DIR || "/app/workspace/data";
const stateDir = process.env.STATE_DIR || "/app/workspace/state";

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

function ticketCatalog() {
  const rows = [
    ...readJsonl(path.join(dataDir, "tickets", "banking77_curated.jsonl")),
    ...readJsonl(path.join(dataDir, "tickets", "clinc150_oos_curated.jsonl"))
  ];
  const out = new Map();
  for (const row of rows) {
    out.set(row.id, row);
  }
  return out;
}

function policies() {
  return readJson(path.join(dataDir, "policies", "queue_policies.json"));
}

function appendProviderRequest(entry) {
  const current = readJson(runtimeStatePath());
  current.provider_requests.push({
    at: new Date().toISOString(),
    ...entry
  });
  writeJson(runtimeStatePath(), current);
}

function providerClassification(ticketId) {
  const ticket = ticketCatalog().get(ticketId);
  if (!ticket) {
    return { error: { status: 404, code: "ticket_not_found", message: `ticket ${ticketId} was not found`, retryable: false } };
  }
  const rule = policies().intents[ticket.expected_intent];
  if (!rule) {
    return { error: { status: 500, code: "policy_not_found", message: `policy missing for ${ticket.expected_intent}`, retryable: false } };
  }
  if (ticket.live_failure_mode === "invalid_json") {
    return {
      malformed: {
        status: 502,
        body: "{invalid-json"
      }
    };
  }
  if (ticket.live_failure_mode === "retryable") {
    return {
      error: {
        status: 503,
        code: "provider_temporarily_unavailable",
        message: "The downstream model is temporarily unavailable.",
        retryable: true
      }
    };
  }
  if (ticket.live_failure_mode === "invalid_payload") {
    return {
      data: {
        ticket_id: ticket.id,
        status: rule.escalation_reason ? "needs_human" : "success",
        queue: rule.queue,
        intent: ticket.expected_intent,
        next_step: rule.recommended_action,
        evidence: null,
        escalationReason: rule.escalation_reason || null
      }
    };
  }
  return {
    data: {
      ticket_id: ticket.id,
      status: rule.escalation_reason ? "escalated" : "success",
      queue: rule.queue,
      intent: ticket.expected_intent,
      recommended_action: rule.recommended_action,
      evidence: rule.evidence,
      escalation_reason: rule.escalation_reason || null
    }
  };
}

function providerReview(ticketId) {
  const classification = providerClassification(ticketId);
  if (classification.error) {
    return classification;
  }
  if (classification.data && classification.data.next_step) {
    const ticket = ticketCatalog().get(ticketId);
    const rule = policies().intents[ticket.expected_intent];
    return {
      data: {
        ticket_id: ticketId,
        disposition: rule.review_disposition,
        note: rule.review_note,
        evidence: null,
        escalationReason: rule.escalation_reason || null
      }
    };
  }
  const rule = policies().intents[classification.data.intent];
  return {
    data: {
      ticket_id: ticketId,
      disposition: rule.review_disposition,
      review_note: rule.review_note,
      evidence: rule.review_evidence,
      escalation_reason: rule.escalation_reason || null
    }
  };
}

function respond(result, route, ticketId, res) {
  appendProviderRequest({ route, ticket_id: ticketId });
  if (result.malformed) {
    res.status(result.malformed.status).type("application/json").send(result.malformed.body);
    return;
  }
  if (result.error) {
    res.status(result.error.status).json({ error: result.error });
    return;
  }
  res.status(200).json({ data: result.data });
}

app.get("/health", (_req, res) => {
  res.json({ ok: true });
});

app.post("/v1/classify", (req, res) => {
  const ticketId = req.body && req.body.ticket_id;
  respond(providerClassification(ticketId), "/v1/classify", ticketId, res);
});

app.post("/v1/review", (req, res) => {
  const ticketId = req.body && req.body.ticket_id;
  respond(providerReview(ticketId), "/v1/review", ticketId, res);
});

const port = Number(process.env.PORT || "3050");
app.listen(port, "0.0.0.0", () => {
  process.stdout.write(`provider-sim listening on ${port}\n`);
});
