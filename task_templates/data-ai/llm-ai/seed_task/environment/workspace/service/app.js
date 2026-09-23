const express = require("express");
const { getPolicies, getSandboxReviewCases, getSandboxTriageCases, getTicket, recordServiceRequest } = require("./dataStore");

const app = express();

class ApiError extends Error {
  constructor(status, code, message, extra = {}) {
    super(message);
    this.status = status;
    this.code = code;
    this.extra = extra;
  }
}

function createRequestId() {
  return `req_${Date.now()}_${Math.random().toString(36).slice(2, 8)}`;
}

function buildErrorDetails(error, ticketId = null) {
  return {
    code: error.code,
    message: error.message,
    retryable: Boolean(error.extra.retryable),
    ticket_id: ticketId
  };
}

function buildErrorPayload(error, mode, ticketId = null) {
  return {
    request_id: createRequestId(),
    mode,
    error: buildErrorDetails(error, ticketId)
  };
}

function normalizeString(value) {
  return typeof value === "string" && value.trim() ? value : null;
}

function normalizeEvidence(value, fallback = []) {
  if (!Array.isArray(value)) {
    return Array.isArray(fallback) ? fallback.slice() : [];
  }
  return value
    .filter((item) => item && typeof item === "object")
    .map((item) => ({
      source_id: normalizeString(item.source_id),
      snippet: normalizeString(item.snippet)
    }))
    .filter((item) => item.source_id && item.snippet);
}

function normalizeTriageStatus(value) {
  if (value === "needs_human") {
    return "escalated";
  }
  return ["success", "escalated", "failed"].includes(value) ? value : null;
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
  const ticket = getTicket(ticketId);
  if (!ticket) {
    throw new ApiError(404, "ticket_not_found", `ticket ${ticketId} was not found`);
  }
  return ticket;
}

function getPolicyBundle(ticketId, ticket = null) {
  const resolvedTicket = ticket || validateTicketId(ticketId);
  const policies = getPolicies();
  const rule = policies.intents[resolvedTicket.expected_intent];
  if (!rule) {
    throw new ApiError(500, "policy_not_found", `policy missing for ${resolvedTicket.expected_intent}`);
  }
  return { ticket: resolvedTicket, rule };
}

function buildTriageResult({
  ticketId,
  status,
  queue = null,
  intent = null,
  recommendedAction = null,
  evidence = [],
  escalationReason = null,
  source,
  error = null
}) {
  const normalizedStatus = normalizeTriageStatus(status) || "failed";
  const reason = normalizeString(escalationReason);
  return {
    ticket_id: ticketId,
    status: normalizedStatus,
    queue: normalizeString(queue),
    intent: normalizeString(intent),
    recommended_action: normalizeString(recommendedAction),
    evidence: normalizeEvidence(evidence),
    escalation: {
      required: normalizedStatus === "escalated" || Boolean(reason),
      reason
    },
    source,
    ...(error ? { error } : {})
  };
}

function buildReviewResult({
  ticketId,
  disposition = null,
  reviewNote = null,
  evidence = [],
  escalationReason = null,
  source
}) {
  return {
    ticket_id: ticketId,
    disposition: normalizeString(disposition),
    review_note: normalizeString(reviewNote),
    evidence: normalizeEvidence(evidence),
    escalation_reason: normalizeString(escalationReason),
    source
  };
}

function sandboxTriageShape(caseDef) {
  return buildTriageResult({
    ticketId: caseDef.ticket_id,
    status: caseDef.status,
    queue: caseDef.queue,
    intent: caseDef.intent,
    recommendedAction: caseDef.recommended_action,
    evidence: caseDef.evidence,
    escalationReason: caseDef.escalation_reason,
    source: "sandbox"
  });
}

function sandboxReviewShape(caseDef) {
  return buildReviewResult({
    ticketId: caseDef.ticket_id,
    disposition: caseDef.disposition,
    reviewNote: caseDef.review_note,
    evidence: caseDef.evidence,
    escalationReason: caseDef.escalation_reason,
    source: "sandbox"
  });
}

function livePolicyTriage(ticketId, ticket = null) {
  const { ticket: resolvedTicket, rule } = getPolicyBundle(ticketId, ticket);
  return buildTriageResult({
    ticketId,
    status: rule.escalation_reason ? "escalated" : "success",
    queue: rule.queue,
    intent: resolvedTicket.expected_intent,
    recommendedAction: rule.recommended_action,
    evidence: rule.evidence,
    escalationReason: rule.escalation_reason,
    source: "live"
  });
}

function livePolicyReview(ticketId, ticket = null) {
  const { rule } = getPolicyBundle(ticketId, ticket);
  return buildReviewResult({
    ticketId,
    disposition: rule.review_disposition,
    reviewNote: rule.review_note,
    evidence: rule.review_evidence,
    escalationReason: rule.escalation_reason,
    source: "live"
  });
}

function normalizeLiveTriage(providerData, fallback) {
  const providerStatus = normalizeTriageStatus(providerData && providerData.status);
  const escalationReason = normalizeString(
    providerData && (providerData.escalation_reason || providerData.escalationReason || fallback.escalation.reason)
  );
  return buildTriageResult({
    ticketId: normalizeString(providerData && providerData.ticket_id) || fallback.ticket_id,
    status: providerStatus || fallback.status,
    queue: normalizeString(providerData && providerData.queue) || fallback.queue,
    intent: normalizeString(providerData && providerData.intent) || fallback.intent,
    recommendedAction:
      normalizeString(providerData && providerData.recommended_action) ||
      normalizeString(providerData && providerData.next_step) ||
      fallback.recommended_action,
    evidence: Array.isArray(providerData && providerData.evidence) ? providerData.evidence : fallback.evidence,
    escalationReason,
    source: "live"
  });
}

function normalizeLiveReview(providerData, fallback) {
  return buildReviewResult({
    ticketId: normalizeString(providerData && providerData.ticket_id) || fallback.ticket_id,
    disposition: normalizeString(providerData && providerData.disposition) || fallback.disposition,
    reviewNote:
      normalizeString(providerData && providerData.review_note) ||
      normalizeString(providerData && providerData.note) ||
      fallback.review_note,
    evidence: Array.isArray(providerData && providerData.evidence) ? providerData.evidence : fallback.evidence,
    escalationReason:
      normalizeString(providerData && (providerData.escalation_reason || providerData.escalationReason)) ||
      fallback.escalation_reason,
    source: "live"
  });
}

async function postProvider(path, payload) {
  const baseUrl = process.env.PROVIDER_BASE_URL || "http://127.0.0.1:3050";
  const response = await fetch(`${baseUrl}${path}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload)
  });

  const rawBody = await response.text();
  let body = {};
  if (rawBody.trim()) {
    try {
      body = JSON.parse(rawBody);
    } catch (_error) {
      throw new ApiError(502, "provider_invalid_json", "provider returned invalid json", {
        retryable: response.status >= 500
      });
    }
  }

  if (!response.ok) {
    const providerError = body && typeof body === "object" ? body.error : null;
    throw new ApiError(
      response.status,
      providerError && providerError.code ? providerError.code : "provider_error",
      providerError && providerError.message ? providerError.message : "provider request failed",
      { retryable: Boolean(providerError && providerError.retryable) || response.status >= 500 }
    );
  }

  if (!body || typeof body !== "object" || !body.data || typeof body.data !== "object") {
    throw new ApiError(502, "provider_invalid_payload", "provider returned an invalid payload", { retryable: true });
  }

  return body.data;
}

function isRecoverableTriageError(error) {
  return error instanceof ApiError && ["provider_invalid_json", "provider_invalid_payload"].includes(error.code);
}

function buildReviewFallbackFromError(ticketId, error, ticket = null) {
  if (isRecoverableTriageError(error)) {
    return livePolicyReview(ticketId, ticket);
  }
  if (error instanceof ApiError && error.code !== "ticket_not_found") {
    return buildReviewResult({
      ticketId,
      disposition: "manual_review",
      reviewNote:
        error.code === "provider_temporarily_unavailable"
          ? "Wait for the downstream service to recover before continuing automated handling."
          : "The automated review chain returned an unstable response and should be checked by a human reviewer.",
      evidence: [],
      escalationReason: error.code,
      source: "live"
    });
  }
  throw error;
}

async function triageTicket(mode, ticketId, ticket = null) {
  if (mode === "sandbox") {
    const cases = getSandboxTriageCases();
    const caseDef = cases[ticketId];
    if (!caseDef) {
      throw new ApiError(404, "sandbox_case_not_found", `sandbox case missing for ${ticketId}`);
    }
    if (caseDef.status === "failed") {
      throw new ApiError(503, caseDef.error.code, caseDef.error.message, { retryable: caseDef.error.retryable });
    }
    return sandboxTriageShape(caseDef);
  }

  const resolvedTicket = ticket || validateTicketId(ticketId);
  const fallback = livePolicyTriage(ticketId, resolvedTicket);
  try {
    const providerData = await postProvider("/v1/classify", { ticket_id: ticketId });
    return normalizeLiveTriage(providerData, fallback);
  } catch (error) {
    if (isRecoverableTriageError(error)) {
      return fallback;
    }
    throw error;
  }
}

async function buildReview(mode, ticketId, ticket = null) {
  if (mode === "sandbox") {
    const cases = getSandboxReviewCases();
    const caseDef = cases[ticketId];
    if (!caseDef) {
      throw new ApiError(404, "sandbox_case_not_found", `sandbox review case missing for ${ticketId}`);
    }
    return sandboxReviewShape(caseDef);
  }

  const resolvedTicket = ticket || validateTicketId(ticketId);
  const fallback = livePolicyReview(ticketId, resolvedTicket);
  try {
    const providerData = await postProvider("/v1/review", { ticket_id: ticketId });
    return normalizeLiveReview(providerData, fallback);
  } catch (error) {
    return buildReviewFallbackFromError(ticketId, error, resolvedTicket);
  }
}

function buildFailedBatchRow(mode, ticketId, error) {
  return buildTriageResult({
    ticketId,
    status: "failed",
    source: mode,
    error: buildErrorDetails(error, ticketId)
  });
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
    const ticket = validateTicketId(ticketId);
    recordServiceRequest({ route: "/api/v1/triage", mode, ticket_id: ticketId });
    res.status(200).json({ request_id: createRequestId(), mode, data: await triageTicket(mode, ticketId, ticket) });
  } catch (error) {
    const apiError = error instanceof ApiError ? error : new ApiError(500, "internal_error", "unexpected error");
    res
      .status(apiError.status)
      .json(buildErrorPayload(apiError, req.body && req.body.mode ? req.body.mode : "unknown", req.body && req.body.ticket_id ? req.body.ticket_id : null));
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
    const results = await Promise.all(
      ticketIds.map(async (rawTicketId) => {
        const ticketId = typeof rawTicketId === "string" ? rawTicketId : null;
        try {
          const ticket = validateTicketId(rawTicketId);
          return await triageTicket(mode, rawTicketId, ticket);
        } catch (error) {
          const apiError = error instanceof ApiError ? error : new ApiError(500, "internal_error", "unexpected error");
          return buildFailedBatchRow(mode, ticketId, apiError);
        }
      })
    );

    res.status(200).json({
      request_id: createRequestId(),
      mode,
      summary: batchSummary(results, ticketIds.length),
      results
    });
  } catch (error) {
    const apiError = error instanceof ApiError ? error : new ApiError(500, "internal_error", "unexpected error");
    res.status(apiError.status).json(buildErrorPayload(apiError, req.body && req.body.mode ? req.body.mode : "unknown"));
  }
});

app.post("/api/v1/review-suggestion", async (req, res) => {
  try {
    const { mode, ticket_id: ticketId } = req.body || {};
    validateMode(mode);
    const ticket = validateTicketId(ticketId);
    recordServiceRequest({ route: "/api/v1/review-suggestion", mode, ticket_id: ticketId });
    res.status(200).json({ request_id: createRequestId(), mode, data: await buildReview(mode, ticketId, ticket) });
  } catch (error) {
    const apiError = error instanceof ApiError ? error : new ApiError(500, "internal_error", "unexpected error");
    res
      .status(apiError.status)
      .json(buildErrorPayload(apiError, req.body && req.body.mode ? req.body.mode : "unknown", req.body && req.body.ticket_id ? req.body.ticket_id : null));
  }
});

module.exports = app;
