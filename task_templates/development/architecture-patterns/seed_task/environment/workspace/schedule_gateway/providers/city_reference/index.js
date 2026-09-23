const { readJson } = require("../../shared");

function normalizeQuery(stops, query, limit) {
  const exact = [];
  const fuzzy = [];
  const q = query.toLowerCase();

  for (const stop of stops) {
    if (stop.stop_id.toLowerCase() === q) {
      exact.push(stop);
      continue;
    }
    if (stop.stop_name.toLowerCase().includes(q)) {
      fuzzy.push(stop);
    }
  }

  return [...exact, ...fuzzy].slice(0, limit);
}

function createCityReferenceProvider({ filePath }) {
  const payload = readJson(filePath);

  return {
    id: payload.meta.id,
    label: payload.meta.label,
    kind: payload.meta.kind,
    timezone: payload.meta.timezone,
    searchStops({ query, limit }) {
      return normalizeQuery(payload.stops, query, limit);
    },
    getDepartures({ stopId, serviceDate, queryTime, limit }) {
      const stop = payload.stops.find((entry) => entry.stop_id === stopId);
      const departures = payload.departures
        .filter((entry) => entry.stop_id === stopId && entry.service_date === serviceDate && entry.departure_time >= queryTime)
        .slice(0, limit);
      return { stop, departures };
    },
    getServiceWindow({ routeId, serviceDate }) {
      const route = payload.routes.find((entry) => entry.route_id === routeId);
      const summary = payload.service_windows.find((entry) => entry.route_id === routeId && entry.service_date === serviceDate);
      return { route, service_window: summary };
    },
  };
}

module.exports = {
  createCityReferenceProvider,
};
