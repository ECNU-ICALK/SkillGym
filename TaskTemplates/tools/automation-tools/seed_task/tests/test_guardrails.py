from __future__ import annotations

import json
import re
from pathlib import Path

from common import BUNDLE_ROOT, OUTPUT_ROOT, sha256_tree, run_build


REFERENCE_HASH = sha256_tree(BUNDLE_ROOT)


def test_reference_bundle_was_not_modified() -> None:
    assert sha256_tree(BUNDLE_ROOT) == REFERENCE_HASH


def test_output_directory_contains_only_contract_files() -> None:
    result = run_build(BUNDLE_ROOT, OUTPUT_ROOT)
    assert result.returncode == 0, result.stderr or result.stdout
    names = sorted(path.name for path in OUTPUT_ROOT.iterdir())
    assert names == ["index.md", "latest.md", "preview.md", "release_manifest.json"]


def test_outputs_do_not_contain_placeholder_or_test_residue() -> None:
    result = run_build(BUNDLE_ROOT, OUTPUT_ROOT)
    assert result.returncode == 0, result.stderr or result.stdout
    banned_patterns = [
        r"\bTODO[:\]]",
        r"placeholder",
        r"verifier",
        r"/tests",
    ]
    for path in OUTPUT_ROOT.iterdir():
        text = path.read_text(encoding="utf-8")
        for pattern in banned_patterns:
            assert re.search(pattern, text, flags=re.IGNORECASE) is None, f"{path.name} contains banned marker {pattern}"


def test_manifest_is_valid_json_object() -> None:
    result = run_build(BUNDLE_ROOT, OUTPUT_ROOT)
    assert result.returncode == 0, result.stderr or result.stdout
    payload = json.loads((OUTPUT_ROOT / "release_manifest.json").read_text(encoding="utf-8"))
    assert isinstance(payload, dict)
