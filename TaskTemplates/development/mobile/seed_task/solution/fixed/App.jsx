import { useEffect, useState } from "react";
import { Link, Route, Routes, useLocation, useNavigate, useParams } from "react-router-dom";
import { fetchBootstrap, fetchStationDetail, searchStations } from "./api.js";

function formatTimestamp(epochSeconds) {
  if (!epochSeconds) {
    return "Unknown";
  }
  return new Intl.DateTimeFormat("en-US", {
    month: "short",
    day: "numeric",
    hour: "numeric",
    minute: "2-digit"
  }).format(new Date(epochSeconds * 1000));
}

function FreshnessPill({ labels, source, updatedAt }) {
  return (
    <div className="freshness-pill" data-testid="source-state" data-source-state={source}>
      <span className="freshness-label" data-testid="freshness-source">
        {source === "saved" ? labels.saved : labels.current}
      </span>
      <strong data-testid="freshness-updated">{formatTimestamp(updatedAt)}</strong>
    </div>
  );
}

function AdvisoryList({ advisories }) {
  if (!advisories.length) {
    return (
      <section className="panel" data-testid="advisories-section">
        <div className="panel-header">
          <h2>Commute reminders</h2>
        </div>
        <p className="muted">No extra reminders in this snapshot.</p>
      </section>
    );
  }

  return (
    <section className="panel" data-testid="advisories-section">
      <div className="panel-header">
        <h2>Commute reminders</h2>
      </div>
      <ul className="advisory-list">
        {advisories.map((advisory) => (
          <li className={`advisory advisory-${advisory.severity}`} key={`${advisory.station_id}-${advisory.kind}`}>
            <strong>{advisory.title}</strong>
            <span>{advisory.message}</span>
          </li>
        ))}
      </ul>
    </section>
  );
}

function StationCard({ station }) {
  return (
    <Link className="station-card" data-testid={`station-card-${station.station_id}`} to={`/station/${station.station_id}`}>
      <div className="station-card-copy">
        <div>
          <h3>{station.name}</h3>
          <p className="station-meta">Station {station.short_name || station.station_id}</p>
        </div>
        <span className={`status-chip status-${station.status_tone}`} data-testid={`status-${station.station_id}`}>
          {station.status_label}
        </span>
      </div>
      <dl className="station-stats">
        <div>
          <dt>Bikes</dt>
          <dd data-testid={`bikes-${station.station_id}`}>{station.bikes_available}</dd>
        </div>
        <div>
          <dt>Docks</dt>
          <dd data-testid={`docks-${station.station_id}`}>{station.docks_available}</dd>
        </div>
        <div>
          <dt>Capacity</dt>
          <dd>{station.capacity}</dd>
        </div>
      </dl>
      <span className="detail-link">View station</span>
    </Link>
  );
}

function HomePage({ bootstrapState }) {
  const [query, setQuery] = useState("");
  const [resultsState, setResultsState] = useState({
    items: bootstrapState.payload.favorites.stations,
    source: bootstrapState.source,
    error: ""
  });

  useEffect(() => {
    if (!query.trim()) {
      setResultsState({
        items: bootstrapState.payload.favorites.stations,
        source: bootstrapState.source,
        error: ""
      });
      return;
    }

    let active = true;
    searchStations(query)
      .then((state) => {
        if (!active) {
          return;
        }
        setResultsState({
          items: state.payload.items,
          source: state.source,
          error: ""
        });
      })
      .catch(() => {
        if (!active) {
          return;
        }
        setResultsState((previous) => ({
          ...previous,
          error: "Search results are unavailable right now."
        }));
      });

    return () => {
      active = false;
    };
  }, [bootstrapState.payload.favorites.stations, bootstrapState.source, query]);

  return (
    <div className="page-stack" data-testid="home-page">
      <section className="panel hero-panel">
        <div className="panel-header">
          <div>
            <p className="eyebrow">Mobile commute board</p>
            <h1>{bootstrapState.payload.system.name}</h1>
            <p className="muted">Watch a few saved stations before you head out.</p>
          </div>
          <span className="hero-count" data-testid="favorite-count">
            {bootstrapState.payload.favorites.stations.length}
          </span>
        </div>
        <div className="favorites-grid" data-testid="favorites-grid">
          {bootstrapState.payload.favorites.stations.map((station) => (
            <StationCard key={station.station_id} station={station} />
          ))}
        </div>
      </section>

      <section className="panel">
        <div className="panel-header">
          <div>
            <h2>Search stations</h2>
            <p className="muted">Search by station name or short code.</p>
          </div>
          <span className="mode-chip">{resultsState.source === "saved" ? "Saved view" : "Current view"}</span>
        </div>
        <label className="search-shell" htmlFor="station-search">
          <span>Search</span>
          <input
            data-testid="search-input"
            id="station-search"
            name="station-search"
            placeholder="Try Broadway or Central Park"
            type="search"
            value={query}
            onChange={(event) => setQuery(event.target.value)}
          />
        </label>
        <div className="search-examples">
          {bootstrapState.payload.search_examples.map((example) => (
            <button
              className="example-chip"
              key={example.query}
              type="button"
              onClick={() => setQuery(example.query)}
            >
              {example.label}
            </button>
          ))}
        </div>
        {resultsState.error ? <p className="error-copy">{resultsState.error}</p> : null}
        <div className="results-list" data-testid="results-list">
          {resultsState.items.map((station) => (
            <StationCard key={station.station_id} station={station} />
          ))}
        </div>
      </section>

      <AdvisoryList advisories={bootstrapState.payload.advisories} />
    </div>
  );
}

function StationDetailPage({ bootstrapState }) {
  const { stationId } = useParams();
  const navigate = useNavigate();
  const [detailState, setDetailState] = useState(null);
  const [error, setError] = useState("");

  useEffect(() => {
    if (!stationId) {
      return;
    }

    let active = true;
    setDetailState(null);
    setError("");

    fetchStationDetail(stationId)
      .then((state) => {
        if (!active) {
          return;
        }
        setDetailState(state);
      })
      .catch(() => {
        if (!active) {
          return;
        }
        setError("This station is unavailable right now.");
      });

    return () => {
      active = false;
    };
  }, [stationId]);

  if (error) {
    return (
      <section className="panel detail-panel" data-testid="station-detail">
        <button className="back-link" type="button" onClick={() => navigate("/")}>
          Back
        </button>
        <p className="error-copy">{error}</p>
      </section>
    );
  }

  if (!detailState) {
    return (
      <section className="panel detail-panel" data-testid="station-detail">
        <button className="back-link" type="button" onClick={() => navigate("/")}>
          Back
        </button>
        <p className="muted">Loading station details…</p>
      </section>
    );
  }

  const station = detailState.payload.station;
  return (
    <section className="panel detail-panel" data-testid="station-detail">
      <button className="back-link" type="button" onClick={() => navigate("/")}>
        Back
      </button>
      {detailState.source === "saved" ? (
        <p className="saved-copy" data-testid="detail-source-state" data-source-state="saved">
          Saved station details are shown while connectivity is unavailable.
        </p>
      ) : (
        <p className="saved-copy" data-testid="detail-source-state" data-source-state="current">
          Current station details are shown from the latest feed.
        </p>
      )}
      <div className="detail-header">
        <div>
          <h2 data-testid="detail-name">{station.name}</h2>
          <p className="muted" data-testid="detail-code">Station {station.short_name || station.station_id}</p>
        </div>
        <span className={`status-chip status-${station.status_tone}`} data-testid="detail-status">
          {station.status_label}
        </span>
      </div>
      <dl className="detail-stats">
        <div>
          <dt>Available bikes</dt>
          <dd data-testid="detail-bikes">{station.bikes_available}</dd>
        </div>
        <div>
          <dt>Open docks</dt>
          <dd data-testid="detail-docks">{station.docks_available}</dd>
        </div>
        <div>
          <dt>Capacity</dt>
          <dd data-testid="detail-capacity">{station.capacity}</dd>
        </div>
        <div>
          <dt>Last report</dt>
          <dd>{formatTimestamp(station.last_reported || bootstrapState.payload.meta.status_last_updated)}</dd>
        </div>
      </dl>
      <p className="muted">
        Coordinates: {station.lat}, {station.lon}
      </p>
      <AdvisoryList advisories={detailState.payload.advisories} />
    </section>
  );
}

function shouldShowQuickAccess(location) {
  if (location.search.includes("entry=quick-access")) {
    return true;
  }
  if (window.matchMedia && window.matchMedia("(display-mode: standalone)").matches) {
    return true;
  }
  return Boolean(window.navigator.standalone);
}

export default function App() {
  const location = useLocation();
  const [bootstrapState, setBootstrapState] = useState(null);
  const [error, setError] = useState("");

  useEffect(() => {
    let active = true;
    fetchBootstrap()
      .then((state) => {
        if (!active) {
          return;
        }
        setBootstrapState(state);
        setError("");
      })
      .catch(() => {
        if (!active) {
          return;
        }
        setError("Unable to reach the station feed.");
      });

    return () => {
      active = false;
    };
  }, []);

  if (!bootstrapState) {
    return (
      <div className="shell">
        <header className="topbar">
          <div>
            <p className="eyebrow">Mobile commute board</p>
            <h1>Commute board</h1>
          </div>
        </header>
        <main>
          <section className="panel">
            <p className={error ? "error-copy" : "muted"}>{error || "Loading station feed…"}</p>
          </section>
        </main>
      </div>
    );
  }

  const { contract, meta, system } = bootstrapState.payload;

  return (
    <div className="shell">
      <header className="topbar">
        <div>
          <p className="eyebrow">Mobile commute board</p>
          <h1>{system.name} commute board</h1>
        </div>
        <FreshnessPill
          labels={contract.freshness_labels}
          source={bootstrapState.source}
          updatedAt={meta.status_last_updated}
        />
      </header>
      {bootstrapState.source === "saved" ? (
        <section className="panel saved-banner" data-testid="saved-banner">
          <strong>Saved commute view</strong>
          <span>Current station updates are unavailable, so the latest retained view is shown.</span>
        </section>
      ) : null}
      {shouldShowQuickAccess(location) ? (
        <section className="panel quick-entry-banner" data-testid="quick-access-banner">
          <strong>{contract.install_entry_name}</strong>
          <span>Open your saved stops and current reminders.</span>
        </section>
      ) : null}
      <main>
        <Routes>
          <Route path="/" element={<HomePage bootstrapState={bootstrapState} />} />
          <Route path="/station/:stationId" element={<StationDetailPage bootstrapState={bootstrapState} />} />
        </Routes>
      </main>
    </div>
  );
}
