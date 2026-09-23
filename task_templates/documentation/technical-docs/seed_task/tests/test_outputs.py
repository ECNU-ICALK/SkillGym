from __future__ import annotations

import re
from pathlib import Path

from conftest import (
    OUTPUT_ROOT,
    contract,
    extract_id_assigner_start,
    extract_sizeby_priority_expectations,
    extract_timeout_update_values,
    expected_documented_api_names,
    make_alternate_bundle_copy,
    normalize,
    package_metadata,
    parse_frontmatter,
    read_manifest,
    read_page,
    run_build,
    rules,
    version_notes,
)

EQUIVALENT_MARKERS = {
    "Adds a sync or async task.": [
        "Adds a sync or async task.",
        "Adds one sync or async task",
    ],
    "Always returns a promise.": [
        "Always returns a promise.",
        "always returns a promise",
    ],
    "The task receives `{signal}` as the first argument when it runs.": [
        "The task receives `{signal}` as the first argument when it runs.",
        "passes `{signal}` to the task when it starts running",
    ],
    "Accepts an array of sync or async functions.": [
        "Accepts an array of sync or async functions.",
        "Queues an array of sync or async functions",
    ],
    "Resolves when all queued functions settle.": [
        "Resolves when all queued functions settle.",
        "Returns `Promise.all(...)` of the queued `add()` calls.",
        "returns a `Promise.all(...)` result for those tasks",
        "delegates to `Promise.all(functions.map(...))`",
    ],
    "Settles when the queue becomes empty.": [
        "Settles when the queue becomes empty.",
        "Resolves when the waiting queue becomes empty.",
    ],
    "Settles when the queue is empty and no tasks are still pending.": [
        "Settles when the queue is empty and no tasks are still pending.",
        "Resolves when the queue is empty and no tasks are still running.",
    ],
    "Counts queued tasks waiting to start.": [
        "Counts queued tasks waiting to start.",
        "Only queued tasks are counted, not already-running work.",
    ],
    "Returns the queue size filtered by matching options.": [
        "Returns the queue size filtered by matching options.",
        "Returns the number of queued tasks whose stored options match the given filter",
    ],
    "Can be used to inspect queued work for one priority level.": [
        "Can be used to inspect queued work for one priority level.",
        "such as one priority level",
    ],
    "Updates the priority of a queued task by id.": [
        "Updates the priority of a queued task by id.",
        "Updates the priority of a queued task by id before it starts.",
    ],
    "A defined concurrency limit is required for this to affect execution order.": [
        "A defined concurrency limit is required for this to affect execution order.",
        "This affects execution order only while the task is still queued.",
    ],
    "Gets or sets the concurrency limit.": [
        "Gets or sets the concurrency limit.",
        "Gets or updates the concurrency limit.",
    ],
    "Values below 1 throw a TypeError.": [
        "Values below 1 throw a TypeError.",
        "Values below `1` throw a `TypeError`",
    ],
    "Counts queued items waiting to run.": [
        "Counts queued items waiting to run.",
        "Counts queued items that are still waiting to start.",
    ],
    "Reports whether the queue is currently paused.": [
        "Reports whether the queue is currently paused.",
        "Reports whether queue execution is currently paused.",
    ],
    "Fires when a task starts running.": [
        "Fires when a task starts running.",
        "Fires each time a task starts running.",
    ],
    "Fires when a task resolves successfully.": [
        "Fires when a task resolves successfully.",
        "Fires when a task resolves without error",
    ],
    "Fires when a task rejects or throws.": [
        "Fires when a task rejects or throws.",
        "Fires when a task throws or rejects.",
    ],
    "Fires when the queue becomes empty.": [
        "Fires when the queue becomes empty.",
        "Fires each time the waiting queue becomes empty.",
    ],
    "Fires when all running work has completed.": [
        "Fires when all running work has completed.",
        "Fires each time the queue becomes empty and all running tasks have completed.",
    ],
    "Fires when work is added to the queue.": [
        "Fires when work is added to the queue.",
        "Fires whenever `add()` queues new work.",
    ],
    "Fires when the queue moves to the next slot.": [
        "Fires when the queue moves to the next slot.",
        "Fires after a task finishes and the queue advances",
    ],
}

EQUIVALENT_OPTION_SUMMARIES = {
    "Applies a per-task timeout in milliseconds.": [
        "Applies a per-task timeout in milliseconds.",
        "Applies a per-task timeout in milliseconds after the task starts running.",
    ],
    "Supplies a queue implementation with enqueue, dequeue, and size support.": [
        "Supplies a queue implementation with enqueue, dequeue, and size support.",
        "Supplies a queue implementation with `enqueue`, `dequeue`, `filter`, and `size`.",
    ],
}

EQUIVALENT_TASK_OPTION_SUMMARIES = {
    "Cancels a queued task or notifies a running task about cancellation.": [
        "Cancels a queued task or notifies a running task about cancellation.",
        "Passes an [`AbortSignal`](https://developer.mozilla.org/en-US/docs/Web/API/AbortSignal) to queued work so aborted tasks can be removed before they start and observed while they run.",
    ],
}


def page_includes_api_marker(page_text: str, api_name: str) -> bool:
    if f"`{api_name}`" in page_text:
        return True
    if "(" in api_name and f"`.{api_name}`" in page_text:
        return True
    return False


def test_formal_build_produces_required_outputs() -> None:
    result = run_build()
    assert result.returncode == 0, result.stderr or result.stdout

    payload = contract()
    output_names = {path.name for path in OUTPUT_ROOT.iterdir()}
    assert output_names == {payload["output_file"], payload["manifest_file"]}


def test_frontmatter_manifest_and_section_order_match_contract() -> None:
    result = run_build()
    assert result.returncode == 0, result.stderr or result.stdout

    payload = contract()
    package = package_metadata()
    page_text = read_page()
    frontmatter, _ = parse_frontmatter(page_text)
    manifest = read_manifest()

    assert frontmatter["title"] == payload["frontmatter"]["title"]
    assert frontmatter["nav_title"] == payload["frontmatter"]["nav_title"]
    assert frontmatter["description"] == payload["frontmatter"]["description_template"].format(version=package["version"])

    assert manifest["page_path"] == payload["output_file"]
    assert manifest["api_name"] == payload["frontmatter"]["title"]
    assert manifest["package_name"] == package["name"]
    assert manifest["package_version"] == package["version"]
    assert manifest["source_files"] == payload["source_files"]

    positions = []
    for heading in payload["required_sections"]:
        index = page_text.find(heading)
        assert index != -1, f"missing heading {heading}"
        positions.append(index)
    assert positions == sorted(positions)


def test_required_api_sections_examples_and_links_are_complete() -> None:
    result = run_build()
    assert result.returncode == 0, result.stderr or result.stdout

    payload = contract()
    page_text = read_page()
    for option in payload["queue_options"]:
        assert f"`{option['name']}`" in page_text
    for option in payload["task_options"]:
        assert f"`{option['name']}`" in page_text
    for item in payload["methods"]:
        assert page_includes_api_marker(page_text, item["name"])
    for item in payload["properties"]:
        assert f"`{item['name']}`" in page_text
    for item in payload["events"]:
        assert f"`{item['name']}`" in page_text
    for example in payload["required_examples"]:
        assert f"### {example['title']}" in page_text
        assert example["summary"] in page_text
        assert example["ts_filename"] in page_text
        assert example["js_filename"] in page_text
    for link in payload["required_links"]:
        assert link in page_text
    for entry in version_notes():
        assert entry["version"] in page_text
        assert entry["summary"] in page_text


def test_intro_follows_single_sentence_then_immediate_example_pattern() -> None:
    result = run_build()
    assert result.returncode == 0, result.stderr or result.stdout

    payload = contract()
    page_text = read_page()
    _, body = parse_frontmatter(page_text)
    top_example = next(item for item in payload["required_examples"] if item["id"] == payload["intro"]["top_example_id"])

    assert payload["intro"]["opening_sentence"] in body
    pattern = re.compile(
        re.escape(payload["intro"]["opening_sentence"])
        + r"[\s\S]*?(?P<ts>```ts [\s\S]+?```)\n\n(?P<js>```js [\s\S]+?```)\n\n## Reference"
    )
    match = pattern.search(body)
    assert match, "intro must contain the required opener and top TS/JS pair before the Reference section"

    ts_block = match.group("ts")
    js_block = match.group("js")
    assert top_example["ts_filename"] in ts_block
    assert top_example["js_filename"] in js_block
    for line in top_example["ts_code"]:
        if line:
            assert line in ts_block
    for line in top_example["js_code"]:
        if line:
            assert line in js_block


def test_behavior_notes_and_manifest_alignment_are_grounded_in_bundle() -> None:
    result = run_build()
    assert result.returncode == 0, result.stderr or result.stdout

    package = package_metadata()
    payload = contract()
    page_text = read_page()
    manifest = read_manifest()
    compact_page = normalize(page_text)

    assert "promise queue with concurrency control" in page_text.lower()
    assert "rate-limiting async or sync operations" in page_text
    assert "Node.js" in page_text
    assert "engine floor" in page_text
    assert "native ESM package" in page_text or "ESM-only" in page_text

    names = {(item["name"], item["kind"]) for item in manifest["documented_api_items"]}
    assert set(expected_documented_api_names()).issubset(names)
    assert ("timeout", "property") in names
    required_example_ids = [example["id"] for example in payload["required_examples"]]
    assert manifest["example_ids"][: len(required_example_ids)] == required_example_ids
    assert manifest["version_notes"] == version_notes()

    assert "AbortSignal" in page_text
    assert "throwOnTimeout" in page_text
    assert "intervalCap" in page_text
    assert "carryoverConcurrencyCount" in page_text


def test_source_and_test_derived_evidence_is_reported() -> None:
    result = run_build()
    assert result.returncode == 0, result.stderr or result.stdout

    page_text = read_page()
    manifest = read_manifest()

    bundle_root = Path("/environment/reference_bundle")
    if not bundle_root.exists():
        bundle_root = Path(__file__).resolve().parents[1] / "environment" / "reference_bundle"

    index_text = (bundle_root / "upstream" / "source" / "index.ts").read_text(encoding="utf-8")
    test_text = (bundle_root / "upstream" / "test" / "test.ts").read_text(encoding="utf-8")

    id_start = extract_id_assigner_start(index_text)
    priority_pairs = extract_sizeby_priority_expectations(test_text)

    assert "sizeBy(options)" in page_text
    assert "paused" in page_text

    notes_text = "\n".join(manifest["notes"])
    notes_lower = notes_text.lower()
    assert any(token in notes_text for token in ["upstream/source/index.ts", "source implementation"])
    assert any(token in notes_text for token in ["upstream/source/options.ts", "option types"])
    assert any(token in notes_text for token in ["upstream/test/test.ts", "behavior tests"])
    assert "release" in notes_lower
    assert "interval" in notes_lower
    assert "abort" in notes_lower


def test_style_rules_switcher_pairs_and_cleanup_requirements_hold() -> None:
    result = run_build()
    assert result.returncode == 0, result.stderr or result.stdout

    page_text = read_page()
    manifest_text = (OUTPUT_ROOT / contract()["manifest_file"]).read_text(encoding="utf-8")
    style_rules = rules()

    for token in style_rules["forbidden_tokens"]:
        assert token not in page_text
        assert token not in manifest_text
    for phrase in style_rules["forbidden_phrases"]:
        assert phrase not in page_text.lower()

    assert page_text.count("switcher") >= 8
    assert page_text.count("filename=\"") >= 8
    assert page_text.count("```ts ") >= 4
    assert page_text.count("```js ") >= 4
    fence_headers = [
        line
        for line in page_text.splitlines()
        if (line.startswith("```ts ") or line.startswith("```js "))
    ]
    assert len(fence_headers) >= 8
    required_example_headers = len(contract()["required_examples"]) * 2
    switcher_headers = sum("switcher" in header for header in fence_headers)
    filename_headers = sum("filename=\"" in header for header in fence_headers)
    assert switcher_headers >= required_example_headers
    assert filename_headers == len(fence_headers)
    for header in fence_headers:
        assert "filename=\"" in header
    assert style_rules["required_callout_heading"] in page_text
    assert style_rules["required_version_history_heading"] in page_text


def test_alternate_fixture_requires_rebuild_from_inputs() -> None:
    tmpdir, alt_root = make_alternate_bundle_copy()
    try:
        alt_output = Path(tmpdir.name) / "output"
        result = run_build(bundle_root=alt_root, output_root=alt_output)
        assert result.returncode == 0, result.stderr or result.stdout

        page_text = read_page(output_root=alt_output, bundle_root=alt_root)
        frontmatter, _ = parse_frontmatter(page_text)
        manifest = read_manifest(output_root=alt_output, bundle_root=alt_root)

        assert frontmatter["description"] == "API reference for the PQueue class in p-queue v8.1.1."
        assert "Cancel queued work after a controller abort" in page_text
        assert "Alternate fixture version note for the bundled release snapshot." in page_text
        assert "`priority`" in page_text
        assert "lower values" in page_text
        assert "sizeBy(options)" in page_text
        assert "paused" in page_text
        assert "Node.js" in page_text
        assert "engine floor" in page_text
        assert manifest["package_version"] == "8.1.1"
    finally:
        tmpdir.cleanup()
