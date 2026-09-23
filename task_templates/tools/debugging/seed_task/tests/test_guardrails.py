from __future__ import annotations

from pathlib import Path

from common import APP_DIR, DATA_DIR, EXPECTED_HASHES, sha256_file


def test_input_hashes_are_unchanged():
    for rel, expected in EXPECTED_HASHES.items():
        path = Path("/root") / rel
        assert path.exists(), f"missing required input file: {rel}"
        assert sha256_file(path) == expected, f"hash mismatch for {rel}"


def test_no_extra_top_level_outputs():
    output_dir = Path("/root/output")
    assert output_dir.exists()
    assert sorted(item.name for item in output_dir.iterdir() if item.is_file()) == [
        "findings.json",
        "investigation.md",
    ]


def test_no_placeholder_language():
    text = (Path("/root/output") / "investigation.md").read_text(encoding="utf-8").lower()
    banned = ["pending", "todo", "placeholder", "freeze", "不是", "真实", "冻结"]
    assert not any(token in text for token in banned)
