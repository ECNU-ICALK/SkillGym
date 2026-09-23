from __future__ import annotations

from conftest import (
    AUTOMATION_CONTRACT_PATH,
    CLASSIFIERS_PATH,
    LICENSES_PATH,
    MANIFEST_PATH,
    original_input_hashes,
    read_manifest,
)


EXPECTED_HASHES = {
    "licenses.json": "0a21659a24f9022b2069d971856b4ac95aa8e8669cb93f1ee217aaff65d369f0",
    "trove_classifiers.py": "ee5df3bacc9f2e451ebf3419165dddbf7dcbd1e90fe7b54a2f0a7ca096745759",
}


def test_original_input_catalogs_are_unchanged() -> None:
    current = original_input_hashes()
    assert current["licenses.json"] == EXPECTED_HASHES["licenses.json"]
    assert current["trove_classifiers.py"] == EXPECTED_HASHES["trove_classifiers.py"]


def test_manifest_exists_in_expected_location() -> None:
    assert LICENSES_PATH.exists()
    assert CLASSIFIERS_PATH.exists()
    assert AUTOMATION_CONTRACT_PATH.exists()
    assert MANIFEST_PATH.exists()
    payload = read_manifest()
    assert isinstance(payload["console_entrypoint"], str)
    assert "pkgmeta" in payload["console_entrypoint"]
