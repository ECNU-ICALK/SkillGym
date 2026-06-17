export const DEFAULT_REGION = "all";
export const DEFAULT_SORT = "renewables-desc";
export const DEFAULT_OVERVIEW_MODE = "table";

function parseOverviewMode(value) {
  return value === "renewables" ? "renewables" : DEFAULT_OVERVIEW_MODE;
}

function parseListParam(value) {
  if (!value) {
    return [];
  }

  return [...new Set(value.split(",").map((entry) => entry.trim().toUpperCase()).filter(Boolean))];
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
    overviewMode: parseOverviewMode(params.get("overview")),
    compareCodes: parseListParam(params.get("compare")).slice(0, 3),
    compareOpen: parseCompareView(params.get("compareView")),
    drawerCode: params.get("drawer")
  };
}

export function writePersistedState({ region, compareCodes, overviewMode }) {
  window.localStorage.setItem(
    "energy-workbench-state",
    JSON.stringify({ region, compareCodes, overviewMode, updatedAt: Date.now() })
  );
}

export function buildUrl({ region, search, sort, overviewMode, compareCodes, compareOpen, drawerCode }) {
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
  if (overviewMode && overviewMode !== DEFAULT_OVERVIEW_MODE) {
    params.set("overview", overviewMode);
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
