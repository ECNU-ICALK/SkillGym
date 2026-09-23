const { readJson } = require("../../shared");

function createDemoStaticProvider({ filePath }) {
  const payload = readJson(filePath);

  return {
    id: payload.id,
    label: payload.label,
    kind: payload.kind,
    timezone: payload.timezone,
    searchStops({ query, limit }) {
      const q = query.toLowerCase();
      return payload.stops
        .filter((stop) => stop.stop_id.toLowerCase() === q || stop.stop_name.toLowerCase().includes(q))
        .slice(0, limit);
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
  createDemoStaticProvider,
};
