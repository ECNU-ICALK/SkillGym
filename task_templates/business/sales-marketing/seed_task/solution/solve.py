#!/usr/bin/env python3
from __future__ import annotations

import csv
import json
import subprocess
import urllib.request
from pathlib import Path


WORKSPACE = Path("/root/workspace")
SITE_ROOT = WORKSPACE / "site"
INPUT_ROOT = WORKSPACE / "seo_inputs"
OUTPUT_ROOT = Path("/root/output")
PAGES_DIR = SITE_ROOT / "src" / "pages"
REDIRECTS_PATH = SITE_ROOT / "src" / "redirects.json"
SITE_CONFIG_PATH = SITE_ROOT / "site_config.json"


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload: dict) -> None:
    path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")


def fetch_json(path: str) -> dict:
    req = urllib.request.Request(f"http://127.0.0.1:8139{path}", headers={"X-Client": "solution-seo"})
    with urllib.request.urlopen(req, timeout=10) as resp:
        return json.loads(resp.read().decode("utf-8"))


def load_page(page_id: str) -> dict:
    return load_json(PAGES_DIR / f"{page_id}.json")


def save_page(page: dict) -> None:
    (PAGES_DIR / f"{page['page_id']}.json").write_text(json.dumps(page, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def patch_pages() -> None:
    site_config = load_json(SITE_CONFIG_PATH)
    site_config["canonical_overrides"] = {}
    site_config["sitemap_allowlist"] = [
        "/",
        "/docs/",
        "/product-analytics/",
        "/error-monitoring/",
        "/pricing/",
    ]
    write_json(SITE_CONFIG_PATH, site_config)

    home = load_page("home")
    home["body_blocks"][1]["links"] = [
        {"href": "/product-analytics/", "label": "Explore product analytics"},
        {"href": "/error-monitoring/", "label": "Explore error monitoring"},
        {"href": "/pricing/", "label": "See pricing"},
        {"href": "/docs/", "label": "Read the docs"}
    ]
    save_page(home)

    docs = load_page("docs")
    docs["body_blocks"][1]["links"] = [
        {"href": "/product-analytics/", "label": "Product analytics setup"},
        {"href": "/error-monitoring/", "label": "Error monitoring rollout"},
        {"href": "/pricing/", "label": "Pricing plans"}
    ]
    save_page(docs)

    analytics = load_page("product-analytics")
    analytics["title"] = "Product Analytics for Event-Driven SaaS Teams"
    analytics["meta_description"] = "Acme Observe gives product analytics teams release-aware funnels, event timelines, and feature usage context."
    analytics["h1"] = "Product analytics with release-aware funnels"
    analytics["canonical_path"] = "/product-analytics/"
    analytics["structured_data"] = [
        {
            "@context": "https://schema.org",
            "@type": "SoftwareApplication",
            "name": "Acme Observe Product Analytics",
            "applicationCategory": "AnalyticsApplication",
            "offers": {
                "@type": "Offer",
                "url": "https://acme-observe.test/product-analytics/",
                "category": "product analytics"
            }
        }
    ]
    analytics["body_blocks"].append(
        {
            "type": "links",
            "links": [
                {"href": "/error-monitoring/", "label": "Explore error monitoring"},
                {"href": "/pricing/", "label": "Pricing for product analytics teams"}
            ]
        }
    )
    save_page(analytics)

    monitoring = load_page("error-monitoring")
    monitoring["title"] = "Error Monitoring for Release Teams"
    monitoring["meta_description"] = "Acme Observe brings error monitoring, stack traces, release markers, and impacted user flows into one triage workflow."
    monitoring["h1"] = "Error monitoring for release-critical teams"
    monitoring["indexable"] = True
    monitoring["structured_data"] = [
        {
            "@context": "https://schema.org",
            "@type": "SoftwareApplication",
            "name": "Acme Observe Error Monitoring",
            "applicationCategory": "DeveloperApplication",
            "offers": {
                "@type": "Offer",
                "url": "https://acme-observe.test/error-monitoring/",
                "category": "error monitoring"
            }
        }
    ]
    monitoring["body_blocks"].append(
        {
            "type": "links",
            "links": [
                {"href": "/product-analytics/", "label": "Product analytics for release investigation"},
                {"href": "/pricing/", "label": "Pricing for error monitoring teams"}
            ]
        }
    )
    save_page(monitoring)

    pricing = load_page("pricing")
    pricing["title"] = "Pricing for Product and Platform Teams"
    pricing["meta_description"] = "Usage-based pricing for startup, scale-up, and platform teams running Acme Observe."
    pricing["h1"] = "Pricing for product analytics and error monitoring"
    pricing["include_in_sitemap"] = True
    pricing["structured_data"] = [
        {
            "@context": "https://schema.org",
            "@type": "OfferCatalog",
            "name": "Acme Observe pricing",
            "itemListElement": [
                {"@type": "Offer", "name": "Startup"},
                {"@type": "Offer", "name": "Scale-up"},
                {"@type": "Offer", "name": "Platform"}
            ]
        }
    ]
    pricing["body_blocks"].append(
        {
            "type": "links",
            "links": [
                {"href": "/product-analytics/", "label": "Product analytics pricing guide"},
                {"href": "/error-monitoring/", "label": "Error monitoring pricing guide"}
            ]
        }
    )
    save_page(pricing)

    redirects = {
        "/analytics/": "/product-analytics/",
        "/monitoring/": "/error-monitoring/",
        "/plans/": "/pricing/"
    }
    write_json(REDIRECTS_PATH, redirects)


def build_site() -> None:
    subprocess.run(["python3", str(SITE_ROOT / "build_site.py")], check=True, capture_output=True, text=True)


def load_keyword_rows() -> dict[str, dict]:
    with (INPUT_ROOT / "keyword_map.csv").open(newline="", encoding="utf-8") as fh:
        return {row["page_id"]: row for row in csv.DictReader(fh)}


def write_outputs() -> None:
    gate = fetch_json("/api/release-gate")
    if not gate["build_current"] or gate["blockers_present"]:
        raise RuntimeError(json.dumps(gate, indent=2, sort_keys=True))

    keyword_rows = load_keyword_rows()
    evidence_map = {
        "product-analytics": ["brief:product-analytics", "ref:posthog-product-analytics"],
        "error-monitoring": ["brief:error-monitoring", "ref:sentry-error-monitoring"],
        "pricing": ["brief:pricing", "ref:posthog-pricing"],
    }
    fixes_map = {
        "product-analytics": ["updated canonical target", "added keyword-aligned title and h1", "added SoftwareApplication schema", "improved discovery paths"],
        "error-monitoring": ["removed noindex state", "aligned title and h1 to keyword intent", "added SoftwareApplication schema", "improved discovery paths"],
        "pricing": ["restored sitemap inclusion", "added meta description", "added OfferCatalog schema"]
    }

    report = {
        "site_id": gate["site_id"],
        "target_pages": [],
        "sitemap_summary": gate["sitemap_summary"],
        "redirects_or_canonicalizations": [],
        "remaining_risks": [
            {
                "page_id": "pricing",
                "risk": "Reference packets reflect public page patterns, not competitor metrics.",
                "why_not_blocking": "The release gate only requires source-backed Acme Observe facts and the current pricing page meets the crawl gate."
            }
        ],
        "validation": {
            "build_status": "pass",
            "seo_audit_status": "pass"
        }
    }

    for page in gate["target_pages"]:
        report["target_pages"].append({
            "page_id": page["page_id"],
            "url": page["url"],
            "primary_keyword": page["primary_keyword"],
            "indexable": page["indexable"],
            "canonical_url": page["canonical_url"],
            "title": page["title"],
            "meta_description": page["meta_description"],
            "h1": page["h1"],
            "incoming_internal_links": page["incoming_internal_links"],
            "structured_data_types": page["structured_data_types"],
            "fixes_applied": fixes_map[page["page_id"]],
            "evidence_refs": evidence_map[page["page_id"]],
        })

    for item in gate["legacy_checks"]:
        report["redirects_or_canonicalizations"].append({
            "source_url": "https://acme-observe.test" + item["source_path"],
            "target_url": "https://acme-observe.test" + item["target_path"],
            "reason": "Legacy competing URL normalized to the canonical launch page."
        })

    OUTPUT_ROOT.mkdir(parents=True, exist_ok=True)
    write_json(OUTPUT_ROOT / "seo_fixes_report.json", report)

    with (OUTPUT_ROOT / "keyword_coverage.csv").open("w", newline="", encoding="utf-8") as fh:
        fieldnames = [
            "page_id",
            "url",
            "primary_keyword",
            "secondary_keywords",
            "title_length",
            "primary_keyword_in_title",
            "primary_keyword_in_h1",
            "meta_description_present",
            "canonical_self_referencing",
            "indexable",
            "incoming_internal_links",
            "structured_data_ok",
        ]
        writer = csv.DictWriter(fh, fieldnames=fieldnames)
        writer.writeheader()
        for page in gate["target_pages"]:
            keyword_row = keyword_rows[page["page_id"]]
            writer.writerow({
                "page_id": page["page_id"],
                "url": page["url"],
                "primary_keyword": keyword_row["primary_keyword"],
                "secondary_keywords": keyword_row["secondary_keywords"],
                "title_length": page["title_length"],
                "primary_keyword_in_title": str(page["primary_keyword_in_title"]).lower(),
                "primary_keyword_in_h1": str(page["primary_keyword_in_h1"]).lower(),
                "meta_description_present": str(page["meta_description_present"]).lower(),
                "canonical_self_referencing": str(page["canonical_self_referencing"]).lower(),
                "indexable": str(page["indexable"]).lower(),
                "incoming_internal_links": page["incoming_internal_links"],
                "structured_data_ok": str(page["structured_data_ok"]).lower(),
            })

    summary = f"""# Growth Summary

Site: {gate['site_id']}

- Repaired target pages: {len(gate['target_pages'])}
- Target page IDs: product-analytics, error-monitoring, pricing
- Canonical and sitemap normalization covered: /analytics/ -> /product-analytics/, /monitoring/ -> /error-monitoring/, /plans/ -> /pricing/
- Discovery-path changes: homepage and docs now link directly to product analytics and error monitoring; docs also links to pricing.
- Structured data changes: SoftwareApplication schema added to product analytics and error monitoring; OfferCatalog schema added to pricing.
- Keyword coverage: all target pages now contain their primary keyword in both title and H1 and pass the live release gate.
- Non-blocking risk: Reference packets reflect public page patterns, not competitor metrics.

Release recommendation: proceed with launch after publishing the rebuilt site and keeping the current redirect map in place.
"""
    (OUTPUT_ROOT / "growth_summary.md").write_text(summary, encoding="utf-8")


def main() -> None:
    fetch_json("/api/release-gate")
    for page_id in ["product-analytics", "error-monitoring", "pricing"]:
        fetch_json(f"/api/page/{page_id}")
    fetch_json("/api/sitemap")
    fetch_json("/api/link-graph")
    patch_pages()
    build_site()
    write_outputs()


if __name__ == "__main__":
    main()
