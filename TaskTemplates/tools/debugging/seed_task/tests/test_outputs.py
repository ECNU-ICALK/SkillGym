from __future__ import annotations

from pathlib import Path

from common import (
    ARTIFACTS_DIR,
    OUTPUT_DIR,
    cpuprofile_duration_ms,
    cpuprofile_timeline,
    differential_hotspots_ms,
    expected_activity_regions,
    expected_stack_examples,
    load_output_json,
    load_output_markdown,
    markdown_sections,
    trace_duration_ms,
    trace_event_duration,
    trace_has_signal,
)


def test_output_files_and_schema():
    assert OUTPUT_DIR.exists(), "output directory is missing"
    assert sorted(p.name for p in OUTPUT_DIR.iterdir() if p.is_file()) == [
        "findings.json",
        "investigation.md",
    ]

    payload = load_output_json()
    assert payload["incident_id"] == "route-explorer-latency"
    assert isinstance(payload["reference_path"], str) and payload["reference_path"].strip()
    assert isinstance(payload["affected_path"], str) and payload["affected_path"].strip()
    assert len(payload["top_findings"]) == 3
    assert set(payload["timeline_summary"]) == {
        "reference_profile_duration_ms",
        "affected_profile_duration_ms",
        "user_ready_duration_ms",
        "profile_gap_ms",
    }
    assert len(payload["activity_regions"]) == 3
    assert len(payload["stack_examples"]) == 2


def test_timeline_summary_matches_captures():
    payload = load_output_json()
    summary = payload["timeline_summary"]
    reference = cpuprofile_duration_ms(ARTIFACTS_DIR / "profiles" / "overview.cpuprofile")
    affected_profile = cpuprofile_duration_ms(ARTIFACTS_DIR / "profiles" / "route-explorer.cpuprofile")
    affected_trace = trace_duration_ms()
    assert abs(summary["reference_profile_duration_ms"] - reference) < 0.01
    assert abs(summary["affected_profile_duration_ms"] - affected_profile) < 0.01
    assert abs(summary["user_ready_duration_ms"] - affected_trace) < 0.01
    assert abs(summary["profile_gap_ms"] - (affected_profile - reference)) < 0.01


def test_activity_regions_match_sampled_timeline():
    payload = load_output_json()
    expected = expected_activity_regions()
    actual = payload["activity_regions"]
    assert [item["phase"] for item in actual] == [item["phase"] for item in expected]
    for want, got in zip(expected, actual):
        assert abs(got["start_ms"] - want["start_ms"]) <= 1.0
        assert abs(got["end_ms"] - want["end_ms"]) <= 1.0
        assert got["dominant_leaf_frames"] == want["dominant_leaf_frames"]

    timeline = cpuprofile_timeline(ARTIFACTS_DIR / "profiles" / "route-explorer.cpuprofile")
    functions = [row["function"] for row in timeline]
    for region in expected:
        start = region["start_ms"]
        end = region["end_ms"]
        region_rows = [row for row in timeline if start <= row["offset_ms"] <= end]
        assert region_rows
        for fn in region["dominant_leaf_frames"]:
            assert fn in [row["function"] for row in region_rows]


def test_stack_examples_match_profile_tree():
    payload = load_output_json()
    actual = payload["stack_examples"]
    expected = expected_stack_examples()
    assert [item["label"] for item in actual] == [item["label"] for item in expected]
    route_stack = actual[0]["frames_leaf_to_root"]
    render_stack = actual[1]["frames_leaf_to_root"]

    assert route_stack[0] in {
        "groupFlightsByAirport",
        "computeConnectionMatrix",
        "buildDelayHeatmap",
    }
    assert route_stack[1:] == ["renderRouteExplorer", "bootstrapDashboard", "(root)"]

    assert render_stack[0] in {"renderRouteCards", "PaintRouteCards"}
    assert render_stack[1:] == ["renderRouteExplorer", "bootstrapDashboard", "(root)"]


def test_findings_identify_differential_hotspots():
    payload = load_output_json()
    findings = payload["top_findings"]
    markdown = load_output_markdown()
    combined = str(payload) + "\n" + markdown
    categories = {finding["category"] for finding in findings}
    assert categories == {"data-processing", "rendering", "gc"}
    for finding in findings:
        assert finding["confidence"] in {"high", "medium", "low"}
        assert 1 <= len(finding["signals"]) <= 5
        assert all(isinstance(item, str) and item.strip() for item in finding["evidence_files"])
    assert "groupFlightsByAirport" in combined
    assert "buildDelayHeatmap" in combined
    assert "renderRouteCards" in combined
    assert "UpdateLayoutTree" in combined or "Paint" in combined
    assert "RunTask" in combined or "MinorGC" in combined or "(garbage collector)" in combined
    assert "2025" in combined
    assert "2175" in combined
    assert "1265" in combined
    assert "shared baseline" in combined.lower() or "shared load" in combined.lower() or "shared setup" in combined.lower()
    assert "route-only-compute" in combined
    assert "render-gc-tail" in combined
    assert "groupFlightsByAirport" in combined and "renderRouteExplorer" in combined and "bootstrapDashboard" in combined
    assert any(name == "groupFlightsByAirport" for name, _ in differential_hotspots_ms())
    assert any(name == "buildDelayHeatmap" for name, _ in differential_hotspots_ms())
    assert any(name == "renderRouteCards" for name, _ in differential_hotspots_ms())


def test_markdown_matches_json():
    payload = load_output_json()
    md = load_output_markdown()
    sections = markdown_sections(md)

    assert "# Route Explorer Performance Investigation" in sections
    assert "## Comparison" in sections
    assert "## Findings" in sections
    assert "## Recommended Follow-up" in sections
    assert "Path" in sections["## Comparison"] and "Approx Duration (ms)" in sections["## Comparison"]
    assert "2025" in md
    assert "2175" in md
    assert "shared-setup" in md or "shared setup" in md.lower()
    assert "route-only-compute" in md
    assert "render-gc-tail" in md
    assert "renderRouteExplorer" in md
    assert "bootstrapDashboard" in md
    assert "(root)" in md

    for finding in payload["top_findings"]:
        assert finding["title"] in md
        for signal in finding["signals"]:
            assert signal in md or signal in str(payload)

    assert "overview.cpuprofile" in md
    assert "route-explorer.cpuprofile" in md
    assert "Trace-route-explorer.json" in md


def test_trace_supports_rendering_and_task_claims():
    assert trace_has_signal("groupFlightsByAirport")
    assert trace_has_signal("buildDelayHeatmap")
    assert trace_has_signal("renderRouteCards")
    assert trace_event_duration("FunctionCall") > 0
    assert trace_event_duration("UpdateLayoutTree") > 0
    assert trace_event_duration("Paint") > 0
