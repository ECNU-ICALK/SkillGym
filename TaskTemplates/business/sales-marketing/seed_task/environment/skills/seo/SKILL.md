# SEO

Use this skill when a task asks you to repair a marketing site so landing pages pass a live SEO release gate. It is most useful when historical crawl snapshots are stale and a local crawl or audit service is the only trustworthy source of the current page state.

## Recommended workflow

1. Read `site_manifest.json` and treat the live `seo-audit` service as authoritative for release-gate status.
2. Before editing source files, probe the live gate:
   - run `seo-audit release-gate`;
   - inspect each target page with `seo-audit page <page-id>`;
   - inspect sitemap and discovery-path state with `seo-audit sitemap` and `seo-audit link-graph`.
3. Make source changes in the site workspace, not just in built artifacts.
4. Rebuild the site with the formal build command from the manifest after every batch of changes.
5. Re-run the live gate and do not stop until every target page is clean and legacy competing URLs are normalized.
6. Write outputs from the audited final state, not from stale snapshots or guesses.

## Common failure modes

- Fixing visible page copy but forgetting to rebuild the site.
- Editing built HTML only, while source files still fail the next build.
- Relying on `search_console_snapshot.json` or `crawl_snapshot.ndjson` instead of the live audit.
- Repairing target pages but leaving legacy competing URLs live in sitemap or discovery paths.
- Improving metadata without fixing internal discovery paths.

## Helper scripts

- `scripts/probe_release_gate.py`: prints the full release-gate payload from the local audit service.
- `scripts/inspect_page.py`: prints the live page audit for one target page.
- `scripts/check_sitemap.py`: prints sitemap and link-graph summaries from the local audit service.

These scripts reduce diagnosis time. You are still responsible for implementing the actual site fixes and matching the task's exact output contract.
