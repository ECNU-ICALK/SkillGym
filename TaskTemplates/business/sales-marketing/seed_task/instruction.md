You need to remove organic-search release blockers for a developer-tools SaaS team's product marketing site before launch. The team has placed the site source code, keyword plan, historical snapshots, reference materials, and the current release validation pipeline into this container, but the growth team still cannot approve this release.

Input data is inside the container:

- `/root/workspace/site/`: the marketing site source code and build scripts.
- `/root/workspace/seo_inputs/site_manifest.json`: site entrypoints, target pages, the official build command, and output requirements.
- `/root/workspace/seo_inputs/keyword_map.csv`: target pages, primary keywords, secondary keywords, search intent, page type, and title constraints.
- `/root/workspace/seo_inputs/search_console_snapshot.json`: an earlier export of index coverage, queries, and landing-page performance; it may be outdated.
- `/root/workspace/seo_inputs/crawl_snapshot.ndjson`: an earlier crawl snapshot of pages and on-site signals; it may only cover some URLs and no longer reflect the current real site.
- `/root/workspace/seo_inputs/content_briefs/`: per-page briefs including product positioning, feature facts, audience, forbidden claims, and allowable evidence.
- `/root/workspace/seo_inputs/reference_pages/`: a normalized reference packet derived from public product pages, docs pages, and pricing pages.
- The container also provides local preview and validation tools required by the current release checks.

## Your Task

1. Review the target pages, site source code, historical snapshots, and the current release validation results to identify the root causes preventing target pages from meeting the launch bar.
2. Without changing the site's core product positioning or each page's intended use, fix these release blockers so all target pages meet the requirements defined in `site_manifest.json` and `keyword_map.csv`.
3. Rebuild the site using the official build, and use the container's current validation pipeline to confirm the target pages now meet the release criteria.
4. Produce a machine-readable fix report, a keyword coverage table, and a short summary for the growth lead.

## Business Rules

1. Every target page listed in `site_manifest.json` must be checked; no omissions.
2. `search_console_snapshot.json` and `crawl_snapshot.ndjson` are historical context only and must not replace the actual validation results from the current build.
3. All target pages must ultimately meet the release bar; you must not evade issues by deleting pages, switching them to noindex, adding robots blocking, replacing them with placeholder pages, or changing the pages' intended purpose.
4. The page positioning, keyword mapping, and title constraints defined in `keyword_map.csv` must be followed; do not rewrite target keywords or loosen the bar on your own.
5. If a historical URL has been replaced by a new page, you must handle it per the site's rules via a canonical redirect or canonicalization merge; do not keep competing duplicate official pages.
6. Page facts must come from allowable evidence in the existing source code, content briefs, or reference packets. Do not fabricate product capabilities, customer cases, performance numbers, integration counts, security/compliance commitments, or market rankings.

## Output Format

If `/root/output/` does not exist, create it first.

Write `/root/output/seo_fixes_report.json` with the following structure:

```json
{
  "site_id": "site-000",
  "target_pages": [
    {
      "page_id": "pricing",
      "url": "https://example.test/pricing",
      "primary_keyword": "string",
      "indexable": true,
      "canonical_url": "https://example.test/pricing",
      "title": "string",
      "meta_description": "string",
      "h1": "string",
      "incoming_internal_links": 2,
      "structured_data_types": ["SoftwareApplication"],
      "fixes_applied": ["string"],
      "evidence_refs": ["brief:pricing", "ref:posthog-pricing"]
    }
  ],
  "sitemap_summary": {
    "sitemap_path": "string",
    "expected_urls_present": true,
    "unexpected_urls": []
  },
  "redirects_or_canonicalizations": [
    {
      "source_url": "string",
      "target_url": "string",
      "reason": "string"
    }
  ],
  "remaining_risks": [
    {
      "page_id": "string",
      "risk": "string",
      "why_not_blocking": "string"
    }
  ],
  "validation": {
    "build_status": "pass",
    "seo_audit_status": "pass"
  }
}
```

Requirements:

- `target_pages` must cover all target pages in `site_manifest.json`, and each `page_id` may appear only once.
- `indexable` must be `true` or `false`.
- `canonical_url` must be the final official canonical URL.
- `incoming_internal_links` must be a JSON number.
- `structured_data_types` must list the schema type(s) for this page as detected by the current release validation pipeline.
- `fixes_applied` must list at least the key fixes applied to the page.
- `evidence_refs` must include at least 2 references, with at least 1 from `content_briefs/` and at least 1 from `reference_pages/`.
- `validation.build_status` and `validation.seo_audit_status` must both be `pass`.

Write `/root/output/keyword_coverage.csv` with column names exactly as follows:

```csv
page_id,url,primary_keyword,secondary_keywords,title_length,primary_keyword_in_title,primary_keyword_in_h1,meta_description_present,canonical_self_referencing,indexable,incoming_internal_links,structured_data_ok
```

Requirements:

- Must cover all target pages.
- `secondary_keywords` must be `|`-separated.
- `title_length` must be numeric.
- `primary_keyword_in_title`, `primary_keyword_in_h1`, `meta_description_present`, `canonical_self_referencing`, `indexable`, and `structured_data_ok` must be `true` or `false`.

Write `/root/output/growth_summary.md`. It must include:

- the site ID;
- the number of target pages fixed;
- any remaining non-blocking risks;
- a summary of sitemap and canonicalization handling;
- a summary of keyword coverage;
- the most important changes to on-site discovery paths;
- the most important structured data changes;
- a short release recommendation to the growth lead.

## Notes

- Do not modify any input files under `/root/workspace/seo_inputs/`.
- Do not treat historical snapshots as the sole source of truth, and do not bypass the actual validation pipeline in this container.
- Do not replace real site fixes with a static hand-written report, fabricated crawl results, fabricated structured-data results, or cached answers.
- Do not evade issues by deleting target pages, disabling build checks, disabling sitemap validation, removing discovery-path requirements, or reducing functionality.
- Do not modify verifier files, task metadata, environment files, or any `skills` directory content.
- You may write helper scripts in the working directory, but in the end you only need to submit the 3 required files under `/root/output/` and keep the site-fix results in place.

