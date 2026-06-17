const express = require("express");
const {
  bootstrapRuntimeState,
  fingerprintPayload,
  loadReferenceData,
  loadRuntimeState,
  saveRuntimeState
} = require("./dataStore");

const ALLOWED_REASONS = new Set(["customer_request", "duplicate", "damaged", "fraud_review"]);

function errorBody(code, message, details = []) {
  return {
    error: {
      code,
      message,
      details
    }
  };
}

function listSuccess(data, meta) {
  return { data, meta };
}

function parsePositiveInteger(value, fallback) {
  const parsed = Number(value);
  if (!Number.isInteger(parsed) || parsed <= 0) {
    return fallback;
  }
  return parsed;
}

function createPartnerIndex(partnerKeys) {
  return new Map(partnerKeys.map((row) => [row.api_key, row]));
}

function logRequest(req) {
  const payload = {
    timestamp: new Date().toISOString(),
    method: req.method,
    path: req.path,
    query: req.query,
    partner_key: req.header("x-partner-key") || null
  };
  process.stdout.write(JSON.stringify(payload) + "\n");
}

function attachCustomer(order, customersById) {
  const customer = customersById.get(order.customer_id) || null;
  return {
    ...order,
    customer: customer
      ? {
          id: customer.id,
          name: customer.name,
          email: customer.email,
          country: customer.default_address.country_code
        }
      : null
  };
}

function calculateOrderFinancials(order, state) {
  const matching = state.refunds.filter((refund) => refund.order_id === order.id && refund.status === "processed");
  const refundedAmount = matching.reduce((sum, refund) => sum + Number(refund.amount), 0);
  const remaining = Math.max(0, Number(order.total_price) - refundedAmount);
  let financialStatus = order.financial_status;
  if (order.cancelled_at) {
    financialStatus = "cancelled";
  } else if (remaining === 0) {
    financialStatus = "refunded";
  } else if (refundedAmount > 0) {
    financialStatus = "partially_refunded";
  }
  return {
    refunded_amount: Number(refundedAmount.toFixed(2)),
    refundable_amount: Number(remaining.toFixed(2)),
    financial_status: financialStatus
  };
}

function enrichOrder(order, customersById, state) {
  const attached = attachCustomer(order, customersById);
  return {
    ...attached,
    ...calculateOrderFinancials(order, state)
  };
}

function sortRows(rows, sort) {
  const reverse = sort.startsWith("-");
  const keyName = reverse ? sort.slice(1) : sort;
  const allowed = new Set(["created_at", "total_price"]);
  const sortKey = allowed.has(keyName) ? keyName : "created_at";
  rows.sort((left, right) => {
    const leftValue = left[sortKey];
    const rightValue = right[sortKey];
    if (leftValue === rightValue) {
      return left.id.localeCompare(right.id);
    }
    if (sortKey === "total_price") {
      return Number(leftValue) - Number(rightValue);
    }
    return String(leftValue).localeCompare(String(rightValue));
  });
  if (reverse) {
    rows.reverse();
  }
}

function remainingQuota(partner, countBefore) {
  return Math.max(0, partner.rate_limit.max_requests - countBefore);
}

function createApp() {
  bootstrapRuntimeState();

  const app = express();
  app.use(express.json());

  const { orders, customers, partnerKeys } = loadReferenceData();
  const customersById = new Map(customers.map((row) => [row.id, row]));
  const ordersById = new Map(orders.map((row) => [row.id, row]));
  const partnerIndex = createPartnerIndex(partnerKeys);
  const requestCounts = new Map();

  app.use((req, _res, next) => {
    logRequest(req);
    next();
  });

  app.get("/health", (_req, res) => {
    res.json({ ok: true, service: "partner-order-refund-api" });
  });

  app.use((req, res, next) => {
    if (req.path === "/health") {
      next();
      return;
    }

    const apiKey = req.header("x-partner-key");
    if (!apiKey) {
      res.status(401).json(errorBody("auth_required", "A partner API key is required."));
      return;
    }

    const partner = partnerIndex.get(apiKey);
    if (!partner) {
      res.status(401).json(errorBody("invalid_api_key", "The supplied partner API key is not recognized."));
      return;
    }

    req.partner = partner;
    const windowKey = `${partner.api_key}:${Math.floor(Date.now() / (partner.rate_limit.window_seconds * 1000))}`;
    const usedBefore = requestCounts.get(windowKey) || 0;
    const remainingBefore = remainingQuota(partner, usedBefore);
    res.setHeader("X-RateLimit-Limit", String(partner.rate_limit.max_requests));
    res.setHeader("X-RateLimit-Remaining", String(Math.max(0, remainingBefore - 1)));
    res.setHeader("X-RateLimit-Window-Seconds", String(partner.rate_limit.window_seconds));

    if (usedBefore >= partner.rate_limit.max_requests) {
      res.setHeader("X-RateLimit-Remaining", "0");
      res.setHeader("Retry-After", String(partner.rate_limit.window_seconds));
      res.status(429).json(errorBody("rate_limited", "Rate limit exceeded for this partner key."));
      return;
    }

    requestCounts.set(windowKey, usedBefore + 1);
    next();
  });

  app.get("/api/v1/orders", (req, res) => {
    const partner = req.partner;
    if (!partner.scopes.includes("orders:read")) {
      res.status(403).json(errorBody("insufficient_scope", "This partner key cannot read orders."));
      return;
    }

    const page = parsePositiveInteger(req.query.page, 1);
    const pageSize = Math.min(50, parsePositiveInteger(req.query.page_size, 20));
    const status = typeof req.query.status === "string" ? req.query.status : null;
    const customerCountry = typeof req.query.customer_country === "string" ? req.query.customer_country : null;
    const createdFrom = typeof req.query.created_from === "string" ? req.query.created_from : null;
    const createdTo = typeof req.query.created_to === "string" ? req.query.created_to : null;
    const sort = typeof req.query.sort === "string" ? req.query.sort : "-created_at";

    const state = loadRuntimeState();
    let rows = orders.map((order) => enrichOrder(order, customersById, state));
    if (status) {
      rows = rows.filter((row) => row.financial_status === status);
    }
    if (customerCountry) {
      rows = rows.filter((row) => row.customer && row.customer.country === customerCountry);
    }
    if (createdFrom) {
      rows = rows.filter((row) => row.created_at >= createdFrom);
    }
    if (createdTo) {
      rows = rows.filter((row) => row.created_at <= createdTo);
    }

    sortRows(rows, sort);
    const totalItems = rows.length;
    const totalPages = totalItems === 0 ? 0 : Math.ceil(totalItems / pageSize);
    const start = Math.max(0, (page - 1) * pageSize);
    const sliced = rows.slice(start, start + pageSize);

    res.json(
      listSuccess(
        sliced,
        {
          resource: "orders",
          pagination: {
            page,
            page_size: pageSize,
            total_items: totalItems,
            total_pages: totalPages,
            has_next: page < totalPages
          }
        }
      )
    );
  });

  app.get("/api/v1/orders/:orderId", (req, res) => {
    const partner = req.partner;
    if (!partner.scopes.includes("orders:read")) {
      res.status(403).json(errorBody("insufficient_scope", "This partner key cannot read orders."));
      return;
    }

    const order = ordersById.get(req.params.orderId);
    if (!order) {
      res.status(404).json(errorBody("order_not_found", "The requested order does not exist."));
      return;
    }

    const state = loadRuntimeState();
    res.json(
      listSuccess(
        enrichOrder(order, customersById, state),
        {
          resource: "order"
        }
      )
    );
  });

  app.post("/api/v1/refunds", (req, res) => {
    const partner = req.partner;
    if (!partner.scopes.includes("refunds:write")) {
      res.status(403).json(errorBody("insufficient_scope", "This partner key cannot create refunds."));
      return;
    }

    const idempotencyKey = req.header("idempotency-key");
    const body = req.body || {};
    const validationErrors = [];
    if (!idempotencyKey) {
      validationErrors.push({ field: "Idempotency-Key", issue: "required" });
    }
    if (typeof body.order_id !== "string" || !body.order_id) {
      validationErrors.push({ field: "order_id", issue: "required" });
    }
    if (typeof body.amount !== "number" || !(body.amount > 0)) {
      validationErrors.push({ field: "amount", issue: "must_be_positive_number" });
    }
    if (typeof body.reason !== "string" || !ALLOWED_REASONS.has(body.reason)) {
      validationErrors.push({ field: "reason", issue: "unsupported_reason" });
    }
    if (validationErrors.length > 0) {
      res.status(422).json(errorBody("validation_error", "Refund payload is invalid.", validationErrors));
      return;
    }

    const order = ordersById.get(body.order_id);
    if (!order) {
      res.status(404).json(errorBody("order_not_found", "The requested order does not exist."));
      return;
    }

    const state = loadRuntimeState();
    const financials = calculateOrderFinancials(order, state);
    if (!["paid", "partially_refunded"].includes(financials.financial_status) || financials.refundable_amount <= 0) {
      res.status(409).json(errorBody("refund_not_allowed", "This order cannot accept a refund in its current state."));
      return;
    }
    if (body.amount > financials.refundable_amount) {
      res.status(409).json(errorBody("refund_not_allowed", "Refund amount exceeds the remaining refundable amount."));
      return;
    }

    const normalizedPayload = {
      order_id: body.order_id,
      amount: Number(body.amount.toFixed(2)),
      reason: body.reason
    };
    const payloadFingerprint = fingerprintPayload(normalizedPayload);
    const existingIdempotency = state.idempotency_records.find((row) => row.key === idempotencyKey);
    if (existingIdempotency) {
      if (existingIdempotency.fingerprint !== payloadFingerprint) {
        res.status(409).json(errorBody("idempotency_conflict", "This idempotency key is already bound to a different payload."));
        return;
      }
      const existingRefund = state.refunds.find((row) => row.id === existingIdempotency.refund_id);
      res.status(200).json(
        listSuccess(existingRefund, {
          resource: "refund",
          idempotent_replay: true
        })
      );
      return;
    }

    const nextIdNumber = state.refunds.reduce((maxValue, row) => {
      const numeric = Number(String(row.id).replace(/^rf_/, ""));
      return Number.isFinite(numeric) ? Math.max(maxValue, numeric) : maxValue;
    }, 2000) + 1;

    const refund = {
      id: `rf_${nextIdNumber}`,
      order_id: body.order_id,
      amount: normalizedPayload.amount,
      currency: order.currency,
      reason: body.reason,
      status: "processed",
      created_at: new Date().toISOString(),
      partner: partner.partner_name
    };

    state.refunds.push(refund);
    state.idempotency_records.push({
      key: idempotencyKey,
      fingerprint: payloadFingerprint,
      refund_id: refund.id
    });
    saveRuntimeState(state);

    res.status(201).json(
      listSuccess(refund, {
        resource: "refund",
        idempotent_replay: false
      })
    );
  });

  app.get("/api/v1/refunds/:refundId", (req, res) => {
    const partner = req.partner;
    if (!partner.scopes.includes("orders:read")) {
      res.status(403).json(errorBody("insufficient_scope", "This partner key cannot read refunds."));
      return;
    }

    const state = loadRuntimeState();
    const refund = state.refunds.find((row) => row.id === req.params.refundId);
    if (!refund) {
      res.status(404).json(errorBody("refund_not_found", "The requested refund does not exist."));
      return;
    }

    res.json(
      listSuccess(refund, {
        resource: "refund"
      })
    );
  });

  app.use((_req, res) => {
    res.status(404).json(errorBody("route_not_found", "The requested route does not exist."));
  });

  return app;
}

module.exports = { createApp };
