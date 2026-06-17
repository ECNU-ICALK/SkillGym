from __future__ import annotations

import hashlib
import time

from conftest import (
    DATA_ROOT,
    OUTPUT_ROOT,
    build_alternate_snapshot,
    load_json,
    reset_output_dir,
    run_script,
)


EXPECTED_HASHES = {
    DATA_ROOT / "flag_contract.json": "9a3d8a1c4fc5799c06f6f5269e22e617fa56832facc3aa2e785703b7f02059cf",
    DATA_ROOT / "flag_behavior_notes.json": "77e3bf3c6c634d691d060acf57880185e702f0131b356eabeede30121090e902",
    DATA_ROOT / "docs_route_snapshot.json": "e2e92443dae42be6e9e720d7bfff6e2fd40defb6a8394d7b5b1c5e03e887c6d1",
    DATA_ROOT / "fixture_matrix.json": "2c55779760a1d98a9e13d36391c5426690f460c375fc399ca640617e76e53d32",
}


def sha256_path(path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_upstream_inputs_are_unchanged() -> None:
    for path, expected in EXPECTED_HASHES.items():
        assert sha256_path(path) == expected, str(path)


def test_alternate_route_snapshot_changes_report_without_code_changes() -> None:
    reset_output_dir()
    alternate_snapshot = build_alternate_snapshot()
    run_script("collect_flag_report.sh", env={"FRAMEWORK_ROUTE_DATA_PATH": str(alternate_snapshot)})

    report = load_json(OUTPUT_ROOT / "segment_cache_report.json")
    build_preview = load_json(OUTPUT_ROOT / "build" / "docs-segment-cache" / "build-preview.json")
    scenarios = {item["scenarioId"]: item for item in report["scenarios"]}

    assert scenarios["docs-baseline"]["routeDigest"] != "116c118e7435741769eeed05dbf54e3ae77b11dd975ec88613a00011f27c480c"
    assert scenarios["docs-baseline"]["groupCount"] == 6
    assert scenarios["docs-segment-cache"]["exportMode"] == "segment-cache"
    assert scenarios["docs-segment-cache"]["groupCount"] == 3
    assert scenarios["docs-segment-cache"]["reusedSegmentCount"] == 3
    assert build_preview["mode"] == "segment-cache"
    assert build_preview["groupCount"] == 3
    assert build_preview["reusedSegmentCount"] == 3


def test_report_is_regenerated_on_each_run() -> None:
    reset_output_dir()
    start = time.time()
    run_script("collect_flag_report.sh")
    report_path = OUTPUT_ROOT / "segment_cache_report.json"
    assert report_path.exists()
    assert report_path.stat().st_mtime >= start
