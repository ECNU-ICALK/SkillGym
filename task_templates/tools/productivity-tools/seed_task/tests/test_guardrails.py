from __future__ import annotations

from conftest import (
    OUTPUT_ROOT,
    baseline_bundle_listing,
    contract,
    directory_listing,
    read_digest,
    read_inventory,
    read_manifest,
    run_build,
)


def test_input_bundle_is_unchanged() -> None:
    from conftest import BUNDLE_ROOT

    assert directory_listing(BUNDLE_ROOT) == baseline_bundle_listing()


def test_output_inventory_is_restricted() -> None:
    result = run_build(clear_state=True)
    assert result.returncode == 0, result.stderr or result.stdout
    payload = contract()
    assert {path.name for path in OUTPUT_ROOT.iterdir()} == {
        payload["output_file"],
        payload["inventory_file"],
        payload["manifest_file"],
    }


def test_outputs_do_not_contain_placeholder_or_verifier_strings() -> None:
    result = run_build(clear_state=True)
    assert result.returncode == 0, result.stderr or result.stdout

    digest = read_digest().lower()
    inventory_text = read_inventory().__repr__().lower()
    manifest_text = read_manifest().__repr__().lower()

    for text in [digest, inventory_text, manifest_text]:
        assert "todo" not in text
        assert "placeholder" not in text
        assert "verifier" not in text


def test_manifest_shape_is_stable() -> None:
    result = run_build(clear_state=True)
    assert result.returncode == 0, result.stderr or result.stdout

    inventory = read_inventory()
    manifest = read_manifest()
    assert isinstance(inventory["tracked_sources"], list)
    assert isinstance(inventory["removed_blog_names"], list)
    assert isinstance(inventory["notes"], list)
    assert isinstance(manifest["delivered_article_urls"], list)
    assert isinstance(manifest["read_marked_article_urls"], list)
    assert isinstance(manifest["reopened_article_urls"], list)
    assert isinstance(manifest["tracked_source_ids"], list)
    assert isinstance(manifest["removed_blog_names"], list)
    assert isinstance(manifest["source_files"], list)
    assert isinstance(manifest["notes"], list)
