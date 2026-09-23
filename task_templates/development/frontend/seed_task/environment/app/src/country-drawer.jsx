import { useEffect, useRef } from "react";
import { useCountryDetails } from "./use-country-details.js";

function formatPopulation(value) {
  return `${(value / 1_000_000).toFixed(1)}M`;
}

export default function CountryDrawer({ countryCode, activeRegionLabel, onClose }) {
  const closeButtonRef = useRef(null);
  const { loading, error, detail } = useCountryDetails(countryCode);

  useEffect(() => {
    closeButtonRef.current?.focus();
  }, [countryCode]);

  return (
    <>
      <div className="drawer-backdrop" aria-hidden="true" />
      <aside
        className="drawer"
        role="dialog"
        aria-modal="true"
        aria-labelledby="drawer-title"
        data-testid="country-drawer"
      >
        <div className="drawer-header">
          <div>
            <p className="eyebrow">Country details</p>
            <h2 id="drawer-title" data-testid="drawer-title">
              {detail?.name || countryCode}
            </h2>
            <p data-testid="drawer-context">{activeRegionLabel}</p>
          </div>
          <button ref={closeButtonRef} type="button" data-testid="drawer-close" onClick={onClose}>
            Close
          </button>
        </div>

        {error ? <p className="empty-inline">Failed to load details: {error}</p> : null}
        {loading && !detail ? <p className="empty-inline">Loading country details…</p> : null}

        {detail ? (
          <dl className="drawer-grid">
            <div>
              <dt>ISO code</dt>
              <dd data-testid="detail-iso-code">{detail.isoCode}</dd>
            </div>
            <div>
              <dt>Income level</dt>
              <dd>{detail.incomeLevel}</dd>
            </div>
            <div>
              <dt>Population</dt>
              <dd>{formatPopulation(detail.population)}</dd>
            </div>
            <div>
              <dt>Demand per capita</dt>
              <dd data-testid="detail-demand-per-capita">{detail.demandPerCapitaKwh.toFixed(0)} kWh</dd>
            </div>
            <div>
              <dt>Dominant renewable</dt>
              <dd data-testid="detail-dominant-source">{detail.dominantRenewableSource}</dd>
            </div>
            <div>
              <dt>Renewables delta</dt>
              <dd>{detail.deltaRenewables.toFixed(1)} pts</dd>
            </div>
          </dl>
        ) : null}
      </aside>
    </>
  );
}
