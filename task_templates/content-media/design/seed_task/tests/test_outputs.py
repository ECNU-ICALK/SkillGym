from __future__ import annotations

from pathlib import Path

from playwright.sync_api import sync_playwright

from conftest import (
    CONTRACT_PATH,
    OUTPUT_ROOT,
    expected_context,
    load_json,
    load_soup,
    make_alternate_brief_copy,
    normalize_space,
    page_by_id,
    page_ids_from_soup,
    run_site,
)


def test_formal_build_produces_required_outputs() -> None:
    result = run_site()
    assert result.returncode == 0, result.stderr or result.stdout
    html_path = OUTPUT_ROOT / "north_america_power_mix_brief.html"
    manifest_path = OUTPUT_ROOT / "site_manifest.json"
    assert html_path.exists()
    assert manifest_path.exists()
    assert {path.name for path in OUTPUT_ROOT.iterdir()} == {"north_america_power_mix_brief.html", "site_manifest.json"}
    assert "<!doctype html>" in html_path.read_text(encoding="utf-8").lower()


def test_contract_coverage_and_manifest_alignment() -> None:
    result = run_site()
    assert result.returncode == 0, result.stderr or result.stdout

    context = expected_context()
    soup = load_soup(OUTPUT_ROOT / "north_america_power_mix_brief.html")
    manifest = load_json(OUTPUT_ROOT / "site_manifest.json")

    assert page_ids_from_soup(soup) == context["contract"]["page_order"]
    assert [page["page_id"] for page in manifest["pages"]] == context["contract"]["page_order"]
    assert manifest["site_path"] == "north_america_power_mix_brief.html"
    assert set(manifest["source_files"]) == {
        "data/country_profile.json",
        "data/world_bank_population.json",
        "data/world_bank_gdp.json",
        "data/annual_co2_emissions.csv",
        "data/electricity_prod_source.csv",
    }
    assert manifest["key_metrics"] == {
        "population_year": context["population_year"],
        "gdp_year": context["gdp_year"],
        "co2_year": context["co2_year"],
        "electricity_year": context["electricity_year"],
    }
    required_page_files = {
        "snapshot": {
            "expected": {
                "data/world_bank_population.json",
                "data/world_bank_gdp.json",
                "data/annual_co2_emissions.csv",
                "data/electricity_prod_source.csv",
            },
            "optional": {"data/country_profile.json"},
        },
    }

    for page_contract, page_manifest in zip(context["contract"]["required_pages"], manifest["pages"], strict=True):
        page = page_by_id(soup, page_contract["page_id"])
        assert page is not None, f"Missing page {page_contract['page_id']}"
        module_ids = [node.get("data-module-id") for node in page.select("[data-module-id]")]
        for module_id in page_contract["required_modules"]:
            assert module_id in module_ids, f"{page_contract['page_id']} missing module {module_id}"
        for chart_id in page_contract["required_chart_ids"]:
            assert page.select_one(f'[data-chart-id="{chart_id}"]') is not None, f"{page_contract['page_id']} missing chart {chart_id}"
            assert chart_id in page_manifest["chart_ids"]
        assert set(page_manifest["module_ids"]) == set(page_contract["required_modules"])
        assert page_manifest["title"] == page_contract["title"]
        if page_contract["page_id"] in required_page_files:
            actual_files = set(page_manifest["key_data_files"])
            expected_files = required_page_files[page_contract["page_id"]]["expected"]
            optional_files = required_page_files[page_contract["page_id"]]["optional"]
            assert expected_files.issubset(actual_files)
            assert actual_files - expected_files <= optional_files


def test_html_content_reflects_expected_metrics() -> None:
    result = run_site()
    assert result.returncode == 0, result.stderr or result.stdout

    context = expected_context()
    soup = load_soup(OUTPUT_ROOT / "north_america_power_mix_brief.html")

    snapshot_text = normalize_space(page_by_id(soup, "snapshot").get_text(" ", strip=True))
    for row in context["snapshot_rows"]:
        assert row["country"] in snapshot_text
        assert row["population_m"] in snapshot_text
        assert row["gdp_t"] in snapshot_text
        assert row["co2_mt"] in snapshot_text
        assert row["top_source"] in snapshot_text
        top_source_tokens = {row["top_source_twh"], f"{float(row['top_source_twh']):,.1f}"}
        assert any(token in snapshot_text for token in top_source_tokens)

    power_text = normalize_space(page_by_id(soup, "power-mix").get_text(" ", strip=True))
    assert str(context["electricity_year"]) in power_text
    for row in context["snapshot_rows"]:
        assert row["country"] in power_text
        assert row["top_source"] in power_text
    for label in ["Solar", "Wind", "Hydropower", "Gas", "Coal"]:
        assert label in power_text

    emissions_text = normalize_space(page_by_id(soup, "emissions").get_text(" ", strip=True))
    trend_start = context["co2_trend"][0][0]
    trend_end = context["co2_trend"][-1][0]
    assert str(trend_start) in emissions_text
    assert str(trend_end) in emissions_text
    for country in ["Canada", "Mexico", "United States"]:
        assert country in emissions_text

    implication_cards = [
        normalize_space(node.get_text(" ", strip=True))
        for node in page_by_id(soup, "implications").select(".implication-card")
    ]
    assert len(implication_cards) == len(context["implications"])
    for card in context["implications"]:
        matching_cards = [text for text in implication_cards if card["title"] in text]
        assert matching_cards, f"Missing implication card {card['title']}"
        card_text = matching_cards[0]
        assert card["country"] in card_text
        metric_tokens = {card["metric"], f"{float(card['metric']):,.1f}"}
        assert any(token in card_text for token in metric_tokens)
        year_tokens = [token for token in card["body"].split() if token.isdigit()]
        for token in year_tokens:
            assert token in card_text
        if card["title"] == "Latest clean-generation lead":
            assert "clean" in card_text.lower()
            assert "twh" in card_text.lower() or "generation" in card_text.lower()

    appendix_text = normalize_space(page_by_id(soup, "appendix").get_text(" ", strip=True))
    for row in context["appendix_rows"]:
        assert row["country"] in appendix_text
        assert row["capital"] in appendix_text
        assert row["income"] in appendix_text
        assert row["region"] in appendix_text


def test_browser_navigation_and_viewport_fit() -> None:
    result = run_site()
    assert result.returncode == 0, result.stderr or result.stdout

    html_uri = (OUTPUT_ROOT / "north_america_power_mix_brief.html").resolve().as_uri()
    contract = load_json(CONTRACT_PATH)

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": 1440, "height": 900})
        page.goto(html_uri)
        page.wait_for_timeout(250)

        def active_page_id() -> str:
            return page.locator(".page.is-active").get_attribute("data-page-id")

        def go_to_index(target_index: int) -> None:
            while contract["page_order"].index(active_page_id()) < target_index:
                page.locator("#nav-next").click()
                page.wait_for_timeout(120)
            while contract["page_order"].index(active_page_id()) > target_index:
                page.locator("#nav-prev").click()
                page.wait_for_timeout(120)

        assert page.locator("#nav-prev").count() == 1
        assert page.locator("#nav-next").count() == 1
        assert page.locator('[data-role="progress"]').count() == 1
        assert active_page_id() == "cover"
        progress_text = normalize_space(page.locator('[data-role="progress"]').inner_text())
        assert progress_text.startswith("1")
        assert progress_text.endswith(str(len(contract["page_order"])))

        page.keyboard.press("ArrowRight")
        page.wait_for_timeout(150)
        assert active_page_id() == "agenda"
        page.keyboard.press("ArrowLeft")
        page.wait_for_timeout(150)
        assert active_page_id() == "cover"

        page.locator("#nav-next").click()
        page.wait_for_timeout(150)
        assert active_page_id() == "agenda"

        for profile in contract["viewport_profiles"]:
            page.set_viewport_size({"width": profile["width"], "height": profile["height"]})
            page.wait_for_timeout(100)
            for idx, expected_page_id in enumerate(contract["page_order"]):
                go_to_index(idx)
                assert active_page_id() == expected_page_id
                box = page.locator(".page.is-active").evaluate(
                    """
                    (node) => ({
                      scrollHeight: node.scrollHeight,
                      clientHeight: node.clientHeight,
                      scrollWidth: node.scrollWidth,
                      clientWidth: node.clientWidth
                    })
                    """
                )
                if profile["name"] == "phone-landscape" and expected_page_id == "power-mix":
                    vertical_tolerance = 140
                elif profile["name"] == "phone-landscape":
                    vertical_tolerance = 70
                else:
                    vertical_tolerance = 1
                assert box["scrollHeight"] <= box["clientHeight"] + vertical_tolerance, f"{profile['name']} vertical overflow on {expected_page_id}"
                assert box["scrollWidth"] <= box["clientWidth"] + 1, f"{profile['name']} horizontal overflow on {expected_page_id}"
        browser.close()


def test_alternate_fixture_rerun_updates_content() -> None:
    result = run_site()
    assert result.returncode == 0, result.stderr or result.stdout
    baseline_text = (OUTPUT_ROOT / "north_america_power_mix_brief.html").read_text(encoding="utf-8")

    tmpdir, alt_root = make_alternate_brief_copy()
    try:
        alt_output = Path(tmpdir.name) / "output"
        alt_result = run_site(brief_root=alt_root, output_root=alt_output)
        assert alt_result.returncode == 0, alt_result.stderr or alt_result.stdout

        alt_context = expected_context(alt_root)
        alt_text = (alt_output / "north_america_power_mix_brief.html").read_text(encoding="utf-8")
        alt_manifest = load_json(alt_output / "site_manifest.json")
        assert alt_manifest["key_metrics"] == {
            "population_year": alt_context["population_year"],
            "gdp_year": alt_context["gdp_year"],
            "co2_year": alt_context["co2_year"],
            "electricity_year": alt_context["electricity_year"],
        }
        assert alt_context["snapshot_rows"][0]["gdp_t"] in alt_text
        assert alt_context["snapshot_rows"][-1]["top_source"] in alt_text or alt_context["snapshot_rows"][0]["top_source"] in alt_text
        assert alt_context["implications"][0]["country"] in alt_text
        assert alt_context["implications"][1]["country"] in alt_text
        assert baseline_text != alt_text
    finally:
        tmpdir.cleanup()
