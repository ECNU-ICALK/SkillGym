#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import re
import sys
from html import unescape
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse


PORT = int(os.environ.get("SEO_AUDIT_PORT", "8139"))
ROOT = Path("/root/workspace/site")
DIST = ROOT / "dist"
LOG_PATH = Path("/var/log/seo-audit/access.log")
INPUT_ROOT = Path("/root/workspace/seo_inputs")

sys.path.insert(0, str(ROOT))
from build_site import load_json, load_pages, normalize_path, path_to_fs, source_hash  # type: ignore


TITLE_RE = re.compile(r"<title>(.*?)</title>", re.S | re.I)
DESC_RE = re.compile(r'<meta name="description" content="(.*?)"', re.I)
ROBOTS_RE = re.compile(r'<meta name="robots" content="(.*?)"', re.I)
CANONICAL_RE = re.compile(r'<link rel="canonical" href="(.*?)"', re.I)
H1_RE = re.compile(r"<h1>(.*?)</h1>", re.S | re.I)
ANCHOR_RE = re.compile(r'<a [^>]*href="([^"]+)"[^>]*>(.*?)</a>', re.I | re.S)
TAG_RE = re.compile(r"<[^>]+>")
JSONLD_RE = re.compile(r'<script type="application/ld\+json">(.*?)</script>', re.S | re.I)
REFRESH_RE = re.compile(r'<meta http-equiv="refresh" content="0; url=([^"]+)"', re.I)
LOC_RE = re.compile(r"<loc>(.*?)</loc>")
MAIN_RE = re.compile(r"<main>(.*?)</main>", re.S | re.I)

REQUIREMENTS = {
    "product-analytics": {
        "required_schema_types": ["SoftwareApplication"],
        "required_schema_kind": "software_application",
        "required_application_category": "AnalyticsApplication",
        "required_offer_category": "product analytics",
        "required_incoming_sources": ["/", "/docs/", "/pricing/", "/error-monitoring/"],
        "min_incoming_internal_links": 4,
        "min_keyword_anchor_links": 4,
    },
    "error-monitoring": {
        "required_schema_types": ["SoftwareApplication"],
        "required_schema_kind": "software_application",
        "required_application_category": "DeveloperApplication",
        "required_offer_category": "error monitoring",
        "required_incoming_sources": ["/", "/docs/", "/pricing/", "/product-analytics/"],
        "min_incoming_internal_links": 4,
        "min_keyword_anchor_links": 4,
    },
    "pricing": {
        "required_schema_types": ["OfferCatalog"],
        "required_schema_kind": "offer_catalog",
        "required_offer_names": ["Startup", "Scale-up", "Platform"],
        "required_incoming_sources": ["/", "/docs/", "/product-analytics/", "/error-monitoring/"],
        "min_incoming_internal_links": 4,
        "min_keyword_anchor_links": 4,
    },
}


def read_manifest() -> dict:
    return load_json(INPUT_ROOT / "site_manifest.json")


def read_keyword_map() -> dict[str, dict]:
    rows = {}
    lines = (INPUT_ROOT / "keyword_map.csv").read_text(encoding="utf-8").strip().splitlines()
    headers = lines[0].split(",")
    for line in lines[1:]:
        values = line.split(",")
        rows[values[0]] = dict(zip(headers, values))
    return rows


def main_scope(html: str) -> str:
    match = MAIN_RE.search(html)
    return match.group(1) if match else html


def normalize_anchor_text(text: str) -> str:
    return re.sub(r"\s+", " ", unescape(TAG_RE.sub("", text))).strip()


def main_internal_anchor_pairs(html: str) -> list[dict[str, str]]:
    pairs = []
    for href, label in ANCHOR_RE.findall(main_scope(html)):
        if href.startswith("/"):
            pairs.append({
                "href": normalize_path(href),
                "anchor_text": normalize_anchor_text(label),
            })
    return pairs


def read_build_meta() -> dict | None:
    path = DIST / ".build-meta.json"
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def build_current() -> bool:
    meta = read_build_meta()
    return bool(meta and meta.get("source_hash") == source_hash())


def page_html_for_path(path: str) -> str | None:
    file_path = path_to_fs(path)
    if not file_path.exists():
        return None
    return file_path.read_text(encoding="utf-8")


def parse_structured_items(html: str) -> list[dict]:
    found: list[dict] = []
    for match in JSONLD_RE.findall(html):
        try:
            payload = json.loads(match)
        except json.JSONDecodeError:
            continue
        if isinstance(payload, list):
            items = payload
        else:
            items = [payload]
        for item in items:
            if isinstance(item, dict):
                found.append(item)
    return found


def parse_structured_types(html: str) -> list[str]:
    found = []
    for item in parse_structured_items(html):
        if "@type" not in item:
            continue
        item_type = item["@type"]
        if isinstance(item_type, list):
            found.extend(str(v) for v in item_type)
        else:
            found.append(str(item_type))
    return sorted(dict.fromkeys(found))


def read_sitemap_urls() -> list[str]:
    path = DIST / "sitemap.xml"
    if not path.exists():
        return []
    text = path.read_text(encoding="utf-8")
    return LOC_RE.findall(text)


def read_redirects() -> dict[str, str]:
    path = DIST / "redirects.json"
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def type_matches(item: dict, target_type: str) -> bool:
    current = item.get("@type")
    if isinstance(current, list):
        return target_type in [str(v) for v in current]
    return str(current) == target_type


def schema_details_for_page(page_id: str, html: str, expected_url: str) -> tuple[bool, list[str]]:
    items = parse_structured_items(html)
    requirements = REQUIREMENTS[page_id]
    if requirements["required_schema_kind"] == "software_application":
        candidates = [item for item in items if type_matches(item, "SoftwareApplication")]
        if not candidates:
            return False, ["missing SoftwareApplication item"]
        for item in candidates:
            offers = item.get("offers")
            if isinstance(offers, list):
                offer_items = [offer for offer in offers if isinstance(offer, dict)]
            elif isinstance(offers, dict):
                offer_items = [offers]
            else:
                offer_items = []
            if (
                isinstance(item.get("name"), str)
                and item.get("name").strip()
                and item.get("applicationCategory") == requirements["required_application_category"]
                and any(
                    offer.get("url") == expected_url and offer.get("category") == requirements["required_offer_category"]
                    for offer in offer_items
                )
            ):
                return True, []
        return False, [
            "SoftwareApplication requires non-empty name",
            f"SoftwareApplication.applicationCategory must be {requirements['required_application_category']}",
            f"SoftwareApplication.offers must include url={expected_url}",
            f"SoftwareApplication.offers must include category={requirements['required_offer_category']}",
        ]

    candidates = [item for item in items if type_matches(item, "OfferCatalog")]
    if not candidates:
        return False, ["missing OfferCatalog item"]
    required_names = set(requirements["required_offer_names"])
    for item in candidates:
        offer_items = item.get("itemListElement", [])
        if not isinstance(offer_items, list):
            continue
        seen_names = {offer.get("name") for offer in offer_items if isinstance(offer, dict)}
        if required_names.issubset(seen_names):
            return True, []
    return False, [
        "OfferCatalog.itemListElement must include Startup",
        "OfferCatalog.itemListElement must include Scale-up",
        "OfferCatalog.itemListElement must include Platform",
    ]


def collect_pages() -> dict[str, dict]:
    manifest = read_manifest()
    keyword_map = read_keyword_map()
    redirects = read_redirects()
    sitemap_urls = set(read_sitemap_urls())
    source_pages = load_pages()
    pages: dict[str, dict] = {}

    outgoing_by_path: dict[str, list[dict[str, str]]] = {}
    is_redirect_by_path: dict[str, bool] = {}

    for page in source_pages.values():
        path = normalize_path(page["path"])
        html = page_html_for_path(path) or ""
        outgoing_by_path[path] = main_internal_anchor_pairs(html)
        is_redirect_by_path[path] = bool(REFRESH_RE.search(html))

    for legacy in manifest["legacy_paths"]:
        path = normalize_path(legacy["source_path"])
        html = page_html_for_path(path) or ""
        outgoing_by_path[path] = main_internal_anchor_pairs(html)
        is_redirect_by_path[path] = bool(REFRESH_RE.search(html))

    incoming_sources = {normalize_path(item["expected_path"]): set() for item in manifest["target_pages"]}
    incoming_keyword_anchor_sources = {normalize_path(item["expected_path"]): set() for item in manifest["target_pages"]}

    for item in manifest["target_pages"]:
        expected_path = normalize_path(item["expected_path"])
        keyword = keyword_map[item["page_id"]]["primary_keyword"].lower()
        for source_path, links in outgoing_by_path.items():
            if is_redirect_by_path.get(source_path):
                continue
            for link in links:
                if link["href"] != expected_path:
                    continue
                incoming_sources[expected_path].add(source_path)
                if keyword in link["anchor_text"].lower():
                    incoming_keyword_anchor_sources[expected_path].add(source_path)

    for item in manifest["target_pages"]:
        page_id = item["page_id"]
        expected_path = normalize_path(item["expected_path"])
        html = page_html_for_path(expected_path) or ""
        keyword = keyword_map[page_id]["primary_keyword"]
        requirements = REQUIREMENTS[page_id]
        title_min = int(keyword_map[page_id]["title_min"])
        title_max = int(keyword_map[page_id]["title_max"])
        page_incoming_sources = sorted(incoming_sources[expected_path])
        page_keyword_sources = sorted(incoming_keyword_anchor_sources[expected_path])
        incoming_count = len(page_incoming_sources)
        keyword_anchor_count = len(page_keyword_sources)
        title = unescape(TITLE_RE.search(html).group(1)).strip() if TITLE_RE.search(html) else ""
        meta_description = unescape(DESC_RE.search(html).group(1)).strip() if DESC_RE.search(html) else ""
        robots = unescape(ROBOTS_RE.search(html).group(1)).strip().lower() if ROBOTS_RE.search(html) else ""
        canonical = unescape(CANONICAL_RE.search(html).group(1)).strip() if CANONICAL_RE.search(html) else ""
        h1 = unescape(H1_RE.search(html).group(1)).strip() if H1_RE.search(html) else ""
        structured_types = parse_structured_types(html)
        expected_url = "https://acme-observe.test" + expected_path
        schema_ok, schema_details = schema_details_for_page(page_id, html, expected_url)
        required_sources = sorted(requirements["required_incoming_sources"])
        missing_required_sources = sorted(set(required_sources) - set(page_incoming_sources))
        missing_keyword_anchor_sources = sorted(set(required_sources) - set(page_keyword_sources))

        blockers = []
        if not build_current():
            blockers.append("build_stale")
        if not html:
            blockers.append("missing_page")
        if "noindex" in robots:
            blockers.append("not_indexable")
        if canonical != expected_url:
            blockers.append("canonical_mismatch")
        if not title or keyword.lower() not in title.lower():
            blockers.append("title_keyword")
        if len(title) < title_min or len(title) > title_max:
            blockers.append("title_length")
        if not h1 or keyword.lower() not in h1.lower():
            blockers.append("h1_keyword")
        if not meta_description:
            blockers.append("meta_description_missing")
        if incoming_count < int(requirements["min_incoming_internal_links"]) or missing_required_sources:
            blockers.append("discovery_path")
        if keyword_anchor_count < int(requirements["min_keyword_anchor_links"]) or missing_keyword_anchor_sources:
            blockers.append("discovery_anchor")
        if expected_url not in sitemap_urls:
            blockers.append("sitemap_missing")
        required_types = set(requirements["required_schema_types"])
        if not required_types.issubset(set(structured_types)) or not schema_ok:
            blockers.append("structured_data")

        pages[page_id] = {
            "page_id": page_id,
            "url": expected_url,
            "primary_keyword": keyword,
            "indexable": "noindex" not in robots and bool(html),
            "canonical_url": canonical,
            "title": title,
            "meta_description": meta_description,
            "h1": h1,
            "title_length": len(title),
            "primary_keyword_in_title": keyword.lower() in title.lower(),
            "primary_keyword_in_h1": keyword.lower() in h1.lower(),
            "meta_description_present": bool(meta_description),
            "canonical_self_referencing": canonical == expected_url,
            "incoming_internal_links": incoming_count,
            "incoming_internal_sources": page_incoming_sources,
            "keyword_anchor_links": keyword_anchor_count,
            "incoming_keyword_anchor_sources": page_keyword_sources,
            "required_incoming_sources": required_sources,
            "missing_required_sources": missing_required_sources,
            "missing_keyword_anchor_sources": missing_keyword_anchor_sources,
            "structured_data_types": structured_types,
            "structured_data_ok": required_types.issubset(set(structured_types)) and schema_ok,
            "structured_data_requirements": schema_details,
            "in_sitemap": expected_url in sitemap_urls,
            "blockers": blockers,
        }
    return pages


def crawl_payload() -> dict:
    manifest = read_manifest()
    pages = collect_pages()
    redirects = read_redirects()
    legacy_checks = []
    sitemap_urls = set(read_sitemap_urls())
    for legacy in manifest["legacy_paths"]:
        source_path = normalize_path(legacy["source_path"])
        target_page = next(item for item in manifest["target_pages"] if item["page_id"] == legacy["target_page_id"])
        target_path = normalize_path(target_page["expected_path"])
        html = page_html_for_path(source_path) or ""
        redirect_target = normalize_path(REFRESH_RE.search(html).group(1)) if REFRESH_RE.search(html) else None
        legacy_checks.append({
            "source_path": source_path,
            "target_path": target_path,
            "normalized": redirects.get(source_path) == target_path and redirect_target == target_path,
            "source_in_sitemap": "https://acme-observe.test" + source_path in sitemap_urls,
        })
    return {
        "site_id": manifest["site_id"],
        "build_current": build_current(),
        "target_pages": list(pages.values()),
        "legacy_checks": legacy_checks,
    }


def sitemap_payload() -> dict:
    manifest = read_manifest()
    urls = read_sitemap_urls()
    expected = {"https://acme-observe.test" + normalize_path(item["expected_path"]) for item in manifest["target_pages"]}
    legacy = {"https://acme-observe.test" + normalize_path(item["source_path"]) for item in manifest["legacy_paths"]}
    return {
        "sitemap_path": str(DIST / "sitemap.xml"),
        "urls": urls,
        "expected_urls_present": expected.issubset(set(urls)),
        "unexpected_urls": sorted(set(urls) & legacy),
    }


def link_graph_payload() -> dict:
    manifest = read_manifest()
    pages = collect_pages()
    graph = []
    for item in manifest["target_pages"]:
        path = normalize_path(item["expected_path"])
        html = page_html_for_path(path) or ""
        outgoing = main_internal_anchor_pairs(html)
        graph.append({
            "page_id": item["page_id"],
            "path": path,
            "outgoing_internal_links": outgoing,
            "incoming_internal_links": pages[item["page_id"]]["incoming_internal_links"],
            "incoming_internal_sources": pages[item["page_id"]]["incoming_internal_sources"],
            "keyword_anchor_links": pages[item["page_id"]]["keyword_anchor_links"],
            "incoming_keyword_anchor_sources": pages[item["page_id"]]["incoming_keyword_anchor_sources"],
            "required_incoming_sources": pages[item["page_id"]]["required_incoming_sources"],
        })
    return {
        "build_current": build_current(),
        "pages": graph,
    }


class Handler(BaseHTTPRequestHandler):
    server_version = "SeoAudit/1.0"

    def log_json(self, status: int) -> None:
        parsed = urlparse(self.path)
        record = {
            "client": self.headers.get("X-Client", "unknown"),
            "method": self.command,
            "path": parsed.path,
            "query": parsed.query,
            "status": status,
        }
        LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
        with LOG_PATH.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(record, sort_keys=True) + "\n")

    def write_json(self, payload: dict, status: int = 200) -> None:
        body = json.dumps(payload, indent=2, sort_keys=True).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)
        self.log_json(status)

    def write_text(self, text: str, status: int = 200, content_type: str = "text/html; charset=utf-8") -> None:
        body = text.encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)
        self.log_json(status)

    def do_GET(self) -> None:
        parsed = urlparse(self.path)
        if parsed.path == "/health":
            return self.write_json({"ok": True, "service": "seo-audit"})
        if parsed.path == "/api/crawl":
            return self.write_json(crawl_payload())
        if parsed.path == "/api/release-gate":
            payload = crawl_payload()
            payload["sitemap_summary"] = sitemap_payload()
            payload["blockers_present"] = any(page["blockers"] for page in payload["target_pages"]) or any(
                not item["normalized"] or item["source_in_sitemap"] for item in payload["legacy_checks"]
            )
            return self.write_json(payload)
        if parsed.path.startswith("/api/page/"):
            page_id = parsed.path.rsplit("/", 1)[-1]
            pages = collect_pages()
            if page_id not in pages:
                return self.write_json({"error": "not_found"}, status=404)
            return self.write_json(pages[page_id])
        if parsed.path == "/api/sitemap":
            return self.write_json(sitemap_payload())
        if parsed.path == "/api/link-graph":
            return self.write_json(link_graph_payload())
        if parsed.path == "/sitemap.xml":
            path = DIST / "sitemap.xml"
            if path.exists():
                return self.write_text(path.read_text(encoding="utf-8"), content_type="application/xml; charset=utf-8")

        file_path = path_to_fs(parsed.path)
        if file_path.exists():
            return self.write_text(file_path.read_text(encoding="utf-8"))
        return self.write_text("<h1>not found</h1>", status=404)


def main() -> None:
    if not (DIST / ".build-meta.json").exists():
        os.system("python3 /root/workspace/site/build_site.py >/tmp/site-build.log 2>&1")
    server = ThreadingHTTPServer(("127.0.0.1", PORT), Handler)
    server.serve_forever()


if __name__ == "__main__":
    main()
