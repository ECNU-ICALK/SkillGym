import { Suspense, lazy, useEffect, useMemo, useRef, useState } from "react";
import { buildUrl, DEFAULT_REGION, DEFAULT_SORT, parseUrlState, readPersistedState, writePersistedState } from "./workbench-state.js";
import { deriveOverviewCountries, summarizeOverview } from "./overview-metrics.js";

const API_BASE = import.meta.env.VITE_API_BASE_URL || "http://localhost:3001";
const LazyCompareWorkspace = lazy(() => import("./compare-workspace.jsx"));
const LazyCountryDrawer = lazy(() => import("./country-drawer.jsx"));
const DEFAULT_OVERVIEW_MODE = "table";

function sortCountries(rows, sort) {
  const copy = [...rows];
  switch (sort) {
    case "generation-desc":
      return copy.sort((left, right) => right.generationTwh - left.generationTwh);
    case "delta-renewables-desc":
      return copy.sort((left, right) => right.deltaRenewables - left.deltaRenewables);
    case "name-asc":
      return copy.sort((left, right) => left.name.localeCompare(right.name));
    case "renewables-desc":
    default:
      return copy.sort((left, right) => right.renewablesShare - left.renewablesShare);
  }
}

function matchesSearch(country, search) {
  if (!search) {
    return true;
  }
  const query = search.toLowerCase();
  return (
    country.name.toLowerCase().includes(query) ||
    country.isoCode.toLowerCase().includes(query) ||
    country.region.toLowerCase().includes(query)
  );
}

function formatRegionLabel(region) {
  return region === DEFAULT_REGION ? "All regions" : region;
}

function StatCard({ label, value, hint, valueTestId }) {
  return (
    <article className="stat-card">
      <p className="stat-label">{label}</p>
      <p className="stat-value" data-testid={valueTestId}>
        {value}
      </p>
      <p className="stat-hint">{hint}</p>
    </article>
  );
}

export default function App() {
  const persisted = readPersistedState();
  const urlState = parseUrlState();

  const [dashboard, setDashboard] = useState({ countries: [], regions: [], codebook: [] });
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  const [region, setRegion] = useState(persisted?.region || urlState.region);
  const [search, setSearch] = useState(urlState.search);
  const [sort, setSort] = useState(urlState.sort);
  const [compareCodes, setCompareCodes] = useState(persisted?.compareCodes || urlState.compareCodes);
  const [drawerCode, setDrawerCode] = useState(urlState.drawerCode);
  const [compareOpen, setCompareOpen] = useState(urlState.compareOpen ?? compareCodes.length > 0);
  const [overviewMode, setOverviewMode] = useState(DEFAULT_OVERVIEW_MODE);

  const drawerTriggerRef = useRef(null);

  useEffect(() => {
    import("./compare-workspace.jsx");
    import("./country-drawer.jsx");
  }, []);

  useEffect(() => {
    let cancelled = false;

    async function load() {
      setLoading(true);
      setError("");
      try {
        const response = await fetch(`${API_BASE}/api/dashboard`);
        if (!response.ok) {
          throw new Error(`Failed to load dashboard (${response.status})`);
        }
        const payload = await response.json();
        if (!cancelled) {
          setDashboard(payload);
        }
      } catch (err) {
        if (!cancelled) {
          setError(err instanceof Error ? err.message : "Failed to load dashboard");
        }
      } finally {
        if (!cancelled) {
          setLoading(false);
        }
      }
    }

    load();
    return () => {
      cancelled = true;
    };
  }, []);

  useEffect(() => {
    const stateFromUrl = parseUrlState();
    setRegion(stateFromUrl.region);
    setSearch(stateFromUrl.search);
    setSort(stateFromUrl.sort);
    setCompareCodes(stateFromUrl.compareCodes);
    setCompareOpen(stateFromUrl.compareOpen ?? stateFromUrl.compareCodes.length > 0);
    setDrawerCode(stateFromUrl.drawerCode);
  }, []);

  useEffect(() => {
    const timer = window.setTimeout(() => {
      const restored = readPersistedState();
      if (!restored) {
        return;
      }
      if (restored.region) {
        setRegion(restored.region);
      }
      if (Array.isArray(restored.compareCodes)) {
        setCompareCodes(restored.compareCodes);
      }
    }, 300);

    return () => window.clearTimeout(timer);
  }, []);

  useEffect(() => {
    const nextUrl = buildUrl({ region, search, sort, compareCodes, compareOpen, drawerCode });
    window.history.replaceState({}, "", nextUrl);
    writePersistedState({ region, compareCodes });
  }, [region, search, sort, compareCodes, compareOpen, drawerCode]);

  useEffect(() => {
    if (!drawerCode) {
      return undefined;
    }
    const onKeyDown = (event) => {
      if (event.key === "Escape") {
        setDrawerCode(null);
      }
    };
    window.addEventListener("keydown", onKeyDown);
    return undefined;
  }, [drawerCode]);

  const visibleCountries = useMemo(() => {
    const filtered = dashboard.countries
      .filter((country) => region === DEFAULT_REGION || country.region === region)
      .filter((country) => matchesSearch(country, search));
    return sortCountries(filtered, sort);
  }, [dashboard.countries, region, search, sort]);

  const compareCountries = useMemo(() => {
    return compareCodes
      .map((isoCode) => dashboard.countries.find((country) => country.isoCode === isoCode))
      .filter(Boolean);
  }, [dashboard.countries, compareCodes]);

  const overviewCountries = useMemo(() => {
    return deriveOverviewCountries(dashboard.countries, { region, search, sort });
  }, [dashboard.countries, region, search, sort]);

  const overviewSummary = useMemo(() => summarizeOverview(overviewCountries), [overviewCountries]);

  const mixCountries = useMemo(() => {
    if (overviewMode === "renewables") {
      return [...visibleCountries].sort((left, right) => right.renewablesShare - left.renewablesShare);
    }
    return visibleCountries;
  }, [overviewMode, visibleCountries]);

  const drawerCountry = useMemo(() => {
    return dashboard.countries.find((country) => country.isoCode === drawerCode) || null;
  }, [dashboard.countries, drawerCode]);

  function updateCompare(isoCode) {
    setCompareCodes((current) => {
      if (current.includes(isoCode)) {
        const next = current.filter((entry) => entry !== isoCode);
        if (!next.length) {
          setCompareOpen(false);
        }
        return next;
      }
      setCompareOpen(true);
      return [...current, isoCode].slice(0, 3);
    });
  }

  function openDrawer(isoCode, trigger) {
    drawerTriggerRef.current = trigger;
    setDrawerCode(isoCode);
  }

  if (loading) {
    return <main className="screen-state">Loading energy workbench…</main>;
  }

  if (error) {
    return <main className="screen-state">Failed to load dashboard: {error}</main>;
  }

  return (
    <main className="page-shell">
      <header className="hero">
        <div>
          <p className="eyebrow">Regional strategy</p>
          <h1>Country energy comparison workbench</h1>
          <p className="hero-copy">
            Compare electricity mix, generation, and demand signals across a curated country set.
          </p>
        </div>
        <div className="hero-context">
          <span data-testid="active-region-label">{formatRegionLabel(region)}</span>
          <span>{dashboard.snapshotId}</span>
        </div>
      </header>

      <section className="panel filters-panel">
        <div className="controls-grid">
          <label className="field">
            <span>Region</span>
            <select
              data-testid="region-select"
              value={region}
              onChange={(event) => setRegion(event.target.value)}
            >
              <option value={DEFAULT_REGION}>All regions</option>
              {dashboard.regions.map((entry) => (
                <option key={entry} value={entry}>
                  {entry}
                </option>
              ))}
            </select>
          </label>

          <label className="field">
            <span>Search country</span>
            <input
              data-testid="search-input"
              value={search}
              onChange={(event) => setSearch(event.target.value)}
              placeholder="Search by name or code"
            />
          </label>

          <label className="field">
            <span>Sort by</span>
            <select data-testid="sort-select" value={sort} onChange={(event) => setSort(event.target.value)}>
              <option value="renewables-desc">Renewables share</option>
              <option value="generation-desc">Generation</option>
              <option value="delta-renewables-desc">Year-over-year renewables gain</option>
              <option value="name-asc">Country name</option>
            </select>
          </label>

          <button
            type="button"
            className="primary-button"
            data-testid="compare-toggle"
            aria-expanded={compareOpen ? "true" : "false"}
            onClick={() => setCompareOpen((current) => !current)}
          >
            {compareOpen ? "Hide comparison" : "Open comparison"}
          </button>
        </div>

        <div className="compare-chip-row" data-testid="compare-chip-row">
          {compareCountries.map((country) => (
            <span key={country.isoCode} className="chip" data-country-code={country.isoCode}>
              {country.name}
            </span>
          ))}
        </div>
      </section>

      <section className="stats-grid">
        <StatCard
          label="Visible countries"
          value={overviewSummary.visibleCount}
          hint="Current filter and search scope"
          valueTestId="stat-visible-count"
        />
        <StatCard
          label="Average renewables share"
          value={`${overviewSummary.averageRenewables.toFixed(1)}%`}
          hint="Hydro + solar + wind across visible countries"
          valueTestId="stat-average-renewables"
        />
        <StatCard
          label="Top renewables row"
          value={overviewSummary.topCountry ? overviewSummary.topCountry.name : "No result"}
          hint={
            overviewSummary.topCountry
              ? `${overviewSummary.topCountry.renewablesShare.toFixed(1)}% renewable share`
              : "Adjust filters"
          }
          valueTestId="stat-top-country"
        />
      </section>

      <section className="panel layout-grid">
        <div className="table-panel">
          <div className="panel-heading">
            <h2>Country table</h2>
            <p>{visibleCountries.length} rows</p>
          </div>
          <table>
            <thead>
              <tr>
                <th>Compare</th>
                <th>Country</th>
                <th>Region</th>
                <th>Renewables</th>
                <th>Generation</th>
                <th>Demand</th>
                <th>Details</th>
              </tr>
            </thead>
            <tbody data-testid="country-table-body">
              {visibleCountries.map((country) => {
                const selected = compareCodes.includes(country.isoCode);
                return (
                  <tr key={country.isoCode} data-country-code={country.isoCode}>
                    <td>
                      <input
                        aria-label={`Compare ${country.name}`}
                        type="checkbox"
                        checked={selected}
                        onChange={() => updateCompare(country.isoCode)}
                      />
                    </td>
                    <td>{country.name}</td>
                    <td>{country.region}</td>
                    <td>{country.renewablesShare.toFixed(1)}%</td>
                    <td>{country.generationTwh.toFixed(1)} TWh</td>
                    <td>{country.demandTwh.toFixed(1)} TWh</td>
                    <td>
                      <button
                        type="button"
                        data-testid={`open-details-${country.isoCode}`}
                        onClick={(event) => openDrawer(country.isoCode, event.currentTarget)}
                      >
                        Open details
                      </button>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>

        <div className="chart-panel">
          <div className="panel-heading">
            <h2>Mix highlight</h2>
            <div className="chart-panel-actions">
              <p>{overviewMode === "renewables" ? "Renewables-first view" : "Current table order"}</p>
              <div className="segmented-control" data-testid="overview-mode-toggle">
                <button
                  type="button"
                  data-testid="overview-mode-table"
                  aria-pressed={overviewMode === "table" ? "true" : "false"}
                  onClick={() => setOverviewMode("table")}
                >
                  Table order
                </button>
                <button
                  type="button"
                  data-testid="overview-mode-renewables"
                  aria-pressed={overviewMode === "renewables" ? "true" : "false"}
                  onClick={() => setOverviewMode("renewables")}
                >
                  Renewables
                </button>
              </div>
            </div>
          </div>
          <div className="mix-list" data-testid="mix-list">
            {mixCountries.slice(0, 4).map((country) => (
              <article key={country.isoCode} className="mix-row" data-country-code={country.isoCode}>
                <div className="mix-copy">
                  <strong>{country.name}</strong>
                  <span>{country.renewablesShare.toFixed(1)}% renewable share</span>
                </div>
                <div className="mix-bars" aria-hidden="true">
                  <span className="mix-bar renewable" style={{ width: `${country.renewablesShare}%` }} />
                  <span className="mix-bar low-carbon" style={{ width: `${country.lowCarbonShare}%` }} />
                </div>
              </article>
            ))}
          </div>
        </div>
      </section>

      {compareOpen ? (
        <Suspense fallback={<section className="panel compare-panel">Loading comparison workspace…</section>}>
          <LazyCompareWorkspace
            countries={compareCountries}
            onRemoveCountry={(isoCode) => {
              setCompareCodes((current) => current.filter((entry) => entry !== isoCode));
            }}
            onClear={() => setCompareCodes([])}
          />
        </Suspense>
      ) : null}

      {drawerCountry ? (
        <Suspense fallback={<aside className="drawer" data-testid="country-drawer">Loading country details…</aside>}>
          <LazyCountryDrawer
            countryCode={drawerCountry.isoCode}
            activeRegionLabel={formatRegionLabel(region)}
            onClose={() => setDrawerCode(null)}
          />
        </Suspense>
      ) : null}
    </main>
  );
}
