const API_BASE = import.meta.env.VITE_API_BASE_URL || "http://localhost:3001";
const STORAGE_PREFIX = "bikeboard-cache";

function storageKey(key) {
  return `${STORAGE_PREFIX}:${key}`;
}

function readCache(key) {
  try {
    const raw = localStorage.getItem(storageKey(key));
    return raw ? JSON.parse(raw) : null;
  } catch (_error) {
    return null;
  }
}

function writeCache(key, payload) {
  try {
    localStorage.setItem(storageKey(key), JSON.stringify(payload));
  } catch (_error) {
    // Ignore quota failures and keep the response path moving.
  }
}

async function requestJson(path) {
  const response = await fetch(`${API_BASE}${path}`, { cache: "no-store" });
  if (!response.ok) {
    throw new Error(`API request failed: ${response.status}`);
  }
  return response.json();
}

async function requestWithFallback(path, cacheKey) {
  try {
    const payload = await requestJson(path);
    const savedAt = Math.floor(Date.now() / 1000);
    writeCache(cacheKey, { payload, savedAt });
    return { payload, source: "current", savedAt };
  } catch (error) {
    const cached = readCache(cacheKey);
    if (cached) {
      return { payload: cached.payload, source: "saved", savedAt: cached.savedAt };
    }
    throw error;
  }
}

export function fetchBootstrap() {
  return requestWithFallback("/api/bootstrap", "bootstrap");
}

export function searchStations(query) {
  const encoded = encodeURIComponent(query.trim());
  return requestWithFallback(`/api/stations?q=${encoded}`, `search:${encoded}`);
}

export function fetchStationDetail(stationId) {
  return requestWithFallback(`/api/stations/${stationId}`, `detail:${stationId}`);
}
