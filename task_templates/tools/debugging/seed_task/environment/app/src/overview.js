export function parseFlightsCsv(rows) {
  return rows;
}

export function normalizeAirportCodes(records) {
  return records;
}

export function buildAirportFilterIndex(records) {
  return new Map(records.map((record) => [record.origin, record]));
}

export function renderOverviewSummary(records) {
  return {
    totalFlights: records.length,
    delayedFlights: records.filter((record) => Number(record.delay_minutes || 0) > 0).length,
  };
}
