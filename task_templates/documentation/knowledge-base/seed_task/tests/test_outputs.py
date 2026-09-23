from __future__ import annotations

from conftest import (
    OUTPUT_ROOT,
    contract,
    expected_selection,
    make_alternate_bundle_copy,
    output_manifest,
    output_page,
    parse_cards,
    read_manifest,
    read_page,
    read_report,
    run_build,
    section_block,
)


def test_formal_build_produces_required_outputs() -> None:
    result = run_build()
    assert result.returncode == 0, result.stderr or result.stdout

    payload = contract()
    assert {path.name for path in OUTPUT_ROOT.iterdir()} == {
        payload["output_file"],
        payload["audit_report_file"],
        payload["manifest_file"],
    }


def test_page_shell_is_preserved_and_cleanup_is_applied() -> None:
    result = run_build()
    assert result.returncode == 0, result.stderr or result.stdout

    payload = contract()
    page_text = read_page()
    for required in payload["required_shell_strings"]:
        assert required in page_text
    for token in payload["cleanup_tokens"]:
        assert token not in page_text.lower()
    for forbidden_url in payload["forbidden_urls"]:
        assert forbidden_url not in page_text


def test_selected_resources_match_contract_rules_and_manifest() -> None:
    result = run_build()
    assert result.returncode == 0, result.stderr or result.stdout

    payload = contract()
    expected = expected_selection()
    page_text = read_page()
    manifest = read_manifest()

    expected_ids = [resource["id"] for section in payload["resource_sections"] for resource in expected[section]]
    actual_ids = [item["id"] for item in manifest["selected_resources"]]
    assert actual_ids == expected_ids

    for section_name in payload["resource_sections"]:
        block = section_block(page_text, section_name)
        cards = parse_cards(block)
        assert len(cards) == payload["section_requirements"][section_name]["exact_count"]
        expected_titles = [resource["title"] for resource in expected[section_name]]
        assert [card["title"] for card in cards] == expected_titles
        expected_urls = [resource["canonical_url_from_audit"] for resource in expected[section_name]]
        assert [card["href"] for card in cards] == expected_urls
        for card in cards:
            assert card["body"].count(".") >= 2

    assert manifest["page_path"] == payload["output_file"]
    assert manifest["concept_slug"] == payload["concept_slug"]
    assert manifest["section_counts"] == {
        section_name: payload["section_requirements"][section_name]["exact_count"]
        for section_name in payload["resource_sections"]
    }
    assert output_page().name == payload["output_file"]
    assert output_manifest().name == payload["manifest_file"]


def test_audit_report_tracks_draft_changes_and_coverage() -> None:
    result = run_build()
    assert result.returncode == 0, result.stderr or result.stdout

    report = read_report()
    assert report.lstrip().startswith("# Resource Audit Report")
    assert "## Removed or Replaced" in report
    assert "## Redirect Updates" in report
    assert "## Added Resources" in report
    assert "## Coverage Check" in report
    assert "canonical" in report.lower()
    assert "removed" in report.lower() or "replaced" in report.lower()
    for required in ["reference", "articles", "videos", "books"]:
        assert required in report.lower()


def test_alternate_bundle_forces_reselection_and_dynamic_titles() -> None:
    tmpdir, alt_root = make_alternate_bundle_copy()
    try:
        alt_output = alt_root.parent / "output"
        result = run_build(bundle_root=alt_root, output_root=alt_output)
        assert result.returncode == 0, result.stderr or result.stdout

        manifest = read_manifest(output_root=alt_output, bundle_root=alt_root)
        page_text = read_page(output_root=alt_output, bundle_root=alt_root)
        expected = expected_selection(bundle_root=alt_root)

        article_ids = [resource["id"] for resource in expected["articles"]]
        assert "freecodecamp_escape_async_await_hell" in article_ids
        assert "webdev_async_functions" not in article_ids

        actual_ids = [item["id"] for item in manifest["selected_resources"]]
        expected_ids = [resource["id"] for section in contract(alt_root)["resource_sections"] for resource in expected[section]]
        assert actual_ids == expected_ids
        assert "Async and Await in 100 Seconds — Fireship" in page_text
        assert "A fast visual recap of how `await` reshapes Promise-driven control flow in modern JavaScript." in page_text
    finally:
        tmpdir.cleanup()
