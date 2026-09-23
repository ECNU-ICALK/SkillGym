const fs = require("fs");
const path = require("path");
const { createRegistry } = require("./registry");
const { providerSummary, readJson } = require("./shared");

function buildQueryResult(provider, query) {
  if (query.kind === "stop_search") {
    return {
      kind: query.kind,
      query,
      result: {
        provider_id: provider.id,
        query: query.query,
        limit: query.limit,
        matches: provider.searchStops({ query: query.query, limit: query.limit }),
      },
    };
  }

  if (query.kind === "departures") {
    const result = provider.getDepartures({
      stopId: query.stop_id,
      serviceDate: query.date,
      queryTime: query.time,
      limit: query.limit,
    });
    return {
      kind: query.kind,
      query,
      result: {
        provider_id: provider.id,
        stop: result.stop,
        service_date: query.date,
        query_time: query.time,
        departures: result.departures,
      },
    };
  }

  if (query.kind === "service_window") {
    const result = provider.getServiceWindow({
      routeId: query.route_id,
      serviceDate: query.date,
    });
    return {
      kind: query.kind,
      query,
      result: {
        provider_id: provider.id,
        route: result.route,
        service_date: query.date,
        service_window: result.service_window,
      },
    };
  }

  throw new Error(`unsupported query kind: ${query.kind}`);
}

function buildAudit(dataRoot) {
  const seed = readJson(path.join(dataRoot, "seed_queries.json"));
  const registry = createRegistry({ dataRoot });
  const provider = registry.mustGetProvider(seed.provider_id);

  return {
    provider: providerSummary(provider),
    query_count: seed.queries.length,
    result_kinds: seed.queries.map((query) => query.kind),
    results: seed.queries.map((query) => buildQueryResult(provider, query)),
  };
}

function main() {
  const workspaceRoot = process.env.WORKSPACE_ROOT || path.resolve(__dirname, "..");
  const dataRoot = process.env.SCHEDULE_DATA_ROOT || path.join(workspaceRoot, "data");
  const compareRoot = process.env.SCHEDULE_AUDIT_COMPARE_ROOT || "";
  const outputRoot = path.join(workspaceRoot, "output");
  const payload = {
    baseline: buildAudit(dataRoot),
  };

  if (compareRoot) {
    payload.comparison = buildAudit(compareRoot);
  }

  fs.mkdirSync(outputRoot, { recursive: true });
  fs.writeFileSync(
    path.join(outputRoot, "provider_audit.json"),
    JSON.stringify(payload, null, 2) + "\n",
    "utf-8"
  );
}

main();
