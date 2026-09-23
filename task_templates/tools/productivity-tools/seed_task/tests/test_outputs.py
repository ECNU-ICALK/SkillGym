from __future__ import annotations

from conftest import (
    OUTPUT_ROOT,
    contract,
    digest_bullets,
    expected_first_run,
    expected_runs,
    make_alternate_bundle_copy,
    output_manifest,
    read_audit_events,
    read_digest,
    read_inventory,
    read_manifest,
    read_reopen_state,
    reopen_state_path,
    run_build,
    watch_db_rows,
)


def assert_digest_matches_expected(digest: str, payload: dict, expected: dict) -> None:
    for required in payload["required_shell_strings"]:
        assert required in digest
    for token in payload["cleanup_tokens"]:
        assert token not in digest.lower()
    if expected["removed_blog_names"]:
        assert "Removed legacy blogs for this run:" in digest
        for name in expected["removed_blog_names"]:
            assert f"- {name}" in digest

    high_bullets = digest_bullets(digest, "high")
    standard_bullets = digest_bullets(digest, "standard")
    assert len(high_bullets) == len(expected["grouped"]["high"])
    assert len(standard_bullets) == len(expected["grouped"]["standard"])

    for article in expected["grouped"]["high"]:
        assert any(
            article["label"] in bullet
            and article["title"] in bullet
            and article["published_at"][:10] in bullet
            and article["url"] in bullet
            for bullet in high_bullets
        )

    for article in expected["grouped"]["standard"]:
        assert any(
            article["label"] in bullet
            and article["title"] in bullet
            and article["published_at"][:10] in bullet
            and article["url"] in bullet
            for bullet in standard_bullets
        )


def assert_build_audit_matches_first_run(expected: dict, payload: dict) -> None:
    events = [event for event in read_audit_events() if event["stage"] == "build"]
    assert any(event["args"] and event["args"][0] == "scan" for event in events)
    added_labels: set[str] = set()
    for event in events:
        args = event["args"]
        if not args or args[0] != "add":
            continue
        if "--name" in args:
            name_index = args.index("--name") + 1
            if name_index < len(args):
                added_labels.add(args[name_index])
        elif len(args) > 1:
            added_labels.add(args[1])
    assert {"GitHub Changelog", "TypeScript Releases"}.issubset(added_labels)
    unread_events = [
        event
        for event in events
        if event["args"] and event["args"][0] in {"unread", "reopen-article", "mark-unread"}
    ]
    assert len(unread_events) == len(expected["reopened_urls"])
    read_events = [event for event in events if event["args"] and event["args"][0] == "read"]
    assert len(read_events) == len(expected["delivered_urls"])
    assert not any(event["args"] and event["args"][0] == "read-all" for event in events)


def test_formal_build_produces_required_outputs() -> None:
    result = run_build(clear_state=True)
    assert result.returncode == 0, result.stderr or result.stdout
    payload = contract()
    assert {path.name for path in OUTPUT_ROOT.iterdir()} == {
        payload["output_file"],
        payload["inventory_file"],
        payload["manifest_file"],
    }


def test_digest_matches_expected_unread_items_and_cleans_shell() -> None:
    result = run_build(clear_state=True)
    assert result.returncode == 0, result.stderr or result.stdout

    payload = contract()
    digest = read_digest()
    expected = expected_first_run()
    assert_digest_matches_expected(digest, payload, expected)


def test_inventory_manifest_and_watch_db_match_contract() -> None:
    result = run_build(clear_state=True)
    assert result.returncode == 0, result.stderr or result.stdout

    expected = expected_first_run()
    inventory = read_inventory()
    manifest = read_manifest()
    payload = contract()

    assert [row["label"] for row in inventory["tracked_sources"]] == payload["required_source_labels"]
    assert inventory["tracked_sources"] == expected["inventory_rows"]
    assert inventory["removed_blog_names"] == expected["removed_blog_names"]
    assert manifest["digest_path"] == payload["output_file"]
    assert sorted(manifest["delivered_article_urls"]) == sorted(expected["delivered_urls"])
    assert sorted(manifest["read_marked_article_urls"]) == sorted(expected["delivered_urls"])
    assert sorted(manifest["reopened_article_urls"]) == sorted(expected["reopened_urls"])
    assert manifest["tracked_source_ids"] == expected["tracked_source_ids"]
    assert manifest["removed_blog_names"] == expected["removed_blog_names"]
    assert manifest["source_files"] == expected["source_files"]
    assert manifest["state_db_path"] == payload["state_db_file"]
    assert manifest["reopen_state_file"] == payload["reopen_state_file"]
    assert output_manifest().name == payload["manifest_file"]
    assert reopen_state_path().name == payload["reopen_state_file"]

    blogs, articles = watch_db_rows()
    assert sorted(row["name"] for row in blogs) == sorted(payload["required_source_labels"])
    assert payload["legacy_blog_names"][0] not in {row["name"] for row in blogs}
    assert all(row["last_scanned"] for row in blogs)

    read_urls = {row["url"] for row in articles if int(row["is_read"]) == 1}
    unread_urls = {row["url"] for row in articles if int(row["is_read"]) == 0}
    assert unread_urls == set(expected["remaining_unread_urls"])
    assert set(expected["seed_read_urls"]).issubset(read_urls)
    assert set(expected["reopened_urls"]).issubset(read_urls)
    assert set(expected["delivered_urls"]).issubset(read_urls)
    reopen_state = read_reopen_state()
    assert sorted(reopen_state["applied_urls"]) == sorted(expected["reopened_urls"])
    assert_build_audit_matches_first_run(expected, payload)


def test_second_and_third_run_continue_backlog_then_emit_no_new_items() -> None:
    runs = expected_runs()
    first = run_build(clear_state=True)
    assert first.returncode == 0, first.stderr or first.stdout
    second = run_build(clear_state=False)
    assert second.returncode == 0, second.stderr or second.stdout

    payload = contract()
    second_expected = runs[1]
    digest = read_digest()
    inventory = read_inventory()
    manifest = read_manifest()
    assert_digest_matches_expected(digest, payload, second_expected)
    assert inventory["tracked_sources"] == second_expected["inventory_rows"]
    assert sorted(manifest["delivered_article_urls"]) == sorted(second_expected["delivered_urls"])
    assert sorted(manifest["read_marked_article_urls"]) == sorted(second_expected["delivered_urls"])
    assert manifest["reopened_article_urls"] == []

    _, articles = watch_db_rows()
    unread_urls = {row["url"] for row in articles if int(row["is_read"]) == 0}
    assert unread_urls == set(second_expected["remaining_unread_urls"])

    events = [event for event in read_audit_events() if event["stage"] == "build"]
    unread_events = [event for event in events if event["args"] and event["args"][0] == "unread"]
    assert unread_events == []
    assert not any(event["args"] and event["args"][0] == "read-all" for event in events)

    third = run_build(clear_state=False)
    assert third.returncode == 0, third.stderr or third.stdout
    third_expected = runs[2]
    digest = read_digest()
    inventory = read_inventory()
    manifest = read_manifest()
    assert_digest_matches_expected(digest, payload, third_expected)
    assert all(row["unread_count"] == 0 for row in inventory["tracked_sources"])
    assert manifest["delivered_article_urls"] == []
    assert manifest["read_marked_article_urls"] == []
    assert manifest["reopened_article_urls"] == []


def test_alternate_bundle_changes_digest_and_inventory_dynamically() -> None:
    tmpdir, alt_bundle, alt_workspace = make_alternate_bundle_copy()
    try:
        alt_output = alt_bundle.parent / "output"
        result = run_build(bundle_root=alt_bundle, workspace_root=alt_workspace, output_root=alt_output, clear_state=True)
        assert result.returncode == 0, result.stderr or result.stdout

        digest = read_digest(output_root=alt_output, bundle_root=alt_bundle)
        inventory = read_inventory(output_root=alt_output, bundle_root=alt_bundle)
        manifest = read_manifest(output_root=alt_output, bundle_root=alt_bundle)
        expected = expected_runs(bundle_root=alt_bundle)[0]

        assert "Node.js 26.2.0 (Current)" in digest
        assert "https://nodejs.org/en/blog/release/v26.2.0" in digest
        assert inventory["tracked_sources"] == expected["inventory_rows"]
        assert sorted(manifest["delivered_article_urls"]) == sorted(expected["delivered_urls"])
    finally:
        tmpdir.cleanup()
