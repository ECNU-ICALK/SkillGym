const API_BASE = import.meta.env.VITE_API_BASE_URL || "http://localhost:3001";

async function requestJson(path) {
  const response = await fetch(`${API_BASE}${path}`, { cache: "no-store" });
  if (!response.ok) {
    throw new Error(`API request failed: ${response.status}`);
  }
  const payload = await response.json();
  return {
    payload,
    source: "current",
    savedAt: Math.floor(Date.now() / 1000)
  };
}

export function fetchBootstrap() {
  return requestJson("/api/bootstrap");
}

export function searchStations(query) {
  const encoded = encodeURIComponent(query.trim());
  return requestJson(`/api/stations?q=${encoded}`);
}

export function fetchStationDetail(stationId) {
  return requestJson(`/api/stations/${stationId}`);
}
