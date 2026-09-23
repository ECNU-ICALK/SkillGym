from __future__ import annotations

import json
import urllib.request

from conftest import (
    EXPECTED_BASE_DIGEST,
    OUTPUT_ROOT,
    load_json,
    reset_output_dir,
    run_script,
    start_server,
    stop_process,
)


def test_dev_server_reports_enabled_runtime_mode() -> None:
    reset_output_dir()
    process = start_server()
    try:
        with urllib.request.urlopen("http://localhost:3300/api/runtime-report", timeout=5) as response:
            payload = json.load(response)
    finally:
        stop_process(process)

    assert payload["scenarioId"] == "docs-segment-cache"
    assert payload["routeDigest"] == EXPECTED_BASE_DIGEST
    assert payload["requestedSegmentCache"] is True
    assert payload["resolvedSegmentCache"] is True
    assert payload["runtimeSegmentCache"] is True
    assert payload["summary"]["mode"] == "segment-cache"
    assert payload["summary"]["groupCount"] == 4
    assert payload["summary"]["reusedSegmentCount"] == 2
    assert payload["summary"]["topGroups"][0] == {
        "key": "docs/app/api-reference/config/next-config-js",
        "size": 3,
    }


def test_build_and_export_artifacts_capture_enabled_flag() -> None:
    reset_output_dir()
    run_script("build_and_export.sh", env={"SCENARIO_ID": "docs-segment-cache"})

    runtime_flags = (OUTPUT_ROOT / "build" / "docs-segment-cache" / "runtime-flags.js").read_text(encoding="utf-8")
    assert '"segmentCache": true' in runtime_flags

    build_manifest = load_json(OUTPUT_ROOT / "build" / "docs-segment-cache" / "build-manifest.json")
    runtime_bundle_manifest = load_json(
        OUTPUT_ROOT / "build" / "docs-segment-cache" / "runtime-bundle-manifest.json"
    )
    build_preview = load_json(OUTPUT_ROOT / "build" / "docs-segment-cache" / "build-preview.json")
    runtime_define_snapshot = load_json(
        OUTPUT_ROOT / "build" / "docs-segment-cache" / "runtime-define-snapshot.json"
    )
    export_summary = load_json(OUTPUT_ROOT / "export" / "docs-segment-cache" / "segment-summary.json")

    assert build_manifest["buildFlags"]["segmentCache"] is True
    assert build_manifest["buildFlags"]["runtimeVariant"] == "segment-cache"
    assert build_manifest["routeDigest"] == EXPECTED_BASE_DIGEST
    assert build_preview == {
        "mode": "segment-cache",
        "groupCount": 4,
        "reusedSegmentCount": 2,
        "groupKeys": [
            "docs/app/api-reference/config/next-config-js",
            "docs/app/api-reference/directives/use-cache",
            "docs/app/building-your-application/rendering/partial-prerendering",
            "docs/app/getting-started",
        ],
        "topGroups": [
            {"key": "docs/app/api-reference/config/next-config-js", "size": 3},
            {"key": "docs/app/api-reference/directives/use-cache", "size": 1},
            {"key": "docs/app/building-your-application/rendering/partial-prerendering", "size": 1},
            {"key": "docs/app/getting-started", "size": 1},
        ],
    }
    assert runtime_bundle_manifest == {
        "selected": {
            "bundleType": "app",
            "bundleId": "app-segment-cache",
            "runtimeVariant": "segment-cache",
        },
        "availableAppBundles": [
            {"bundleId": "app-baseline", "runtimeVariant": "baseline"},
            {"bundleId": "app-segment-cache", "runtimeVariant": "segment-cache"},
        ],
        "selectedBundleAvailable": True,
    }
    assert runtime_define_snapshot == {
        "app": {
            "__FRAMEWORK_SEGMENT_CACHE__": "true",
            "__FRAMEWORK_RUNTIME_VARIANT__": "segment-cache",
            "__FRAMEWORK_APP_BUNDLE_ID__": "app-segment-cache",
        },
        "server": {
            "__FRAMEWORK_SEGMENT_CACHE__": "true",
        },
    }
    assert export_summary == {
        "scenarioId": "docs-segment-cache",
        "requestedSegmentCache": True,
        "resolvedSegmentCache": True,
        "exportMode": "segment-cache",
        "routeDigest": EXPECTED_BASE_DIGEST,
        "groupCount": 4,
        "reusedSegmentCount": 2,
    }


def test_final_report_covers_both_scenarios() -> None:
    reset_output_dir()
    run_script("collect_flag_report.sh")

    report = load_json(OUTPUT_ROOT / "segment_cache_report.json")
    assert sorted(item["scenarioId"] for item in report["scenarios"]) == [
        "docs-baseline",
        "docs-segment-cache",
    ]

    scenarios = {item["scenarioId"]: item for item in report["scenarios"]}

    assert scenarios["docs-baseline"] == {
        "scenarioId": "docs-baseline",
        "requestedSegmentCache": False,
        "resolvedSegmentCache": False,
        "buildSegmentCache": False,
        "exportMode": "baseline",
        "routeDigest": EXPECTED_BASE_DIGEST,
        "groupCount": 6,
        "reusedSegmentCount": 0,
    }
    assert scenarios["docs-segment-cache"] == {
        "scenarioId": "docs-segment-cache",
        "requestedSegmentCache": True,
        "resolvedSegmentCache": True,
        "buildSegmentCache": True,
        "exportMode": "segment-cache",
        "routeDigest": EXPECTED_BASE_DIGEST,
        "groupCount": 4,
        "reusedSegmentCount": 2,
    }
