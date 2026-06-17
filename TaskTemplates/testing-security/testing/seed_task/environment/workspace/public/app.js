const state = {
  rows: [],
  selected: [],
};

const searchInput = document.getElementById('search-input');
const countrySelect = document.getElementById('country-select');
const minRunwayInput = document.getElementById('min-runway-input');
const applyFiltersButton = document.getElementById('apply-filters');
const clearFiltersButton = document.getElementById('clear-filters');
const exportButton = document.getElementById('export-button');
const compareButton = document.getElementById('show-compare');
const countEl = document.getElementById('airport-count');
const loadingIndicator = document.getElementById('loading-indicator');
const tableBody = document.getElementById('airport-table-body');
const rowTemplate = document.getElementById('airport-row-template');
const resultsSummary = document.getElementById('results-summary');
const resultsSummarySkeleton = document.getElementById('results-summary-skeleton');
const resultsSummaryBody = document.getElementById('results-summary-body');
const detailPanel = document.getElementById('detail-panel');
const detailList = document.getElementById('detail-list');
const comparePanel = document.getElementById('compare-panel');
const compareSummary = document.getElementById('compare-summary');
const insightsPanel = document.getElementById('insights-panel');
const insightsSkeleton = document.getElementById('insights-skeleton');
const insightsBody = document.getElementById('insights-body');
const rootElement = document.documentElement;
const uiFlags = window.__AIRPORT_UI_FLAGS__ || {};

function resolveTheme() {
  return localStorage.getItem('theme') === 'dark' ? 'dark' : 'light';
}

function applyStoredTheme() {
  rootElement.dataset.theme = resolveTheme();
}

function scheduleResultsSummaryLoad() {
  const reserveMode = uiFlags.summaryReserveMode || 'full';
  resultsSummary.classList.add('is-reserved');
  if (reserveMode === 'compact') {
    resultsSummary.classList.add('is-reserved-compact');
    resultsSummarySkeleton.classList.add('is-compact');
  }

  window.setTimeout(() => {
    if (resultsSummaryBody.dataset.loaded === 'true') {
      return;
    }

    resultsSummaryBody.dataset.loaded = 'true';
    resultsSummary.hidden = false;
    resultsSummarySkeleton.hidden = true;
    resultsSummaryBody.hidden = false;
    resultsSummaryBody.classList.add('results-summary-body');
    resultsSummaryBody.innerHTML = `
      <article>
        <strong>Runway balance summary</strong>
        <span>The opening view still needs a visual stability check before dispatchers rely on it for the next compare-and-export cycle.</span>
      </article>
      <article>
        <strong>Late content watch</strong>
        <span>Any delayed summary block should keep the existing table and controls steady for the active viewport.</span>
      </article>
    `;
  }, 650);
}

function scheduleInsightsLoad() {
  const reserveMode = uiFlags.insightsReserveMode || 'full';
  insightsPanel.classList.add('is-reserved');
  if (reserveMode === 'compact') {
    insightsPanel.classList.add('is-reserved-compact');
    insightsSkeleton.classList.add('is-compact');
  }

  window.setTimeout(() => {
    if (insightsBody.dataset.loaded === 'true') {
      return;
    }

    insightsBody.dataset.loaded = 'true';
    insightsPanel.hidden = false;
    insightsSkeleton.hidden = true;
    insightsBody.hidden = false;
    insightsBody.classList.add('insights-body');
    insightsBody.innerHTML = `
      <article class="insight-card">
        <strong>Runway staging brief</strong>
        <span>The current filtered view can support a two-wave runway release after the overnight cargo bank clears.</span>
      </article>
      <article class="insight-card">
        <strong>Queue balance note</strong>
        <span>Pacific departures are holding steady, but East Coast hubs still need an updated comparison check before export.</span>
      </article>
    `;

    if (uiFlags.lowerAreaShiftMode === 'lateral') {
      document.body.classList.add('lower-area-shift-active');
    }
  }, 650);
}

function maybeApplyDeferredTheme() {
  const mode = uiFlags.deferredThemeBootstrapMode || (uiFlags.deferredThemeBootstrap ? 'timeout' : 'none');
  if (mode === 'none') {
    return;
  }

  if (mode === 'raf') {
    window.requestAnimationFrame(applyStoredTheme);
    return;
  }

  window.setTimeout(applyStoredTheme, 140);
}

function buildQueryString() {
  const params = new URLSearchParams();
  if (searchInput.value.trim()) {
    params.set('q', searchInput.value.trim());
  }
  if (countrySelect.value) {
    params.set('country', countrySelect.value);
  }
  if (minRunwayInput.value) {
    params.set('minRunwayLength', minRunwayInput.value);
  }
  return params.toString();
}

function setLoading(isLoading) {
  loadingIndicator.hidden = !isLoading;
}

function formatFeet(value) {
  return value ? `${value.toLocaleString()} ft` : 'n/a';
}

function renderCount() {
  countEl.textContent = `${state.rows.length} airports in the current view`;
}

function syncCompareButton() {
  compareButton.disabled = state.selected.length !== 2;
}

function renderRows() {
  tableBody.innerHTML = '';

  for (const airport of state.rows) {
    const fragment = rowTemplate.content.cloneNode(true);
    const row = fragment.querySelector('[data-testid="airport-row"]');
    row.dataset.ident = airport.ident;
    row.querySelector('[data-field="code"]').textContent = `${airport.ident} / ${airport.iataCode || '—'}`;
    row.querySelector('[data-field="name"]').textContent = airport.name;
    row.querySelector('[data-field="country"]').textContent = airport.countryName;
    row.querySelector('[data-field="city"]').textContent = airport.municipality || '—';
    row.querySelector('[data-field="runways"]').textContent = String(airport.runwayCount);
    row.querySelector('[data-field="longest"]').textContent = formatFeet(airport.longestRunwayFt);

    const detailsButton = row.querySelector('[data-action="details"]');
    detailsButton.dataset.ident = airport.ident;
    detailsButton.addEventListener('click', () => openDetails(airport.ident));

    const compareToggleButton = row.querySelector('[data-action="compare"]');
    compareToggleButton.dataset.ident = airport.ident;
    compareToggleButton.textContent = state.selected.includes(airport.ident) ? 'Remove from compare' : 'Add to compare';
    compareToggleButton.addEventListener('click', () => toggleCompareAirport(airport.ident));

    tableBody.appendChild(fragment);
  }
}

async function fetchJson(url) {
  const response = await fetch(url);
  if (!response.ok) {
    throw new Error(`Request failed: ${response.status}`);
  }
  return response.json();
}

async function loadAirports() {
  setLoading(true);
  const query = buildQueryString();
  const url = query ? `/api/airports?${query}` : '/api/airports';

  try {
    const payload = await fetchJson(url);
    state.rows = payload.data;
    state.selected = state.selected.filter((ident) => state.rows.some((row) => row.ident === ident));
    renderRows();
    renderCount();
    syncCompareButton();
  } finally {
    setLoading(false);
  }
}

async function populateCountries() {
  const payload = await fetchJson('/api/filter-options');
  for (const country of payload.data) {
    const option = document.createElement('option');
    option.value = country.code;
    option.textContent = country.name;
    countrySelect.appendChild(option);
  }
}

function renderDetailField(label, value) {
  const wrapper = document.createElement('div');
  const term = document.createElement('dt');
  const description = document.createElement('dd');
  term.textContent = label;
  description.textContent = value;
  wrapper.append(term, description);
  detailList.appendChild(wrapper);
}

async function openDetails(ident) {
  setLoading(true);

  try {
    const payload = await fetchJson(`/api/airports/${ident}`);
    const airport = payload.data;
    detailList.innerHTML = '';
    renderDetailField('Airport', airport.name);
    renderDetailField('Code', `${airport.ident} / ${airport.iataCode || '—'}`);
    renderDetailField('Country', airport.countryName);
    renderDetailField('Region', airport.regionName);
    renderDetailField('City', airport.municipality || '—');
    renderDetailField('Runway count', String(airport.runwayCount));
    renderDetailField('Shortest runway', formatFeet(airport.shortestRunwayFt));
    renderDetailField('Longest runway', formatFeet(airport.longestRunwayFt));
    renderDetailField('Lighted runways', String(airport.lightedRunwayCount));
    renderDetailField('Scheduled service', airport.scheduledService ? 'Yes' : 'No');
    detailPanel.hidden = false;
  } finally {
    setLoading(false);
  }
}

function toggleCompareAirport(ident) {
  if (state.selected.includes(ident)) {
    state.selected = state.selected.filter((value) => value !== ident);
  } else if (state.selected.length < 2) {
    state.selected = [...state.selected, ident];
  } else {
    state.selected = [state.selected[1], ident];
  }

  renderRows();
  syncCompareButton();
}

async function openComparison() {
  if (state.selected.length !== 2) {
    return;
  }

  setLoading(true);

  try {
    const params = new URLSearchParams({
      left: state.selected[0],
      right: state.selected[1],
    });
    const payload = await fetchJson(`/api/compare?${params.toString()}`);
    const { left, right, longestRunwayDifferenceFt, shortestRunwayDifferenceFt, elevationDifferenceFt, pairLabel } = payload.data;

    compareSummary.innerHTML = `
      <p><strong>Pair:</strong> ${pairLabel}</p>
      <p><strong>Left airport:</strong> ${left.name} (${left.ident})</p>
      <p><strong>Right airport:</strong> ${right.name} (${right.ident})</p>
      <p><strong>Longest runway difference:</strong> ${longestRunwayDifferenceFt.toLocaleString()} ft</p>
      <p><strong>Shortest runway difference:</strong> ${shortestRunwayDifferenceFt.toLocaleString()} ft</p>
      <p><strong>Elevation difference:</strong> ${elevationDifferenceFt.toLocaleString()} ft</p>
    `;
    comparePanel.hidden = false;
  } finally {
    setLoading(false);
  }
}

function downloadCurrentView() {
  const query = buildQueryString();
  const href = query ? `/api/export?${query}` : '/api/export';
  const anchor = document.createElement('a');
  anchor.href = href;
  anchor.download = '';
  document.body.appendChild(anchor);
  anchor.click();
  anchor.remove();
}

applyFiltersButton.addEventListener('click', () => {
  loadAirports().catch((error) => {
    countEl.textContent = error.message;
  });
});

clearFiltersButton.addEventListener('click', () => {
  searchInput.value = '';
  countrySelect.value = '';
  minRunwayInput.value = '';
  detailPanel.hidden = true;
  comparePanel.hidden = true;
  loadAirports().catch((error) => {
    countEl.textContent = error.message;
  });
});

compareButton.addEventListener('click', () => {
  openComparison().catch((error) => {
    compareSummary.textContent = error.message;
    comparePanel.hidden = false;
  });
});

exportButton.addEventListener('click', downloadCurrentView);

async function bootstrap() {
  maybeApplyDeferredTheme();
  scheduleResultsSummaryLoad();
  scheduleInsightsLoad();
  await populateCountries();
  await loadAirports();
}

bootstrap().catch((error) => {
  countEl.textContent = error.message;
});
