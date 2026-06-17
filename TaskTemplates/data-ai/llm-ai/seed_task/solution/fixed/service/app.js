const express = require("express");
const { getSandboxReviewCases, getSandboxTriageCases, getTicket, recordServiceRequest } = require("./dataStore");

const app = express();

let requestCounter = 0;

function nextRequestId() {
  requestCounter += 1;
  return `req_${Date.now()}_${requestCounter}`;
}

class ApiError extends Error {
  constructor(status, code, message, extra = {}) {
    super(message);
    this.status = status;
    this.code = code;
    this.extra = extra;
  }
}

function buildErrorPayload(error, mode, ticketId = null) {
  return {
    request_id: nextRequestId(),
    mode,
    error: {
      code: error.code,
      message: error.message,
      retryable: Boolean(error.extra.retryable),
      ticket_id: ticketId
    }
  };
}

function validateMode(mode) {
  if (!["sandbox", "live"].includes(mode)) {
    throw new ApiError(422, "invalid_mode", "mode must be sandbox or live");
  }
}

function validateTicketId(ticketId) {
  if (typeof ticketId !== "string" || !ticketId.trim()) {
    throw new ApiError(422, "invalid_ticket_id", "ticket_id is required");
  }
  const normalizedTicketId = ticketId.trim();
  const ticket = getTicket(normalizedTicketId);
  if (!ticket) {
    throw new ApiError(404, "ticket_not_found", `ticket ${normalizedTicketId} was not found`);
  }
  return normalizedTicketId;
}

function canonicalTriage(caseDef, source) {
  return {
    ticket_id: caseDef.ticket_id,
    status: caseDef.status,
    queue: caseDef.queue,
    intent: caseDef.intent,
    recommended_action: caseDef.recommended_action,
    evidence: Array.isArray(caseDef.evidence) ? caseDef.evidence : [],
    escalation: {
      required: Boolean(caseDef.escalation_reason),
      reason: caseDef.escalation_reason || null
    },
    source
  };
}

function canonicalReview(caseDef, source) {
  return {
    ticket_id: caseDef.ticket_id,
    disposition: caseDef.disposition,
    review_note: caseDef.review_note,
    evidence: Array.isArray(caseDef.evidence) ? caseDef.evidence : [],
    escalation_reason: caseDef.escalation_reason || null,
    source
  };
}

function isValidTriagePayload(payload) {
  return Boolean(
    payload &&
      typeof payload.ticket_id === "string" &&
      ["success", "escalated", "failed"].includes(payload.status) &&
      typeof payload.queue === "string" &&
      typeof payload.intent === "string" &&
      typeof payload.recommended_action === "string" &&
      Array.isArray(payload.evidence) &&
      Object.prototype.hasOwnProperty.call(payload, "escalation_reason")
  );
}

function isValidReviewPayload(payload) {
  return Boolean(
    payload &&
      typeof payload.ticket_id === "string" &&
      typeof payload.disposition === "string" &&
      typeof payload.review_note === "string" &&
      Array.isArray(payload.evidence) &&
      Object.prototype.hasOwnProperty.call(payload, "escalation_reason")
  );
}

async function postProvider(path, payload, validator) {
  const baseUrl = process.env.PROVIDER_BASE_URL || "http://127.0.0.1:3050";
  let response;
  try {
    response = await fetch(`${baseUrl}${path}`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload)
    });
  } catch (_error) {
    throw new ApiError(502, "provider_unreachable", "provider request failed before receiving a response", { retryable: true });
  }

  const rawBody = await response.text();
  let body = {};
  try {
    body = rawBody ? JSON.parse(rawBody) : {};
  } catch (_error) {
    throw new ApiError(502, "provider_invalid_response", "provider returned invalid JSON", { retryable: true });
  }

  if (!response.ok) {
    throw new ApiError(
      response.status,
      body.error && body.error.code ? body.error.code : "provider_error",
      body.error && body.error.message ? body.error.message : "provider request failed",
      { retryable: Boolean(body.error && body.error.retryable) }
    );
  }

  if (!validator(body.data)) {
    throw new ApiError(502, "provider_invalid_payload", "provider returned a payload that does not satisfy the contract", { retryable: true });
  }

  return body.data;
}

function readSandboxTriage(ticketId, source) {
  const caseDef = getSandboxTriageCases()[ticketId];
  if (!caseDef) {
    throw new ApiError(404, "sandbox_case_not_found", `sandbox case missing for ${ticketId}`);
  }
  if (caseDef.status === "failed") {
    throw new ApiError(503, caseDef.error.code, caseDef.error.message, { retryable: caseDef.error.retryable });
  }
  return canonicalTriage(caseDef, source);
}

function readSandboxReview(ticketId, source) {
  const caseDef = getSandboxReviewCases()[ticketId];
  if (!caseDef) {
    throw new ApiError(404, "sandbox_case_not_found", `sandbox review case missing for ${ticketId}`);
  }
  return canonicalReview(caseDef, source);
}

function batchFailureRow(ticketId, error) {
  const apiError = error instanceof ApiError ? error : new ApiError(500, "internal_error", "unexpected error");
  return {
    ticket_id: ticketId,
    status: "failed",
    error: {
      code: apiError.code,
      message: apiError.message,
      retryable: Boolean(apiError.extra.retryable),
      ticket_id: ticketId
    }
  };
}

async function triageTicket(mode, ticketId) {
  if (mode === "sandbox") {
    return readSandboxTriage(ticketId, "sandbox");
  }
  try {
    return canonicalTriage(await postProvider("/v1/classify", { ticket_id: ticketId }, isValidTriagePayload), "live");
  } catch (error) {
    const apiError = error instanceof ApiError ? error : new ApiError(500, "internal_error", "unexpected error");
    if (apiError.code === "provider_invalid_response" || apiError.code === "provider_invalid_payload" || apiError.extra.retryable) {
      return readSandboxTriage(ticketId, "live");
    }
    throw apiError;
  }
}

async function buildReview(mode, ticketId) {
  if (mode === "sandbox") {
    return readSandboxReview(ticketId, "sandbox");
  }
  try {
    return canonicalReview(await postProvider("/v1/review", { ticket_id: ticketId }, isValidReviewPayload), "live");
  } catch (error) {
    const apiError = error instanceof ApiError ? error : new ApiError(500, "internal_error", "unexpected error");
    if (apiError.code === "provider_invalid_response" || apiError.code === "provider_invalid_payload" || apiError.extra.retryable) {
      return readSandboxReview(ticketId, "live");
    }
    throw apiError;
  }
}

function batchSummary(results, total) {
  return {
    total,
    processed: results.length,
    success_count: results.filter((row) => row.status === "success").length,
    escalated_count: results.filter((row) => row.status === "escalated").length,
    failed_count: results.filter((row) => row.status === "failed").length
  };
}

app.get("/health", (_req, res) => {
  res.json({ ok: true });
});

app.use(express.json());

app.post("/api/v1/triage", async (req, res) => {
  try {
    const { mode, ticket_id: ticketId } = req.body || {};
    validateMode(mode);
    const normalizedTicketId = validateTicketId(ticketId);
    recordServiceRequest({ route: "/api/v1/triage", mode, ticket_id: normalizedTicketId });
    res.status(200).json({ request_id: nextRequestId(), mode, data: await triageTicket(mode, normalizedTicketId) });
  } catch (error) {
    const apiError = error instanceof ApiError ? error : new ApiError(500, "internal_error", "unexpected error");
    res.status(apiError.status).json(buildErrorPayload(apiError, req.body && req.body.mode ? req.body.mode : "unknown", req.body && req.body.ticket_id ? req.body.ticket_id : null));
  }
});

app.post("/api/v1/triage/batch", async (req, res) => {
  try {
    const { mode, ticket_ids: ticketIds } = req.body || {};
    validateMode(mode);
    if (!Array.isArray(ticketIds) || ticketIds.length === 0) {
      throw new ApiError(422, "invalid_ticket_ids", "ticket_ids must be a non-empty array");
    }
    recordServiceRequest({ route: "/api/v1/triage/batch", mode, ticket_ids: ticketIds });
    const results = [];
    for (const rawTicketId of ticketIds) {
      let normalizedTicketId = rawTicketId;
      try {
        normalizedTicketId = validateTicketId(rawTicketId);
        results.push(await triageTicket(mode, normalizedTicketId));
      } catch (error) {
        results.push(batchFailureRow(typeof normalizedTicketId === "string" ? normalizedTicketId : rawTicketId, error));
      }
    }
    res.status(200).json({ request_id: nextRequestId(), mode, summary: batchSummary(results, ticketIds.length), results });
  } catch (error) {
    const apiError = error instanceof ApiError ? error : new ApiError(500, "internal_error", "unexpected error");
    res.status(apiError.status).json(buildErrorPayload(apiError, req.body && req.body.mode ? req.body.mode : "unknown"));
  }
});

app.post("/api/v1/review-suggestion", async (req, res) => {
  try {
    const { mode, ticket_id: ticketId } = req.body || {};
    validateMode(mode);
    const normalizedTicketId = validateTicketId(ticketId);
    recordServiceRequest({ route: "/api/v1/review-suggestion", mode, ticket_id: normalizedTicketId });
    res.status(200).json({ request_id: nextRequestId(), mode, data: await buildReview(mode, normalizedTicketId) });
  } catch (error) {
    const apiError = error instanceof ApiError ? error : new ApiError(500, "internal_error", "unexpected error");
    res.status(apiError.status).json(buildErrorPayload(apiError, req.body && req.body.mode ? req.body.mode : "unknown", req.body && req.body.ticket_id ? req.body.ticket_id : null));
  }
});

app.use((error, req, res, next) => {
  if (error instanceof SyntaxError && error.status === 400 && "body" in error) {
    const apiError = new ApiError(400, "invalid_json_body", "request body must be valid JSON");
    res.status(apiError.status).json(buildErrorPayload(apiError, req.body && req.body.mode ? req.body.mode : "unknown"));
    return;
  }
  next(error);
});

module.exports = app;
