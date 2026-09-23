export default function CompareWorkspace({ countries, onRemoveCountry, onClear }) {
  if (!countries.length) {
    return (
      <section className="panel compare-panel empty" data-testid="compare-workspace">
        <div className="panel-heading">
          <h2>Comparison workspace</h2>
        </div>
        <p>Add up to three countries from the table to compare generation, demand, and electricity mix.</p>
      </section>
    );
  }

  return (
    <section className="panel compare-panel" data-testid="compare-workspace">
      <div className="panel-heading">
        <h2>Comparison workspace</h2>
        <button type="button" className="ghost-button" onClick={onClear}>
          Clear selection
        </button>
      </div>
      <div className="compare-grid">
        {countries.map((country) => (
          <article key={country.isoCode} className="compare-card" data-country-code={country.isoCode}>
            <div className="compare-card-header">
              <div>
                <h3>{country.name}</h3>
                <p>{country.region}</p>
              </div>
              <button
                type="button"
                className="ghost-button"
                onClick={() => onRemoveCountry(country.isoCode)}
              >
                Remove
              </button>
            </div>
            <dl>
              <div>
                <dt>Renewables</dt>
                <dd>{country.renewablesShare.toFixed(1)}%</dd>
              </div>
              <div>
                <dt>Low carbon</dt>
                <dd>{country.lowCarbonShare.toFixed(1)}%</dd>
              </div>
              <div>
                <dt>Generation</dt>
                <dd>{country.generationTwh.toFixed(1)} TWh</dd>
              </div>
              <div>
                <dt>Demand</dt>
                <dd>{country.demandTwh.toFixed(1)} TWh</dd>
              </div>
              <div>
                <dt>Wind + solar</dt>
                <dd>{(country.windShare + country.solarShare).toFixed(1)}%</dd>
              </div>
              <div>
                <dt>Nuclear</dt>
                <dd>{country.nuclearShare.toFixed(1)}%</dd>
              </div>
            </dl>
          </article>
        ))}
      </div>
    </section>
  );
}
