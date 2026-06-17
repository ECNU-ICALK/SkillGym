You are building the first release of a tenant-scoped vulnerability advisory service. The workspace already contains a runnable Node.js service scaffold and local data snapshots, but the current implementation does not satisfy the delivery contract required for partner use.

Input data is in `/app/workspace/`:
- `service/`: the existing Node.js / Express service scaffold and runtime helpers.
- `data/nvd_cves.ndjson`: advisory records with identifiers, descriptions, vendors, product metadata, severity, and references.
- `data/kev_catalog.json`: a curated exploited-vulnerability catalog.
- `data/epss_scores.csv`: exploitability scores keyed by CVE ID.
- `data/tenants.json`: tenant keys, scopes, roles, quotas, and export entitlements.
- `data/export_jobs.json`: export job seed records and artifact metadata references.

Your task:
1. Complete the tenant-facing HTTP API for `/api/v1/advisories`, `/api/v1/advisories/:cveId`, `/api/v1/bulk-lookups`, and `/api/v1/export-jobs` without changing the service entrypoint or replacing the current stack.
2. Make the advisory list support stable pagination and common filters, and make the detail, bulk lookup, and export flows use the provided local data files as the source of record for advisory content and tenant policy.
3. Enforce API key authentication, tenant scopes, role checks, quota limits, and export restrictions so invalid credentials, malformed input, oversized bulk requests, and unauthorized export attempts fail cleanly. Only analyst tenants may create, inspect, or download export jobs, even when another tenant still carries related export scope or entitlement metadata.
4. Ensure each accepted export job writes one CSV artifact under `/app/workspace/output/exports/`, persists mutable runtime job state through the existing runtime state path, and only exports the data slice allowed by the caller's tenant configuration.

Output:
- Modify the existing implementation under `/app/workspace/service/`.
- Accepted export jobs must write a CSV file under `/app/workspace/output/exports/`.
- Each export CSV must include advisory columns for CVE ID, vendor, product, severity, CVSS v3 base score, EPSS, KEV flag, published timestamp, and description.
- Keep the existing startup entrypoint unchanged.

Notes:
- Treat the files under `/app/workspace/data/` as read-only input snapshots for advisory content, tenant configuration, and initial export-job seed records.
- The deployment environment provides runtime configuration through its existing process environment.
- Keep credential or signing material in the existing runtime configuration rather than embedding fixed secret values in source.
- Persist mutable export-job records and generated artifacts through the existing runtime state and output paths rather than rewriting the input snapshots.
- Do not modify the input data files to sidestep missing behavior.
- Do not treat tenant-scope denials as ordinary missing data or silently omit unauthorized rows from an otherwise successful response.
- Do not remove authentication, authorization, tenant scoping, quota enforcement, or export controls to make requests pass.
- Do not hardcode a fixed set of responses for the expected test inputs.
- Do not special-case individual CVE IDs, tenants, or query strings.
- Do not fetch external data at request time.
