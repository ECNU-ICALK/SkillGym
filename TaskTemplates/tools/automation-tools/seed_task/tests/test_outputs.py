from __future__ import annotations

import re

from common import (
    CONTRACT,
    BUNDLE_ROOT,
    make_bundle_copy,
    read_manifest,
    read_output,
    release_channel,
    release_kind,
    release_payload,
    run_build,
    top_announcement_header,
    processed_items,
    extract_full_changelog,
    long_date,
)


def assert_required_outputs(output_root) -> None:
    names = sorted(path.name for path in output_root.iterdir())
    assert names == sorted(CONTRACT["required_output_files"]), names


def assert_manifest_core(manifest: dict, payload: dict[str, str]) -> None:
    for field in CONTRACT["required_manifest_fields"]:
        assert field in manifest, f"missing manifest field {field}"
    assert manifest["version"] == payload["version"]
    assert manifest["release_channel"] == release_channel(payload["version"])
    assert manifest["release_kind"] == release_kind(payload["version"])
    assert manifest["release_date_long"] == long_date(payload["released_at"])
    assert manifest["full_changelog_url"] == extract_full_changelog(payload["body"])


def assert_highlight_shape(page_text: str, expected_min: int) -> None:
    section = page_text.split("## Highlights", 1)[1].split("## What's Changed", 1)[0]
    bullets = [line for line in section.splitlines() if line.startswith("- **")]
    assert len(bullets) >= expected_min, bullets
    for bullet in bullets:
        assert "](" not in bullet, bullet
        assert " by @" not in bullet, bullet


def test_visible_fixture_outputs_match_stable_minor_contract() -> None:
    bundle_root, output_root = make_bundle_copy()
    result = run_build(bundle_root, output_root)
    assert result.returncode == 0, result.stderr or result.stdout

    payload = release_payload(bundle_root)
    latest = read_output(output_root, "latest.md")
    preview = read_output(output_root, "preview.md")
    index = read_output(output_root, "index.md")
    manifest = read_manifest(output_root)

    assert_required_outputs(output_root)
    assert_manifest_core(manifest, payload)
    assert manifest["updated_files"] == ["index.md", "latest.md"]
    assert latest.startswith(f"# Latest stable release: {payload['version']}")
    assert f"Released: {long_date(payload['released_at'])}" in latest
    assert "## Highlights" in latest and "## What's Changed" in latest
    assert_highlight_shape(latest, 3)
    assert extract_full_changelog(payload["body"]) in latest
    assert preview == (bundle_root / "workspace/docs/changelogs/preview.md").read_text(encoding="utf-8")
    assert index.startswith("# Gemini CLI release notes")
    assert top_announcement_header(payload["version"], payload["released_at"]) in index
    assert re.search(r"\[#\d+\]\(https://github.com/google-gemini/gemini-cli/pull/\d+\)", index), index


def test_preview_minor_fixture_updates_only_preview_page() -> None:
    bundle_root, output_root = make_bundle_copy("preview_minor")
    result = run_build(bundle_root, output_root)
    assert result.returncode == 0, result.stderr or result.stdout

    payload = release_payload(bundle_root)
    preview = read_output(output_root, "preview.md")
    latest = read_output(output_root, "latest.md")
    index = read_output(output_root, "index.md")
    manifest = read_manifest(output_root)

    assert_manifest_core(manifest, payload)
    assert manifest["updated_files"] == ["preview.md"]
    assert preview.startswith(f"# Preview release: {payload['version']}")
    assert f"Released: {long_date(payload['released_at'])}" in preview
    assert_highlight_shape(preview, 3)
    assert latest == (bundle_root / "workspace/docs/changelogs/latest.md").read_text(encoding="utf-8")
    assert index == (bundle_root / "workspace/docs/changelogs/index.md").read_text(encoding="utf-8")


def test_stable_patch_fixture_prepends_items_and_keeps_other_pages() -> None:
    bundle_root, output_root = make_bundle_copy("stable_patch")
    result = run_build(bundle_root, output_root)
    assert result.returncode == 0, result.stderr or result.stdout

    payload = release_payload(bundle_root)
    latest = read_output(output_root, "latest.md")
    preview = read_output(output_root, "preview.md")
    index = read_output(output_root, "index.md")
    manifest = read_manifest(output_root)

    assert_manifest_core(manifest, payload)
    assert manifest["updated_files"] == ["latest.md"]
    assert latest.startswith(f"# Latest stable release: {payload['version']}")
    assert f"Released: {long_date(payload['released_at'])}" in latest
    assert "fix(patch): cherry-pick" in latest
    assert "## What's Changed" in latest
    assert "**Full Changelog**:" in latest
    assert preview == (bundle_root / "workspace/docs/changelogs/preview.md").read_text(encoding="utf-8")
    assert index == (bundle_root / "workspace/docs/changelogs/index.md").read_text(encoding="utf-8")


def test_preview_patch_fixture_prepends_items_and_keeps_other_pages() -> None:
    bundle_root, output_root = make_bundle_copy("preview_patch")
    result = run_build(bundle_root, output_root)
    assert result.returncode == 0, result.stderr or result.stdout

    payload = release_payload(bundle_root)
    preview = read_output(output_root, "preview.md")
    latest = read_output(output_root, "latest.md")
    index = read_output(output_root, "index.md")
    manifest = read_manifest(output_root)

    assert_manifest_core(manifest, payload)
    assert manifest["updated_files"] == ["preview.md"]
    assert preview.startswith(f"# Preview release: {payload['version']}")
    assert f"Released: {long_date(payload['released_at'])}" in preview
    assert "fix(patch): cherry-pick" in preview
    assert "## What's Changed" in preview
    assert "**Full Changelog**:" in preview
    assert latest == (bundle_root / "workspace/docs/changelogs/latest.md").read_text(encoding="utf-8")
    assert index == (bundle_root / "workspace/docs/changelogs/index.md").read_text(encoding="utf-8")
