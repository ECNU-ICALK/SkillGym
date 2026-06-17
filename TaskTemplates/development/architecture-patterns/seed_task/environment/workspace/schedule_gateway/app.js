const express = require("express");
const { createRegistry } = require("./registry");
const {
  parsePositiveInt,
  requireDateParam,
  requireTimeParam,
  providerSummary,
} = require("./shared");

function createApp({ dataRoot }) {
  const registry = createRegistry({ dataRoot });
  const app = express();

  app.get("/healthz", (_req, res) => {
    res.json({ ok: true });
  });

  app.get("/v1/providers", (_req, res) => {
    const providers = registry.listProviders().map(providerSummary);
    res.json({ providers });
  });

  app.get("/v1/providers/:providerId/stops/search", (req, res) => {
    const provider = registry.mustGetProvider(req.params.providerId);
    const query = String(req.query.q || "").trim();
    if (!query) {
      return res.status(400).json({ error: "q is required" });
    }
    const limit = parsePositiveInt(req.query.limit, 5, 10);
    const matches = provider.searchStops({ query, limit });
    return res.json({
      provider_id: provider.id,
      query,
      limit,
      matches,
    });
  });

  app.get("/v1/providers/:providerId/stops/:stopId/departures", (req, res) => {
    const provider = registry.mustGetProvider(req.params.providerId);
    const serviceDate = requireDateParam(req.query.date);
    const queryTime = requireTimeParam(req.query.time);
    const limit = parsePositiveInt(req.query.limit, 5, 10);
    const response = provider.getDepartures({
      stopId: req.params.stopId,
      serviceDate,
      queryTime,
      limit,
    });
    return res.json({
      provider_id: provider.id,
      stop: response.stop,
      service_date: serviceDate,
      query_time: queryTime,
      departures: response.departures,
    });
  });

  app.get("/v1/providers/:providerId/routes/:routeId/service-window", (req, res) => {
    const provider = registry.mustGetProvider(req.params.providerId);
    const serviceDate = requireDateParam(req.query.date);
    const summary = provider.getServiceWindow({
      routeId: req.params.routeId,
      serviceDate,
    });
    return res.json({
      provider_id: provider.id,
      route: summary.route,
      service_date: serviceDate,
      service_window: summary.service_window,
    });
  });

  app.use((error, _req, res, _next) => {
    if (error && error.statusCode) {
      return res.status(error.statusCode).json({ error: error.message });
    }
    return res.status(500).json({ error: "internal server error" });
  });

  return app;
}

module.exports = {
  createApp,
};
