const fs = require('fs');
const path = require('path');
const express = require('express');
const crypto = require('crypto');

const {
  loadInputs,
  saveState,
  isValidCveId,
  allowTenantAdvisories,
  parseBool,
  filterRows,
  paginate,
  writeExportCsv,
} = require('./dataStore');

function asInt(value) {
  if (value === undefined || value === null || value === '') return null;
  if (!/^\d+$/.test(String(value))) return null;
  return Number(value);
}

function createApp({ dataDir, stateDir, outputDir } = {}) {
  const store = loadInputs({ dataDir, stateDir, outputDir });
  const exportSigningSecret = process.env.EXPORT_SIGNING_SECRET || 'unsafe-dev-export-signing-secret';
  const app = express();
  app.use(express.json({ limit: '128kb' }));

  app.get('/health', (_req, res) => {
    res.json({ ok: true });
  });

  function setRateHeaders(res, tenant, remaining) {
    res.setHeader('X-RateLimit-Limit', String(tenant.daily_quota));
    res.setHeader('X-RateLimit-Remaining', String(Math.max(0, remaining)));
  }

  app.use((req, res, next) => {
    if (req.path === '/health') return next();
    const apiKey = req.header('X-Partner-Key');
    if (!apiKey) {
      return res.status(401).json({ error: { code: 'missing_api_key', message: 'X-Partner-Key is required.' } });
    }
    const tenant = store.tenantsByKey.get(apiKey);
    if (!tenant) {
      return res.status(401).json({ error: { code: 'invalid_api_key', message: 'Unknown partner key.' } });
    }
    const current = Number(store.state.request_counters[tenant.tenant_id] || 0);
    if (current >= tenant.daily_quota) {
      setRateHeaders(res, tenant, 0);
      res.setHeader('Retry-After', '60');
      return res.status(429).json({ error: { code: 'rate_limited', message: 'Rate limit exceeded.' } });
    }
    store.state.request_counters[tenant.tenant_id] = current + 1;
    saveState(store);
    setRateHeaders(res, tenant, tenant.daily_quota - store.state.request_counters[tenant.tenant_id]);
    req.tenant = tenant;
    next();
  });

  function requireScope(scope) {
    return (req, res, next) => {
      if (!req.tenant.scopes.includes(scope)) {
        return res.status(403).json({ error: { code: 'insufficient_scope', message: 'Tenant is not allowed to perform this action.' } });
      }
      next();
    };
  }

  function parseFilters(tenant, source) {
    const filters = source && typeof source === 'object' && source.filters && typeof source.filters === 'object' ? source.filters : source;
    const page = asInt(filters.page) || 1;
    const pageSize = asInt(filters.page_size) || 20;
    const kevOnly = parseBool(filters.kev_only);
    if (!Number.isInteger(page) || page < 1) {
      return { error: { status: 422, body: { error: { code: 'validation_error', message: 'page must be a positive integer.' } } } };
    }
    if (!Number.isInteger(pageSize) || pageSize < 1) {
      return { error: { status: 422, body: { error: { code: 'validation_error', message: 'page_size must be a positive integer.' } } } };
    }
    if (pageSize > Number(tenant.max_page_size || 20)) {
      return { error: { status: 422, body: { error: { code: 'validation_error', message: 'page_size exceeds the tenant limit.' } } } };
    }
    return {
      page,
      pageSize,
      vendor: filters.vendor || null,
      severity: filters.severity || null,
      kev_only: kevOnly,
      q: filters.q || null,
      sort: filters.sort || '-published',
    };
  }

  function findAdvisory(tenant, cveId) {
    return allowTenantAdvisories(store.advisories, tenant).find((row) => row.cve_id === cveId) || null;
  }

  app.get('/api/v1/advisories', requireScope('read:advisories'), (req, res) => {
    const parsed = parseFilters(req.tenant, req.query);
    if (parsed.error) {
      return res.status(parsed.error.status).json(parsed.error.body);
    }
    const rows = filterRows(store.advisories, req.tenant, parsed);
    res.json({
      data: paginate(rows, parsed.page, parsed.pageSize),
      meta: {
        total_items: rows.length,
        page: parsed.page,
        page_size: parsed.pageSize,
        has_next: parsed.page * parsed.pageSize < rows.length,
      },
    });
  });

  app.get('/api/v1/advisories/:cveId', requireScope('read:advisories'), (req, res) => {
    if (!isValidCveId(req.params.cveId)) {
      return res.status(422).json({ error: { code: 'validation_error', message: 'cve_id is invalid.' } });
    }
    const row = findAdvisory(req.tenant, req.params.cveId);
    if (!row) {
      return res.status(404).json({ error: { code: 'advisory_not_found', message: 'Advisory not found.' } });
    }
    res.json({ data: row });
  });

  app.post('/api/v1/bulk-lookups', requireScope('bulk:lookups'), (req, res) => {
    const payload = req.body || {};
    if (!Array.isArray(payload.cve_ids)) {
      return res.status(422).json({ error: { code: 'validation_error', message: 'cve_ids must be an array.' } });
    }
    if (payload.cve_ids.length > Number(req.tenant.bulk_lookup_limit || 10)) {
      return res.status(422).json({ error: { code: 'bulk_limit_exceeded', message: 'bulk lookup request is too large.' } });
    }
    const results = [];
    const seen = new Set();
    for (const cveId of payload.cve_ids) {
      if (!isValidCveId(cveId)) {
        return res.status(422).json({ error: { code: 'validation_error', message: 'cve_ids contains an invalid CVE identifier.' } });
      }
      if (seen.has(cveId)) continue;
      seen.add(cveId);
      const row = findAdvisory(req.tenant, cveId);
      if (!row) {
        continue;
      }
      results.push(row);
    }
    res.json({ data: results, meta: { requested: payload.cve_ids.length, returned: results.length } });
  });

  app.post('/api/v1/export-jobs', requireScope('export:advisories'), (req, res) => {
    const payload = req.body || {};
    if (payload.format && payload.format !== 'csv') {
      return res.status(422).json({ error: { code: 'validation_error', message: 'Only csv export is supported.' } });
    }
    const parsed = parseFilters(req.tenant, payload);
    if (parsed.error) {
      return res.status(parsed.error.status).json(parsed.error.body);
    }
    if (parsed.vendor && !req.tenant.vendor_allowlist.map((item) => item.toLowerCase()).includes(String(parsed.vendor).toLowerCase())) {
      return res.status(403).json({ error: { code: 'tenant_scope_violation', message: 'Requested export is outside tenant scope.' } });
    }
    const rows = filterRows(store.advisories, req.tenant, parsed);
    const exportId = `job_${String(store.state.next_export_job_seq).padStart(4, '0')}`;
    store.state.next_export_job_seq += 1;
    const artifactPath = writeExportCsv(store.outputRoot, exportId, rows);
    const job = {
      id: exportId,
      tenant_id: req.tenant.tenant_id,
      status: 'completed',
      row_count: rows.length,
      filters: {
        vendor: parsed.vendor,
        severity: parsed.severity,
        kev_only: parsed.kev_only,
        q: parsed.q,
        sort: parsed.sort,
      },
      artifact_path: artifactPath,
      integrity: crypto.createHmac('sha256', exportSigningSecret).update(exportId).digest('hex'),
      created_at: new Date().toISOString(),
    };
    store.state.export_jobs.push(job);
    saveState(store);
    res.status(201).json({ data: job });
  });

  app.get('/api/v1/export-jobs/:jobId', requireScope('export:advisories'), (req, res) => {
    const job = store.state.export_jobs.find((row) => row.id === req.params.jobId && row.tenant_id === req.tenant.tenant_id);
    if (!job) {
      return res.status(404).json({ error: { code: 'export_job_not_found', message: 'Export job not found.' } });
    }
    res.json({ data: job });
  });

  app.get('/api/v1/export-jobs/:jobId/download', requireScope('export:advisories'), (req, res) => {
    const job = store.state.export_jobs.find((row) => row.id === req.params.jobId && row.tenant_id === req.tenant.tenant_id);
    if (!job) {
      return res.status(404).json({ error: { code: 'export_job_not_found', message: 'Export job not found.' } });
    }
    res.setHeader('Content-Type', 'text/csv; charset=utf-8');
    res.setHeader('Content-Disposition', `attachment; filename="${path.basename(job.artifact_path)}"`);
    res.send(fs.readFileSync(job.artifact_path, 'utf8'));
  });

  app.use((_req, res) => {
    res.status(404).json({ error: { code: 'not_found', message: 'Route not found.' } });
  });

  return app;
}

module.exports = { createApp };
