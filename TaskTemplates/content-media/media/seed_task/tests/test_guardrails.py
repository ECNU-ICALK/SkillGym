from __future__ import annotations

from conftest import BASELINE_SHA_PATH, MISSION_ROOT, OUTPUT_ROOT, current_hash_lines, output_inventory, output_json, run_build


def test_input_tree_is_unchanged() -> None:
    result = run_build()
    assert result.returncode == 0, result.stderr or result.stdout
    assert current_hash_lines(MISSION_ROOT) == BASELINE_SHA_PATH.read_text(encoding="utf-8")


def test_output_inventory_is_restricted() -> None:
    result = run_build()
    assert result.returncode == 0, result.stderr or result.stdout
    assert output_inventory() == {
        "delivery_report.json",
        "frame_index.json",
        "previews/launch_001.mp4",
        "previews/launch_002.mp4",
        "previews/launch_003.mp4",
        "previews/launch_004.mp4",
        "previews/touchdown_001.mp4",
        "previews/touchdown_002.mp4",
        "previews/touchdown_003.mp4",
        "previews/touchdown_004.mp4",
        "previews/tracking_001.mp4",
        "previews/tracking_002.mp4",
        "previews/tracking_003.mp4",
        "previews/tracking_004.mp4",
        "sheets/launch_sheet.jpg",
        "sheets/touchdown_sheet.jpg",
        "sheets/tracking_sheet.jpg",
        "stills/launch_001.png",
        "stills/launch_002.png",
        "stills/launch_003.png",
        "stills/launch_004.png",
        "stills/touchdown_001.png",
        "stills/touchdown_002.png",
        "stills/touchdown_003.png",
        "stills/touchdown_004.png",
        "stills/tracking_001.png",
        "stills/tracking_002.png",
        "stills/tracking_003.png",
        "stills/tracking_004.png",
    }


def test_outputs_have_no_placeholder_or_process_residue() -> None:
    result = run_build()
    assert result.returncode == 0, result.stderr or result.stdout
    frame_index_text = (OUTPUT_ROOT / "frame_index.json").read_text(encoding="utf-8").lower()
    report_text = (OUTPUT_ROOT / "delivery_report.json").read_text(encoding="utf-8").lower()
    for token in ["todo", "tbd", "placeholder", "verifier", "runtime check"]:
        assert token not in frame_index_text
        assert token not in report_text


def test_blank_locator_requests_are_preserved() -> None:
    result = run_build()
    assert result.returncode == 0, result.stderr or result.stdout
    manifest = output_json("frame_index.json")
    blanks = []
    for clip in manifest["clips"]:
        for row in clip["requests"]:
            if row["still_locator"] == "":
                blanks.append(row["request_id"])
                assert (OUTPUT_ROOT / row["still_path"]).is_file()
    assert blanks == ["launch_001", "tracking_001", "touchdown_001"]
