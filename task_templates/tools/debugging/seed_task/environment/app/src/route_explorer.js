export function groupFlightsByAirport(records) {
  const grouped = new Map();
  for (const record of records) {
    const key = `${record.origin}-${record.destination}`;
    const bucket = grouped.get(key);
    if (bucket) {
      bucket.push(record);
    } else {
      grouped.set(key, [record]);
    }
  }
  return grouped;
}

export function computeConnectionMatrix(groupedRoutes) {
  return Array.from(groupedRoutes.entries()).map(([routeKey, items]) => ({
    routeKey,
    flights: items.length,
  }));
}

export function buildDelayHeatmap(records) {
  return records.map((record) => ({
    route: `${record.origin}-${record.destination}`,
    bucket: Math.max(0, Math.min(12, Math.floor(Number(record.delay_minutes || 0) / 10))),
  }));
}

export function renderRouteCards(rows) {
  return rows.map((row) => `${row.routeKey}:${row.flights}`);
}
