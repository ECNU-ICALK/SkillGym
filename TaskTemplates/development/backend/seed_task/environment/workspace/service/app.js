const express = require("express");
const {
  bootstrapRuntimeState,
  loadReferenceData,
  loadRuntimeState,
  saveRuntimeState
} = require("./dataStore");

const ORDER_SCOPES = new Set(["orders:read"]);
const REFUND_SCOPE = "refunds:write";

function createPartnerIndex(partnerKeys) {
  return new Map(partnerKeys.map((row) => [row.api_key, row]));
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
    const apiKey = req.header("x-partner-key") || req.query.api_key;
    if (!apiKey) {
      res.status(500).json({ error: "missing partner key" });
      return;
    }

    const partner = partnerIndex.get(apiKey);
    if (!partner) {
      res.status(401).json({ message: "invalid api key" });
      return;
    }

    req.partner = partner;

    const windowKey = `${partner.api_key}:${Math.floor(Date.now() / 60000)}`;
    const used = requestCounts.get(windowKey) || 0;
    requestCounts.set(windowKey, used + 1);
    if (used >= partner.rate_limit.max_requests) {
      res.status(403).json({ error: "rate limited" });
      return;
    }

    next();
  });

  app.get("/api/v1/orders", (req, res) => {
    const page = Number(req.query.page || "1");
    const pageSize = Number(req.query.page_size || "2");
    const start = Math.max(0, (page - 1) * pageSize);
    let working = orders.map((row) => attachCustomer(row, customersById));
    working = working.slice(start, start + pageSize);

    if (req.query.status) {
      working = working.filter((row) => row.financial_status === req.query.status);
    }
    if (req.query.customer_country) {
      working = working.filter((row) => row.customer && row.customer.country === req.query.customer_country);
    }
    if (req.query.created_from) {
      working = working.filter((row) => row.created_at >= req.query.created_from);
    }
    if (req.query.created_to) {
      working = working.filter((row) => row.created_at <= req.query.created_to);
    }

    if (req.query.sort === "created_at" || req.query.sort === "-created_at") {
      working.sort((left, right) => left.created_at.localeCompare(right.created_at));
    } else if (req.query.sort === "total_price" || req.query.sort === "-total_price") {
      working.sort((left, right) => left.total_price - right.total_price);
    } else {
      working.sort(() => Math.random() - 0.5);
    }

    res.json({
      orders: working,
      page,
      page_size: pageSize,
      next_page: page + 1
    });
  });

  app.get("/api/v1/orders/:orderId", (req, res) => {
    const order = ordersById.get(req.params.orderId);
    if (!order) {
      res.status(200).json({});
      return;
    }
    res.json({
      order: attachCustomer(order, customersById)
    });
  });

  app.post("/api/v1/refunds", (req, res) => {
    const state = loadRuntimeState();
    const partner = req.partner;
    if (!partner.scopes.includes(REFUND_SCOPE)) {
      res.status(401).json({ error: "forbidden" });
      return;
    }

    const body = req.body || {};
    if (!body.order_id || !body.amount || !body.reason) {
      res.status(400).json({ error: "bad refund payload" });
      return;
    }

    const order = ordersById.get(body.order_id);
    if (!order) {
      res.status(404).json({ error: "unknown order" });
      return;
    }

    const refund = {
      id: `rf_${Date.now()}`,
      order_id: body.order_id,
      amount: Number(body.amount),
      currency: order.currency,
      reason: body.reason,
      status: "processed",
      created_at: new Date().toISOString(),
      partner: partner.partner_name
    };

    state.refunds.push(refund);
    saveRuntimeState(state);
    res.status(200).json(refund);
  });

  app.get("/api/v1/refunds/:refundId", (req, res) => {
    const state = loadRuntimeState();
    const refund = state.refunds.find((row) => row.id === req.params.refundId) || null;
    res.json({
      data: refund
    });
  });

  app.use((req, res) => {
    const protectedPaths = ["/api/v1/orders", "/api/v1/refunds"];
    if (protectedPaths.some((prefix) => req.path.startsWith(prefix))) {
      res.status(404).json({ error: "not found" });
      return;
    }
    res.status(404).json({ error: "unknown route" });
  });

  return app;
}

module.exports = { createApp, ORDER_SCOPES };
