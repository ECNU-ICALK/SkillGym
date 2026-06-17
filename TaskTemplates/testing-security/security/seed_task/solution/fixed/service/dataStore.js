const fs = require('fs');
const path = require('path');

function resolveRoot(dir, fallback) {
  return path.resolve(dir || fallback);
}

function readJson(filePath) {
  return JSON.parse(fs.readFileSync(filePath, 'utf8'));
}

function readNdjson(filePath) {
  return fs
    .readFileSync(filePath, 'utf8')
    .split(/\r?\n/)
    .map((line) => line.trim())
    .filter(Boolean)
    .map((line) => JSON.parse(line));
}

function readCsv(filePath) {
  const text = fs.readFileSync(filePath, 'utf8').trim();
  const [headerLine, ...lines] = text.split(/\r?\n/);
  const headers = headerLine.split(',');
  return lines.filter(Boolean).map((line) => {
    const values = line.split(',');
    const row = {};
    headers.forEach((header, index) => {
      row[header] = values[index] ?? '';
    });
    return row;
  });
}

function csvEscape(value) {
  const text = value === null || value === undefined ? '' : String(value);
  if (/[",\n\r]/.test(text)) {
    return `"${text.replace(/"/g, '""')}"`;
  }
  return text;
}

function loadInputs({ dataDir, stateDir, outputDir }) {
  const root = resolveRoot(dataDir, path.join(process.cwd(), 'data'));
  const stateRoot = resolveRoot(stateDir, path.join(process.cwd(), 'state'));
  const outputRoot = resolveRoot(outputDir, path.join(process.cwd(), 'output', 'exports'));
  const advisoriesRaw = readNdjson(path.join(root, 'nvd_cves.ndjson'));
  const kevRaw = readJson(path.join(root, 'kev_catalog.json'));
  const epssRaw = readCsv(path.join(root, 'epss_scores.csv'));
  const tenantsRaw = readJson(path.join(root, 'tenants.json'));

  const epssByCve = new Map(epssRaw.map((row) => [row.cve, row]));
  const kevByCve = new Map((kevRaw.vulnerabilities || []).map((row) => [row.cveID, row]));
  const tenantsByKey = new Map((tenantsRaw.tenants || []).map((tenant) => [tenant.api_key, tenant]));

  const advisories = advisoriesRaw.map((row) => {
    const epss = epssByCve.get(row.cve_id);
    const kev = kevByCve.get(row.cve_id);
    return {
      cve_id: row.cve_id,
      published: row.published,
      modified: row.modified,
      vendor: String(row.vendor || '').toLowerCase(),
      product: String(row.product || '').toLowerCase(),
      severity: String(row.severity || '').toLowerCase(),
      cvss_v3_base_score: Number(row.cvss_v3_base_score || 0),
      epss: epss ? Number(epss.epss) : Number(row.epss || 0),
      percentile: epss ? Number(epss.percentile) : null,
      kev: Boolean(kev) || Boolean(row.kev),
      kev_vendor: kev ? kev.vendorProject : null,
      kev_product: kev ? kev.product : null,
      description: row.description || '',
      references: Array.isArray(row.references) ? row.references.slice() : [],
    };
  });

  const statePath = path.join(stateRoot, 'runtime_state.json');
  const state = readJson(statePath);
  if (!state.request_counters) state.request_counters = {};
  if (!Array.isArray(state.export_jobs)) state.export_jobs = [];
  if (typeof state.next_export_job_seq !== 'number') {
    state.next_export_job_seq = state.export_jobs.length + 1;
  }

  return {
    outputRoot,
    statePath,
    advisories,
    tenantsByKey,
    state,
  };
}

function saveState(store) {
  fs.writeFileSync(store.statePath, JSON.stringify(store.state, null, 2) + '\n', 'utf8');
}

function isValidCveId(value) {
  return /^CVE-\d{4}-\d{4,}$/.test(value);
}

function allowTenantAdvisories(rows, tenant) {
  const allowlist = new Set((tenant.vendor_allowlist || []).map((item) => String(item).toLowerCase()));
  return rows.filter((row) => allowlist.has(row.vendor));
}

function parseBool(value) {
  if (value === undefined || value === null) return null;
  if (value === true || value === 'true' || value === '1') return true;
  if (value === false || value === 'false' || value === '0') return false;
  return null;
}

function sortRows(rows, sortKey) {
  const reverse = String(sortKey || '-published').startsWith('-');
  const key = reverse ? String(sortKey).slice(1) : String(sortKey || 'published');
  const accessor = (row) => {
    if (key === 'epss') return row.epss;
    if (key === 'cvss' || key === 'cvss_v3_base_score') return row.cvss_v3_base_score;
    if (key === 'published') return row.published;
    if (key === 'severity') return row.severity;
    if (key === 'vendor') return row.vendor;
    return row.published;
  };
  return rows.slice().sort((left, right) => {
    const a = accessor(left);
    const b = accessor(right);
    let cmp;
    if (typeof a === 'number' && typeof b === 'number') {
      cmp = a - b;
    } else {
      cmp = String(a).localeCompare(String(b));
    }
    if (cmp === 0) {
      cmp = left.cve_id.localeCompare(right.cve_id);
    }
    return reverse ? -cmp : cmp;
  });
}

function filterRows(rows, tenant, filters) {
  let scoped = allowTenantAdvisories(rows, tenant);
  if (filters.vendor) {
    scoped = scoped.filter((row) => row.vendor === String(filters.vendor).toLowerCase());
  }
  if (filters.severity) {
    scoped = scoped.filter((row) => row.severity === String(filters.severity).toLowerCase());
  }
  if (filters.kev_only !== null) {
    scoped = scoped.filter((row) => row.kev === filters.kev_only);
  }
  if (filters.q) {
    const q = String(filters.q).toLowerCase();
    scoped = scoped.filter((row) => [row.cve_id, row.vendor, row.product, row.description].join(' ').toLowerCase().includes(q));
  }
  return sortRows(scoped, filters.sort);
}

function paginate(rows, page, pageSize) {
  const start = (page - 1) * pageSize;
  return rows.slice(start, start + pageSize);
}

function writeExportCsv(outputDir, exportId, rows) {
  fs.mkdirSync(outputDir, { recursive: true });
  const filePath = path.join(outputDir, `${exportId}.csv`);
  const lines = [
    'cve_id,vendor,product,severity,cvss_v3_base_score,epss,kev,published,description',
    ...rows.map((row) =>
      [
        csvEscape(row.cve_id),
        csvEscape(row.vendor),
        csvEscape(row.product),
        csvEscape(row.severity),
        csvEscape(row.cvss_v3_base_score),
        csvEscape(row.epss),
        csvEscape(row.kev ? 'true' : 'false'),
        csvEscape(row.published),
        csvEscape(row.description),
      ].join(',')
    ),
  ];
  fs.writeFileSync(filePath, lines.join('\n') + '\n', 'utf8');
  return filePath;
}

module.exports = {
  loadInputs,
  saveState,
  isValidCveId,
  allowTenantAdvisories,
  parseBool,
  filterRows,
  paginate,
  writeExportCsv,
};
