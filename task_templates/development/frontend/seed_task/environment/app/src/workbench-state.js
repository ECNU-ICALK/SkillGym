export const DEFAULT_REGION = "all";
export const DEFAULT_SORT = "renewables-desc";

function parseListParam(value) {
  return value ? value.split(",").map((entry) => entry.trim()).filter(Boolean) : [];
}

function parseCompareView(value) {
  if (value === "open") {
    return true;
  }
  if (value === "closed") {
    return false;
  }
  return null;
}

export function parseUrlState() {
  const params = new URLSearchParams(window.location.search);
  return {
    region: params.get("region") || DEFAULT_REGION,
    search: params.get("search") || "",
    sort: params.get("sort") || DEFAULT_SORT,
    compareCodes: parseListParam(params.get("compare")),
    compareOpen: parseCompareView(params.get("compareView")),
    drawerCode: params.get("drawer")
  };
}

export function readPersistedState() {
  try {
    const raw = window.localStorage.getItem("energy-workbench-state");
    if (!raw) {
      return null;
    }
    return JSON.parse(raw);
  } catch {
    return null;
  }
}

export function writePersistedState({ region, compareCodes }) {
  window.localStorage.setItem(
    "energy-workbench-state",
    JSON.stringify({ region, compareCodes, updatedAt: Date.now() })
  );
}

export function buildUrl({ region, search, sort, compareCodes, compareOpen, drawerCode }) {
  const params = new URLSearchParams();
  if (region && region !== DEFAULT_REGION) {
    params.set("region", region);
  }
  if (search) {
    params.set("search", search);
  }
  if (sort && sort !== DEFAULT_SORT) {
    params.set("sort", sort);
  }
  if (compareCodes.length) {
    params.set("compare", compareCodes.join(","));
    params.set("compareView", compareOpen ? "open" : "closed");
  }
  if (drawerCode) {
    params.set("drawer", drawerCode);
  }
  const query = params.toString();
  return query ? `?${query}` : window.location.pathname;
}
