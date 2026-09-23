from __future__ import annotations

import json
import re
from pathlib import Path

from test_helpers import (
    STUDIO_DIR,
    canvas_hash,
    click_export,
    click_preset,
    console_messages,
    contract,
    encounter_data,
    expected_zone_metrics,
    expected_zone_pressure,
    hash_state,
    page_overview,
    page_session,
    parse_float,
    request_urls,
    sample_groups,
    sample_stats,
    select_zone,
    set_color,
    set_seed,
    set_slider,
)


def test_01_required_files_boot_and_notes() -> None:
    with (STUDIO_DIR / "notes.md").open(encoding="utf-8") as fh:
        notes = fh.read().lower()
    for token in contract()["notes_requirements"]:
        assert token in notes, f"notes.md must mention {token}"

    with page_session() as page:
        overview = page_overview(page)
        assert contract()["page_title"] in overview["title"]
        assert overview["canvasCount"] >= 1, "page must render a canvas"
        assert not [msg for msg in console_messages(page) if msg.startswith("error:")], (
            f"page emitted console errors: {console_messages(page)}"
        )


def test_02_layout_controls_and_local_assets() -> None:
    cfg = contract()
    expected_ids = {
        cfg["required_controls"]["seed"]["display_id"],
        cfg["required_controls"]["seed"]["input_id"],
        cfg["required_controls"]["seed"]["prev_button_id"],
        cfg["required_controls"]["seed"]["next_button_id"],
        cfg["required_controls"]["seed"]["random_button_id"],
        cfg["required_controls"]["seed"]["go_button_id"],
        cfg["required_controls"]["zone"]["select_id"],
        *cfg["required_controls"]["preset"]["button_ids"],
        *(item["id"] for item in cfg["required_controls"]["parameters"]),
        *(item["id"] for item in cfg["required_controls"]["colors"]),
        cfg["required_controls"]["actions"]["regenerate_button_id"],
        cfg["required_controls"]["actions"]["reset_button_id"],
        cfg["required_controls"]["actions"]["export_button_id"],
        cfg["required_controls"]["actions"]["export_status_id"],
        cfg["required_controls"]["actions"]["export_json_id"],
        cfg["summary_contract"]["route_title_id"],
        cfg["summary_contract"]["route_summary_id"],
        *cfg["summary_contract"]["metric_ids"].values(),
        cfg["summary_contract"]["highlight_list_id"],
        cfg["summary_contract"]["source_list_id"],
    }
    with page_session() as page:
        overview = page_overview(page)
        assert expected_ids <= set(overview["idsPresent"]), f"missing ids: {sorted(expected_ids - set(overview['idsPresent']))}"
        shell_state = page.evaluate(
            """
            () => ({
              appShell: Boolean(document.querySelector('.app-shell')),
              sidebar: Boolean(document.querySelector('.sidebar')),
              canvasArea: Boolean(document.querySelector('.canvas-area')),
              canvasContainer: Boolean(document.getElementById('canvas-container')),
              sidebarHeadings: Array.from(document.querySelectorAll('.sidebar .control-section > h3')).map((node) => node.textContent.trim()),
              stageHeadings: Array.from(document.querySelectorAll('.stage > section > h3')).map((node) => node.textContent.trim()),
              pressureCards: document.querySelectorAll('#type-pressure > article.pressure-card').length,
              hasTypeMixBars: Boolean(document.getElementById('type-mix-bars')),
              hasAttackCoverage: Boolean(document.getElementById('attack-coverage')),
              hasExposureProfile: Boolean(document.getElementById('exposure-profile')),
            })
            """
        )
        assert shell_state["appShell"] and shell_state["sidebar"] and shell_state["canvasArea"] and shell_state["canvasContainer"], shell_state
        assert shell_state["sidebarHeadings"] == ["Seed", "Zone", "Preset", "Parameters", "Colors", "Actions"], shell_state["sidebarHeadings"]
        assert shell_state["stageHeadings"] == ["Highlighted Species", "Type Pressure", "Zone Signals", "Source Links"], shell_state["stageHeadings"]
        assert shell_state["pressureCards"] == 3, shell_state
        assert shell_state["hasTypeMixBars"] and shell_state["hasAttackCoverage"] and shell_state["hasExposureProfile"], shell_state
        relation_surface = page.evaluate(
            """
            () => ({
              hasP5Canvas: Boolean(document.querySelector('canvas.p5Canvas')),
              hasTypePressure: Boolean(document.getElementById('type-pressure')),
              hasZoneSignals: Boolean(document.getElementById('zone-signals')),
            })
            """
        )
        assert relation_surface["hasP5Canvas"], "page must render through the bundled local p5 viewer path"
        assert relation_surface["hasTypePressure"] and relation_surface["hasZoneSignals"], "page must keep the existing type-relations sections"
        assert not overview["remoteRefs"], f"remote asset refs are not allowed: {overview['remoteRefs']}"
        assert all(url.startswith("http://127.0.0.1:8765/") for url in request_urls(page)), request_urls(page)


def test_03_zone_switch_updates_data_summary() -> None:
    with page_session() as page:
        for zone in encounter_data()["zones"]:
            select_zone(page, zone["zone_id"])
            overview = page_overview(page)
            metrics = expected_zone_metrics(zone["zone_id"])
            assert zone["zone_label"] in overview["routeTitle"]
            assert len(overview["highlighted"]) >= contract()["summary_contract"]["minimum_highlight_cards"]
            assert {card["speciesId"] for card in overview["highlighted"]} <= metrics["encounter_species"]
            assert parse_float(overview["metrics"]["speciesCount"]) == metrics["species_count"]
            level_parts = [float(match) for match in re.findall(r"-?\d+(?:\.\d+)?", overview["metrics"]["avgLevel"])]
            assert level_parts, f"avg level metric missing numeric content: {overview['metrics']['avgLevel']!r}"
            assert abs(level_parts[0] - metrics["avg_min"]) <= 0.2
            assert abs(level_parts[-1] - metrics["avg_max"]) <= 0.2
            assert abs(parse_float(overview["metrics"]["avgBst"]) - metrics["avg_bst"]) <= 0.2
            mix_text = overview["metrics"]["typeMix"].lower()
            assert any(type_name in mix_text for type_name in metrics["top_types"])
            assert any(link["href"] == zone["source_url"] for link in overview["sourceLinks"])


def test_04_same_seed_regenerate_is_reproducible() -> None:
    with page_session() as page:
        select_zone(page, "kanto-power-plant-area")
        set_seed(page, 24021)
        payload_a = click_export(page)
        hash_a = canvas_hash(page)
        page.click("#regenerate-button")
        page.wait_for_timeout(150)
        payload_b = click_export(page)
        hash_b = canvas_hash(page)
        assert payload_a == payload_b, "same seed + regenerate should keep export payload stable"
        assert payload_a["scene_id"] == payload_b["scene_id"]
        assert hash_a == hash_b, "same seed + regenerate should keep the canvas stable"


def test_05_same_hash_reload_is_reproducible() -> None:
    hash_url = (
        "http://127.0.0.1:8765/workspace/studio/index.html"
        "#seed=54231&zone=seafoam-islands-b1f&preset=storm"
        "&density=0.91&turbulence=0.67&focus=0.39&contrast=0.83"
        "&color1=%23114488&color2=%23c48a2d&color3=%23d14f3f"
    )
    with page_session(url=hash_url) as page:
        overview_a = page_overview(page)
        payload_a = click_export(page)
        hash_a = canvas_hash(page)
        state_a = hash_state(page)
    with page_session(url=hash_url) as page:
        overview_b = page_overview(page)
        payload_b = click_export(page)
        hash_b = canvas_hash(page)
        state_b = hash_state(page)
    assert payload_a == payload_b, "reloading the same seeded URL must keep export payload stable"
    assert hash_a == hash_b, "reloading the same seeded URL must keep the canvas stable"
    assert overview_a["seedInput"] == overview_b["seedInput"] == "54231"
    assert overview_a["zoneValue"] == overview_b["zoneValue"] == "seafoam-islands-b1f"
    assert abs(overview_a["controls"]["density"] - 0.91) <= 0.01
    assert abs(overview_a["controls"]["turbulence"] - 0.67) <= 0.01
    assert abs(overview_a["controls"]["focus"] - 0.39) <= 0.01
    assert abs(overview_a["controls"]["contrast"] - 0.83) <= 0.01
    assert overview_a["colors"]["color1"] == "#114488"
    assert overview_a["colors"]["color2"] == "#c48a2d"
    assert overview_a["colors"]["color3"] == "#d14f3f"
    for key in contract()["shareable_state"]["required_hash_keys"]:
        assert state_a.get(key), f"missing {key} in location hash"
        assert state_b.get(key), f"missing {key} in location hash after reload"
    assert state_a == state_b
    assert state_a["zone"] == "seafoam-islands-b1f"
    assert state_a["seed"] == "54231"


def test_06_different_seed_changes_scene() -> None:
    with page_session() as page:
        select_zone(page, "seafoam-islands-b1f")
        set_seed(page, 24021)
        payload_a = click_export(page)
        hash_a = canvas_hash(page)
        set_seed(page, 24022)
        payload_b = click_export(page)
        hash_b = canvas_hash(page)
        assert payload_a["zone_id"] == payload_b["zone_id"] == "seafoam-islands-b1f"
        assert payload_a["sample_points"] != payload_b["sample_points"], "sample points must react to seed changes"
        assert hash_a != hash_b, "canvas hash must change when seed changes"


def test_07_presets_and_reset_behavior() -> None:
    cfg = contract()
    with page_session() as page:
        for preset_name, preset_values in cfg["presets"].items():
            click_preset(page, preset_name)
            overview = page_overview(page)
            assert abs(overview["controls"]["density"] - preset_values["density"]) <= 0.01
            assert abs(overview["controls"]["turbulence"] - preset_values["turbulence"]) <= 0.01
            assert abs(overview["controls"]["focus"] - preset_values["focus"]) <= 0.01
            assert abs(overview["controls"]["contrast"] - preset_values["contrast"]) <= 0.01

        select_zone(page, "rock-tunnel-1f")
        set_seed(page, 777)
        set_slider(page, "density-control", 1.1)
        set_color(page, "color1", "#114488")
        page.click("#reset-button")
        page.wait_for_timeout(150)
        overview = page_overview(page)
        default = cfg["presets"][cfg["default_preset"]]
        assert overview["zoneValue"] == cfg["default_zone_id"]
        assert overview["seedInput"] == str(cfg["default_seed"])
        assert str(cfg["default_seed"]) in overview["seedDisplay"]
        assert abs(overview["controls"]["density"] - default["density"]) <= 0.01
        assert abs(overview["controls"]["turbulence"] - default["turbulence"]) <= 0.01
        assert abs(overview["controls"]["focus"] - default["focus"]) <= 0.01
        assert abs(overview["controls"]["contrast"] - default["contrast"]) <= 0.01
        assert overview["colors"]["color1"] == cfg["required_controls"]["colors"][0]["default"]
        assert overview["colors"]["color2"] == cfg["required_controls"]["colors"][1]["default"]
        assert overview["colors"]["color3"] == cfg["required_controls"]["colors"][2]["default"]


def test_08_color_controls_change_canvas_but_not_scene_geometry() -> None:
    with page_session() as page:
        select_zone(page, "viridian-forest-area")
        before = page_overview(page)
        hash_before = canvas_hash(page)
        export_before = click_export(page)
        set_color(page, "color1", "#114488")
        set_color(page, "color3", "#d14f3f")
        after = page_overview(page)
        hash_after = canvas_hash(page)
        export_after = click_export(page)
        assert after["colors"]["color1"] == "#114488"
        assert after["colors"]["color3"] == "#d14f3f"
        assert hash_before != hash_after, "changing theme colors must change the rendered scene"
        assert before["routeTitle"] == after["routeTitle"]
        assert before["metrics"] == after["metrics"]
        assert export_before["type_mix"] == export_after["type_mix"]
        assert export_before["sample_points"] == export_after["sample_points"]
        state = hash_state(page)
        assert state["color1"] == "#114488"
        assert state["color3"] == "#d14f3f"


def test_09_export_download_and_payload_schema() -> None:
    cfg = contract()
    expected_species = expected_zone_metrics("kanto-safari-zone-middle")["encounter_species"]
    with page_session() as page:
        select_zone(page, "kanto-safari-zone-middle")
        click_preset(page, "storm")
        with page.expect_download() as download_info:
            page.click("#export-button")
        page.wait_for_timeout(120)
        payload = json.loads(page.locator("#export-json").input_value())
        download = download_info.value
        assert set(cfg["export_contract"]["required_keys"]) <= set(payload), payload.keys()
        assert payload["preset"] == "storm"
        assert payload["zone_id"] == "kanto-safari-zone-middle"
        assert payload["colors"]["color1"] == page_overview(page)["colors"]["color1"]
        assert payload["colors"]["color2"] == page_overview(page)["colors"]["color2"]
        assert payload["colors"]["color3"] == page_overview(page)["colors"]["color3"]
        assert len(payload["sample_points"]) >= cfg["export_contract"]["minimum_sample_points"]
        assert len(payload["highlighted_species"]) >= cfg["summary_contract"]["minimum_highlight_cards"]
        assert download.suggested_filename.endswith(".json")
        downloaded_payload = json.loads(Path(download.path()).read_text(encoding="utf-8"))
        assert downloaded_payload == payload

        highlighted_species = set()
        for row in payload["highlighted_species"]:
            if isinstance(row, str):
                token = row.strip().lower()
            else:
                token = (
                    row.get("species_id")
                    or row.get("species_name")
                    or row.get("display_name", "")
                ).strip().lower()
            assert token, f"highlight row must reference a species: {row!r}"
            highlighted_species.add(token)
        assert highlighted_species <= expected_species

        assert isinstance(payload["parameters"], dict)
        assert isinstance(payload["average_level"], (int, float))
        assert isinstance(payload["average_base_stat_total"], (int, float))
        assert isinstance(payload["type_mix"], list) and payload["type_mix"], payload["type_mix"]
        for row in payload["type_mix"]:
            assert set(cfg["export_contract"]["type_mix_item_required_keys"]) <= set(row), row
            share = float(row["share"])
            assert 0 < share <= 1, row
        for point in payload["sample_points"]:
            assert set(cfg["export_contract"]["sample_point_required_keys"]) <= set(point), point
            assert isinstance(point["trail_id"], str) and point["trail_id"], point
            assert int(point["step"]) >= 0, point
            assert isinstance(point["species_name"], str) and point["species_name"], point
            assert isinstance(point["layer"], (str, int, float)) and str(point["layer"]).strip(), point
            assert 0 <= float(point["x"]) <= 1, point
            assert 0 <= float(point["y"]) <= 1, point
            assert float(point["radius"]) > 0, point
            assert float(point["weight"]) > 0, point
            assert point["species_name"] in expected_species, point
        json.dumps(payload)


def test_10_sample_points_follow_actual_trails() -> None:
    with page_session() as page:
        select_zone(page, "kanto-power-plant-area")
        click_preset(page, "storm")
        payload = click_export(page)

    groups = sample_groups(payload)
    stats = sample_stats(payload)
    assert stats["trail_count"] >= 6, stats
    assert stats["min_trail_points"] >= 4, stats
    assert stats["mean_trail_points"] >= 4, stats
    for trail_id, rows in groups.items():
        steps = [int(row["step"]) for row in rows]
        assert steps == sorted(steps), (trail_id, steps)
        assert len(set(steps)) == len(steps), (trail_id, steps)


def test_11_density_changes_trail_count_and_export_volume() -> None:
    with page_session() as page:
        select_zone(page, "seafoam-islands-b1f")
        set_seed(page, 24021)
        set_slider(page, "density-control", 0.35)
        low = click_export(page)
        set_slider(page, "density-control", 1.15)
        high = click_export(page)

    low_stats = sample_stats(low)
    high_stats = sample_stats(high)
    assert high_stats["trail_count"] >= low_stats["trail_count"] + 3, (low_stats, high_stats)
    assert high_stats["point_count"] >= low_stats["point_count"] + 12, (low_stats, high_stats)


def test_12_turbulence_changes_turning_dispersion() -> None:
    with page_session() as page:
        select_zone(page, "seafoam-islands-b1f")
        set_seed(page, 24021)
        set_slider(page, "turbulence-control", 0.08)
        low = click_export(page)
        set_slider(page, "turbulence-control", 0.95)
        high = click_export(page)

    low_stats = sample_stats(low)
    high_stats = sample_stats(high)
    assert high_stats["turn_dispersion"] > low_stats["turn_dispersion"] * 1.15, (low_stats, high_stats)


def test_13_focus_changes_centroid_compaction() -> None:
    with page_session() as page:
        select_zone(page, "viridian-forest-area")
        set_seed(page, 24021)
        set_slider(page, "focus-control", 0.22)
        low = click_export(page)
        set_slider(page, "focus-control", 0.96)
        high = click_export(page)

    low_stats = sample_stats(low)
    high_stats = sample_stats(high)
    assert high_stats["mean_distance"] < low_stats["mean_distance"] * 0.94, (low_stats, high_stats)


def test_14_contrast_changes_render_but_not_data_summary() -> None:
    with page_session() as page:
        select_zone(page, "rock-tunnel-1f")
        set_seed(page, 31007)
        set_slider(page, "contrast-control", 0.21)
        low_hash = canvas_hash(page)
        low_overview = page_overview(page)
        low_export = click_export(page)
        set_slider(page, "contrast-control", 0.98)
        high_hash = canvas_hash(page)
        high_overview = page_overview(page)
        high_export = click_export(page)

    assert low_hash != high_hash, "contrast should change the rendered result"
    assert low_overview["routeTitle"] == high_overview["routeTitle"]
    assert low_overview["metrics"] == high_overview["metrics"]
    assert low_export["type_mix"] == high_export["type_mix"]
    assert low_export["sample_points"] == high_export["sample_points"]


def test_15_type_relations_drive_analysis_surface() -> None:
    zone_id = "seafoam-islands-b1f"
    expected = expected_zone_pressure(zone_id)
    zone = expected_zone_metrics(zone_id)["zone"]
    method_tokens = {token.lower() for token in zone.get("methods", [])}
    with page_session() as page:
        select_zone(page, zone_id)
        payload = click_export(page)
        panel_state = page.evaluate(
            """
            () => ({
              pressureCards: Array.from(document.querySelectorAll('#type-pressure article, #type-pressure > div, #type-pressure > section'))
                .map((node) => (node.textContent || '').trim())
                .filter(Boolean),
              signalCards: Array.from(document.querySelectorAll('#zone-signals article, #zone-signals > div, #zone-signals > section'))
                .map((node) => (node.textContent || '').trim())
                .filter(Boolean),
              pressureText: ((document.getElementById('type-pressure') || {}).textContent || '').trim().toLowerCase(),
              signalText: ((document.getElementById('zone-signals') || {}).textContent || '').trim().toLowerCase(),
              attackCoverageText: ((document.getElementById('attack-coverage') || {}).textContent || '').trim().toLowerCase(),
              exposureProfileText: ((document.getElementById('exposure-profile') || {}).textContent || '').trim().toLowerCase(),
              typeMixBarsText: ((document.getElementById('type-mix-bars') || {}).textContent || '').trim().toLowerCase(),
            })
            """
        )
    payload_top_types = [str(row["type"]).strip().lower() for row in payload["type_mix"][:3]]
    assert payload_top_types[:2] == expected["top_types"][:2], payload["type_mix"]
    assert len(panel_state["pressureCards"]) == 3, panel_state["pressureCards"]
    assert len(panel_state["signalCards"]) >= 3, panel_state["signalCards"]
    assert sum(1 for type_name in expected["top_types"][:3] if type_name in panel_state["typeMixBarsText"]) >= 2, panel_state
    assert sum(1 for type_name in expected["coverage"] if type_name in panel_state["attackCoverageText"]) >= 1, panel_state
    assert sum(1 for type_name in expected["exposure"] if type_name in panel_state["exposureProfileText"]) >= 2, panel_state
    assert any(token in panel_state["signalText"] for token in method_tokens | {zone["biome"].lower(), "rare", "support"}), panel_state
