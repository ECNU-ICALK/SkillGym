const fs = require("fs");
const path = require("path");
const { loadProvider } = require("./provider_loader");
const { createDemoStaticProvider } = require("./providers/demo_static");
const { createCityReferenceProvider } = require("./providers/city_reference");
const { createMtaStaticProvider } = require("./providers/mta_static");
const { providerSummary, readJson, dataPath } = require("./shared");

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

function buildProviderSet(dataRoot) {
  return [
    loadProvider("demo_static", () =>
      createDemoStaticProvider({ filePath: dataPath(dataRoot, "providers/demo_static.json") })
    ),
    loadProvider("city_reference", () =>
      createCityReferenceProvider({ filePath: dataPath(dataRoot, "providers/city_reference.json") })
    ),
    loadProvider("mta_static", () =>
      createMtaStaticProvider({ dataRoot: dataPath(dataRoot, "gtfs") })
    ),
  ];
}

function buildCompareView(dataRoot) {
  const providers = buildProviderSet(dataRoot);
  const summaries = providers.map(providerSummary);
  const seed = readJson(path.join(dataRoot, "seed_queries.json"));
  const provider = providers.find((entry) => entry.id === seed.provider_id);
  return {
    providers: summaries,
    query_count: seed.queries.length,
    results: seed.queries.map((query) => buildQueryResult(provider, query)),
  };
}

function main() {
  const workspaceRoot = process.env.WORKSPACE_ROOT || path.resolve(__dirname, "..");
  const dataRoot = process.env.SCHEDULE_DATA_ROOT || path.join(workspaceRoot, "data");
  const compareRoot = process.env.SCHEDULE_COMPARE_ROOT || "";
  if (!compareRoot) {
    throw new Error("SCHEDULE_COMPARE_ROOT is required");
  }

  const outputRoot = path.join(workspaceRoot, "output");
  const payload = {
    baseline: buildCompareView(dataRoot),
    comparison: buildCompareView(compareRoot),
  };

  fs.mkdirSync(outputRoot, { recursive: true });
  fs.writeFileSync(
    path.join(outputRoot, "provider_compare.json"),
    JSON.stringify(payload, null, 2) + "\n",
    "utf-8"
  );
}

main();
