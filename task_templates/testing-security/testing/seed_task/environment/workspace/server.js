const express = require('express');
const fs = require('fs');
const path = require('path');
const { parse } = require('csv-parse/sync');

const app = express();
const PORT = Number(process.env.PORT || 3000);
const DATA_DIR = process.env.AIRPORT_DATA_DIR || '/app/workspace/data';
const ACCESS_LOG_FILE = process.env.AIRPORT_OPS_ACCESS_LOG || '/tmp/airport-ops-access.log';
const NETWORK_DELAY_MS = Number(process.env.AIRPORT_OPS_DELAY_MS || 120);
const MUTATION_MODE = process.env.AIRPORT_OPS_MUTATION_MODE || '';
const PUBLIC_DIR = path.join(__dirname, 'public');
const INDEX_TEMPLATE = fs.readFileSync(path.join(PUBLIC_DIR, 'index.html'), 'utf8');

function readCsv(relativePath) {
  const fullPath = path.join(DATA_DIR, relativePath);
  return parse(fs.readFileSync(fullPath, 'utf8'), {
    columns: true,
    skip_empty_lines: true,
  });
}

function toInt(value) {
  if (value === null || value === undefined || value === '') {
    return null;
  }
  const parsed = Number(value);
  return Number.isFinite(parsed) ? parsed : null;
}

function sleep(ms) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

const airports = readCsv('airports.csv');
const countries = readCsv('countries.csv');
const regions = readCsv('regions.csv');
const runways = readCsv('runways.csv');

const countryByCode = new Map(countries.map((row) => [row.code, row]));
const regionByCode = new Map(regions.map((row) => [row.code, row]));
const runwaysByIdent = new Map();

for (const runway of runways) {
  const bucket = runwaysByIdent.get(runway.airport_ident) || [];
  bucket.push(runway);
  runwaysByIdent.set(runway.airport_ident, bucket);
}

function buildAirportSummary(airport) {
  const airportRunways = (runwaysByIdent.get(airport.ident) || [])
    .map((row) => ({
      lengthFt: toInt(row.length_ft),
      widthFt: toInt(row.width_ft),
      surface: row.surface || 'UNKNOWN',
      lighted: row.lighted === '1',
      closed: row.closed === '1',
      leIdent: row.le_ident,
      heIdent: row.he_ident,
    }))
    .filter((row) => row.lengthFt !== null);

  const lengths = airportRunways.map((row) => row.lengthFt);
  const shortestRunwayFt = lengths.length ? Math.min(...lengths) : null;
  const longestRunwayFt = lengths.length ? Math.max(...lengths) : null;
  const lightedRunwayCount = airportRunways.filter((row) => row.lighted && !row.closed).length;
  const country = countryByCode.get(airport.iso_country);
  const region = regionByCode.get(airport.iso_region);

  return {
    ident: airport.ident,
    icaoCode: airport.gps_code || airport.ident,
    iataCode: airport.iata_code || '',
    name: airport.name,
    countryCode: airport.iso_country,
    countryName: country ? country.name : airport.iso_country,
    regionCode: airport.iso_region,
    regionName: region ? region.name : airport.iso_region,
    municipality: airport.municipality || '',
    type: airport.type,
    continent: airport.continent,
    latitudeDeg: Number(airport.latitude_deg),
    longitudeDeg: Number(airport.longitude_deg),
    elevationFt: toInt(airport.elevation_ft),
    scheduledService: airport.scheduled_service === 'yes',
    runwayCount: airportRunways.length,
    lightedRunwayCount,
    shortestRunwayFt,
    longestRunwayFt,
    runwaySurfaces: Array.from(new Set(airportRunways.map((row) => row.surface))).sort(),
  };
}

const airportSummaries = airports.map(buildAirportSummary).sort((left, right) => {
  return left.name.localeCompare(right.name);
});

const airportByIdent = new Map(airportSummaries.map((airport) => [airport.ident, airport]));

function filterAirports({ q = '', country = '', minRunwayLength = '' }) {
  const trimmedQuery = q.trim().toLowerCase();
  const trimmedCountry = country.trim().toUpperCase();
  const minLength = minRunwayLength === '' ? null : Number(minRunwayLength);

  return airportSummaries.filter((airport) => {
    if (MUTATION_MODE !== 'ignore-country-filter' && trimmedCountry && airport.countryCode !== trimmedCountry) {
      return false;
    }

    if (minLength !== null && Number.isFinite(minLength)) {
      if (airport.longestRunwayFt === null || airport.longestRunwayFt < minLength) {
        return false;
      }
    }

    if (!trimmedQuery) {
      return true;
    }

    const haystackFields =
      MUTATION_MODE === 'search-name-disabled'
        ? [airport.ident, airport.icaoCode, airport.iataCode]
        : [
            airport.ident,
            airport.icaoCode,
            airport.iataCode,
            airport.name,
            airport.municipality,
            airport.countryName,
          ];

    const haystack = haystackFields.join(' ').toLowerCase();

    return haystack.includes(trimmedQuery);
  });
}

function csvEscape(value) {
  const text = String(value ?? '');
  if (text.includes(',') || text.includes('"') || text.includes('\n')) {
    return `"${text.replace(/"/g, '""')}"`;
  }
  return text;
}

function writeAuditEntry(entry) {
  const line = JSON.stringify({
    timestamp: new Date().toISOString(),
    ...entry,
  });
  fs.appendFileSync(ACCESS_LOG_FILE, `${line}\n`, 'utf8');
}

function renderIndexHtml() {
  const themeBootstrap = `<script>(function(){const theme=localStorage.getItem('theme')==='dark'?'dark':'light';document.documentElement.dataset.theme=theme;})();</script>`;
  const themeFlickerOverlay =
    MUTATION_MODE === 'theme-flicker'
      ? `
        <style id="theme-flicker-cover">
          html::before {
            content: '';
            position: fixed;
            inset: 0;
            background: rgba(255, 255, 255, 0.98);
            pointer-events: none;
            z-index: 2147483647;
          }
        </style>
        <script>(function(){let frames=0;function step(){frames+=1;if(frames>=2){const node=document.getElementById('theme-flicker-cover');if(node){node.remove();}return;}requestAnimationFrame(step);}requestAnimationFrame(step);})();</script>
      `
      : '';
  const uiFlags = {
    summaryReserveMode: MUTATION_MODE === 'insights-layout-shift' ? 'compact' : 'full',
    insightsReserveMode: MUTATION_MODE === 'insights-layout-shift' ? 'compact' : 'full',
    lowerAreaShiftMode: MUTATION_MODE === 'insights-lateral-shift' ? 'lateral' : 'none',
  };

  return INDEX_TEMPLATE
    .replace('__THEME_BOOTSTRAP__', `${themeBootstrap}${themeFlickerOverlay}`)
    .replace('__UI_FLAGS__', JSON.stringify(uiFlags));
}

app.use((req, res, next) => {
  res.locals.audit = {};
  res.on('finish', () => {
    if (!req.path.startsWith('/api/')) {
      return;
    }

    writeAuditEntry({
      method: req.method,
      path: req.path,
      status: res.statusCode,
      query: req.query,
      ...res.locals.audit,
    });
  });
  next();
});

app.get('/', (req, res) => {
  res.type('html').send(renderIndexHtml());
});

app.use(express.static(PUBLIC_DIR, { index: false }));

app.get('/api/filter-options', async (req, res) => {
  await sleep(NETWORK_DELAY_MS);
  const options = countries
    .map((row) => ({ code: row.code, name: row.name }))
    .sort((left, right) => left.name.localeCompare(right.name));
  res.locals.audit = {
    kind: 'filter-options',
    resultCount: options.length,
  };
  res.json({ data: options });
});

app.get('/api/airports', async (req, res) => {
  await sleep(NETWORK_DELAY_MS);
  const rows = filterAirports({
    q: req.query.q || '',
    country: req.query.country || '',
    minRunwayLength: req.query.minRunwayLength || '',
  });

  res.locals.audit = {
    kind: 'list',
    resultCount: rows.length,
    matchedIdents: rows.map((row) => row.ident),
  };

  res.json({
    data: rows,
    meta: {
      count: rows.length,
      filters: {
        q: req.query.q || '',
        country: req.query.country || '',
        minRunwayLength: req.query.minRunwayLength || '',
      },
    },
  });
});

app.get('/api/airports/:ident', async (req, res) => {
  await sleep(NETWORK_DELAY_MS);
  const airport = airportByIdent.get(req.params.ident.toUpperCase());
  if (!airport) {
    res.locals.audit = {
      kind: 'detail-miss',
      airportIdent: req.params.ident.toUpperCase(),
    };
    return res.status(404).json({ error: { code: 'airport_not_found' } });
  }

  res.locals.audit = {
    kind: 'detail',
    airportIdent: airport.ident,
  };

  if (MUTATION_MODE === 'detail-region-swap' && airport.ident === 'YSSY') {
    return res.json({
      data: {
        ...airport,
        regionName: 'Queensland',
      },
    });
  }

  if (MUTATION_MODE === 'detail-kjfk-region-swap' && airport.ident === 'KJFK') {
    return res.json({
      data: {
        ...airport,
        regionName: 'California',
      },
    });
  }

  res.json({ data: airport });
});

app.get('/api/compare', async (req, res) => {
  await sleep(NETWORK_DELAY_MS);
  const left = airportByIdent.get(String(req.query.left || '').toUpperCase());
  const right = airportByIdent.get(String(req.query.right || '').toUpperCase());

  if (!left || !right || left.ident === right.ident) {
    res.locals.audit = {
      kind: 'compare-invalid',
      left: req.query.left || '',
      right: req.query.right || '',
    };
    return res.status(400).json({ error: { code: 'invalid_compare_pair' } });
  }

  const summary = {
    left,
    right,
    longestRunwayDifferenceFt: (right.longestRunwayFt || 0) - (left.longestRunwayFt || 0),
    shortestRunwayDifferenceFt: (right.shortestRunwayFt || 0) - (left.shortestRunwayFt || 0),
    elevationDifferenceFt: (right.elevationFt || 0) - (left.elevationFt || 0),
    sameCountry: left.countryCode === right.countryCode,
    sameContinent: left.continent === right.continent,
    pairLabel: `${left.ident} vs ${right.ident}`,
  };

  res.locals.audit = {
    kind: 'compare',
    left: left.ident,
    right: right.ident,
  };

  if (MUTATION_MODE === 'compare-summary-bug') {
    return res.json({
      data: {
        ...summary,
        longestRunwayDifferenceFt: summary.longestRunwayDifferenceFt + 500,
        sameCountry: false,
      },
    });
  }

  if (MUTATION_MODE === 'compare-kjfk-yssy-difference-bug' && left.ident === 'KJFK' && right.ident === 'YSSY') {
    return res.json({
      data: {
        ...summary,
        longestRunwayDifferenceFt: summary.longestRunwayDifferenceFt + 750,
      },
    });
  }

  if (MUTATION_MODE === 'compare-kjfk-klax-difference-bug' && left.ident === 'KJFK' && right.ident === 'KLAX') {
    return res.json({
      data: {
        ...summary,
        longestRunwayDifferenceFt: summary.longestRunwayDifferenceFt - 700,
      },
    });
  }

  res.json({ data: summary });
});

app.get('/api/export', async (req, res) => {
  await sleep(NETWORK_DELAY_MS);
  let rows = (MUTATION_MODE === 'export-unfiltered' ? airportSummaries : filterAirports({
    q: req.query.q || '',
    country: req.query.country || '',
    minRunwayLength: req.query.minRunwayLength || '',
  }));

  if (MUTATION_MODE === 'export-region-column-bug') {
    rows = rows.map((row) =>
      row.ident === 'KJFK'
        ? {
            ...row,
            regionName: 'California',
          }
        : row
    );
  }

  if (
    MUTATION_MODE === 'export-us-12000-klax-region-bug' &&
    (req.query.country || '').toString().toUpperCase() === 'US' &&
    (req.query.minRunwayLength || '').toString() === '12000'
  ) {
    rows = rows.map((row) =>
      row.ident === 'KLAX'
        ? {
            ...row,
            regionName: 'Nevada',
          }
        : row
    );
  }

  const csvRows = [
    [
      'ident',
      'iata_code',
      'name',
      'country',
      'region',
      'municipality',
      'runway_count',
      'shortest_runway_ft',
      'longest_runway_ft',
    ].join(','),
    ...rows.map((row) =>
      [
        row.ident,
        row.iataCode,
        row.name,
        row.countryName,
        row.regionName,
        row.municipality,
        row.runwayCount,
        row.shortestRunwayFt ?? '',
        row.longestRunwayFt ?? '',
      ]
        .map(csvEscape)
        .join(',')
    ),
  ];

  const countrySegment = (req.query.country || 'all').toString().toLowerCase();
  const runwaySegment = (req.query.minRunwayLength || '0').toString();
  const fileName = `airport-export-${countrySegment}-${runwaySegment}.csv`;

  res.locals.audit = {
    kind: 'export',
    resultCount: rows.length,
    matchedIdents: rows.map((row) => row.ident),
    filename: fileName,
  };

  res.setHeader('Content-Type', 'text/csv; charset=utf-8');
  res.setHeader('Content-Disposition', `attachment; filename="${fileName}"`);
  res.send(`${csvRows.join('\n')}\n`);
});

app.get('/health', (req, res) => {
  res.json({ ok: true });
});

app.listen(PORT, () => {
  console.log(`Airport Ops Console listening on http://127.0.0.1:${PORT}`);
});
