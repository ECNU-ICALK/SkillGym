from __future__ import annotations

import csv
import json

from conftest import CSV_PATH, KEYWORD_ROWS, MANIFEST, REPORT_PATH, SUMMARY_PATH, fetch_json, load_csv_rows, load_json


REQUIRED_REPORT_KEYS = {
    "site_id",
    "target_pages",
    "sitemap_summary",
    "redirects_or_canonicalizations",
    "remaining_risks",
    "validation",
}

CSV_HEADERS = [
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


def test_output_files_exist_and_parse() -> None:
    report = load_json(REPORT_PATH)
    rows = load_csv_rows()
    summary = SUMMARY_PATH.read_text(encoding="utf-8")
    assert set(report) == REQUIRED_REPORT_KEYS
    assert isinstance(rows, list) and rows
    assert summary.strip()


def test_report_covers_all_target_pages_and_validates_live_release_gate() -> None:
    report = load_json(REPORT_PATH)
    live = fetch_json("/api/release-gate")
    expected_ids = [item["page_id"] for item in MANIFEST["target_pages"]]
    report_pages = report["target_pages"]
    assert report["site_id"] == MANIFEST["site_id"]
    assert [item["page_id"] for item in report_pages] == expected_ids
    assert report["validation"] == {"build_status": "pass", "seo_audit_status": "pass"}
    assert live["build_current"] is True
    assert live["blockers_present"] is False
    assert all(not item["blockers"] for item in live["target_pages"])


def test_report_target_pages_match_live_audit_state() -> None:
    report = load_json(REPORT_PATH)
    live = fetch_json("/api/release-gate")
    live_pages = {item["page_id"]: item for item in live["target_pages"]}

    for item in report["target_pages"]:
        page_id = item["page_id"]
        live_item = live_pages[page_id]
        assert item["url"] == live_item["url"]
        assert item["primary_keyword"] == live_item["primary_keyword"]
        assert item["indexable"] is True
        assert item["indexable"] == live_item["indexable"]
        assert item["canonical_url"] == live_item["canonical_url"]
        assert item["title"] == live_item["title"]
        assert item["meta_description"] == live_item["meta_description"]
        assert item["h1"] == live_item["h1"]
        assert item["incoming_internal_links"] == live_item["incoming_internal_links"]
        assert item["incoming_internal_links"] >= 2
        assert set(item["structured_data_types"]) == set(live_item["structured_data_types"])
        assert item["fixes_applied"], f"{page_id} must list key fixes"
        refs = item["evidence_refs"]
        assert isinstance(refs, list) and len(refs) >= 2
        assert any(ref.startswith("brief:") for ref in refs)
        assert any(ref.startswith("ref:") for ref in refs)


def test_legacy_urls_are_normalized_and_kept_out_of_sitemap() -> None:
    report = load_json(REPORT_PATH)
    live = fetch_json("/api/release-gate")
    sitemap = fetch_json("/api/sitemap")
    live_redirects = {
        item["source_path"]: item
        for item in live["legacy_checks"]
    }
    report_redirects = {item["source_url"]: item for item in report["redirects_or_canonicalizations"]}

    assert sitemap["expected_urls_present"] is True
    assert sitemap["unexpected_urls"] == []

    for legacy in MANIFEST["legacy_paths"]:
        source_path = legacy["source_path"]
        target_path = next(
            item["expected_path"] for item in MANIFEST["target_pages"] if item["page_id"] == legacy["target_page_id"]
        )
        live_item = live_redirects[source_path]
        assert live_item["normalized"] is True
        assert live_item["source_in_sitemap"] is False
        report_item = report_redirects["https://acme-observe.test" + source_path]
        assert report_item["target_url"] == "https://acme-observe.test" + target_path


def test_keyword_coverage_matches_live_audit() -> None:
    live = fetch_json("/api/release-gate")
    live_pages = {item["page_id"]: item for item in live["target_pages"]}
    rows = load_csv_rows()
    assert list(rows[0].keys()) == CSV_HEADERS
    assert [row["page_id"] for row in rows] == [item["page_id"] for item in MANIFEST["target_pages"]]

    for row in rows:
        live_item = live_pages[row["page_id"]]
        keyword_row = KEYWORD_ROWS[row["page_id"]]
        assert row["url"] == live_item["url"]
        assert row["primary_keyword"] == keyword_row["primary_keyword"]
        assert row["secondary_keywords"] == keyword_row["secondary_keywords"]
        assert int(row["title_length"]) == live_item["title_length"]
        assert row["primary_keyword_in_title"] == str(live_item["primary_keyword_in_title"]).lower()
        assert row["primary_keyword_in_h1"] == str(live_item["primary_keyword_in_h1"]).lower()
        assert row["meta_description_present"] == str(live_item["meta_description_present"]).lower()
        assert row["canonical_self_referencing"] == str(live_item["canonical_self_referencing"]).lower()
        assert row["indexable"] == str(live_item["indexable"]).lower()
        assert int(row["incoming_internal_links"]) == live_item["incoming_internal_links"]
        assert row["structured_data_ok"] == str(live_item["structured_data_ok"]).lower()


def test_growth_summary_contains_business_recap_not_placeholder_text() -> None:
    text = SUMMARY_PATH.read_text(encoding="utf-8")
    lowered = text.lower()
    assert MANIFEST["site_id"] in text
    for item in MANIFEST["target_pages"]:
        assert item["page_id"] in text
    assert "sitemap" in lowered
    assert "canonical" in lowered or "normalize" in lowered or "规范化" in text
    assert (
        "internal" in lowered
        or "discovery" in lowered
        or "发现路径" in text
        or "站内发现" in text
    )
    assert "structured data" in lowered or "schema" in lowered or "结构化数据" in text
    assert "release" in lowered or "发布" in text or "上线" in text
    assert "risk" in lowered or "风险" in text
    assert "placeholder" not in lowered
    assert "todo" not in lowered
