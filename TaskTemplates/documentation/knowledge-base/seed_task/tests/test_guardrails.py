from __future__ import annotations

from conftest import (
    OUTPUT_ROOT,
    baseline_bundle_listing,
    contract,
    directory_listing,
    output_manifest,
    read_manifest,
    read_page,
    read_report,
    run_build,
)


def test_input_bundle_is_unchanged() -> None:
    from conftest import BUNDLE_ROOT

    assert directory_listing(BUNDLE_ROOT) == baseline_bundle_listing()


def test_output_inventory_is_restricted() -> None:
    result = run_build()
    assert result.returncode == 0, result.stderr or result.stdout
    payload = contract()
    assert {path.name for path in OUTPUT_ROOT.iterdir()} == {
        payload["output_file"],
        payload["audit_report_file"],
        payload["manifest_file"],
    }


def test_outputs_do_not_contain_placeholder_or_verifier_strings() -> None:
    result = run_build()
    assert result.returncode == 0, result.stderr or result.stdout

    page_text = read_page().lower()
    manifest_text = output_manifest().read_text(encoding="utf-8").lower()
    report_text = read_report().lower()
    assert "placeholder" not in page_text
    for text in [page_text, manifest_text]:
        assert "verifier" not in text
        assert "todo" not in text
        assert "tbd" not in text
    assert "verifier" not in report_text


def test_manifest_shape_is_stable() -> None:
    result = run_build()
    assert result.returncode == 0, result.stderr or result.stdout

    manifest = read_manifest()
    assert isinstance(manifest["selected_resources"], list)
    assert isinstance(manifest["section_counts"], dict)
    assert isinstance(manifest["notes"], list)
