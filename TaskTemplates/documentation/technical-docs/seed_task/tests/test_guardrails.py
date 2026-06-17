from __future__ import annotations

from conftest import (
    OUTPUT_ROOT,
    baseline_reference_listing,
    contract,
    directory_listing,
    read_manifest,
    read_page,
    run_build,
)


def test_input_bundle_is_unchanged() -> None:
    from conftest import BUNDLE_ROOT

    assert directory_listing(BUNDLE_ROOT) == baseline_reference_listing()


def test_output_inventory_is_restricted() -> None:
    result = run_build()
    assert result.returncode == 0, result.stderr or result.stdout
    payload = contract()
    assert {path.name for path in OUTPUT_ROOT.iterdir()} == {payload["output_file"], payload["manifest_file"]}


def test_outputs_do_not_contain_placeholder_or_verifier_strings() -> None:
    result = run_build()
    assert result.returncode == 0, result.stderr or result.stdout

    page_text = read_page().lower()
    manifest_text = (OUTPUT_ROOT / contract()["manifest_file"]).read_text(encoding="utf-8").lower()
    for text in (page_text, manifest_text):
        assert "placeholder" not in text
        assert "verifier" not in text
        assert "todo" not in text
        assert "tbd" not in text
        assert "draft marker" not in text


def test_manifest_shape_is_stable() -> None:
    result = run_build()
    assert result.returncode == 0, result.stderr or result.stdout

    manifest = read_manifest()
    assert isinstance(manifest["documented_api_items"], list)
    assert isinstance(manifest["example_ids"], list)
    assert isinstance(manifest["version_notes"], list)
    assert isinstance(manifest["notes"], list)
