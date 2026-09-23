#!/usr/bin/env python3
from __future__ import annotations

import argparse
import html
import json
import re
from pathlib import Path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build the bundled PQueue API reference page.")
    parser.add_argument("--bundle-root", default="/environment/reference_bundle")
    parser.add_argument("--workspace-root", default="/environment/workspace")
    parser.add_argument("--output-root", default="/environment/output")
    return parser.parse_args()


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def load_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def render_code_block(language: str, filename: str, lines: list[str], highlight: int) -> str:
    body = "\n".join(lines)
    return f"```{language} filename=\"{filename}\" switcher highlight={{{highlight}}}\n{body}\n```"


def render_table(headers: list[str], rows: list[list[str]]) -> str:
    lines = [
        "| " + " | ".join(headers) + " |",
        "| " + " | ".join(["---"] * len(headers)) + " |",
    ]
    for row in rows:
        lines.append("| " + " | ".join(row) + " |")
    return "\n".join(lines)


def release_highlight(release_html: str) -> str:
    for match in re.findall(r"<li>(.*?)</li>", release_html, flags=re.DOTALL):
        if "intervalCount" not in match:
            continue
        text = re.sub(r"<[^>]+>", "", match)
        text = html.unescape(" ".join(text.split()))
        if text:
            return text
    raise ValueError("missing release highlight")


def id_assigner_start(source_index: str) -> str:
    match = re.search(r"#idAssigner\s*=\s*(\d+)n;", source_index)
    if not match:
        raise ValueError("missing #idAssigner")
    return f"{match.group(1)}n"


def timeout_update_values(test_text: str) -> tuple[str, str]:
    block = re.search(
        r"test\('\.add\(\) - change timeout in between'.*?\n\}\);",
        test_text,
        flags=re.DOTALL,
    )
    if not block:
        raise ValueError("missing timeout update test block")
    initial = re.search(r"initialTimeout = (\d+);", block.group(0))
    updated = re.search(r"newTimeout = (\d+);", block.group(0))
    if not initial or not updated:
        raise ValueError("missing timeout update values")
    return initial.group(1), updated.group(1)


def size_by_expectations(test_text: str) -> list[tuple[str, str]]:
    block = re.search(
        r"test\('\.sizeBy\(\) - priority'.*?\n\}\);",
        test_text,
        flags=re.DOTALL,
    )
    if not block:
        raise ValueError("missing sizeBy test block")
    pairs = re.findall(r"sizeBy\(\{priority: ([^}]+)\}\), (\d+)", block.group(0))
    if not pairs:
        raise ValueError("missing sizeBy expectations")
    return pairs


def queue_option_description(name: str) -> str:
    descriptions = {
        "concurrency": "Limits how many tasks run at the same time. Values below `1` throw `TypeError` at construction time and when you update `queue.concurrency`.",
        "timeout": "Applies a per-task timeout in milliseconds. The queue instance also exposes `timeout` as the default used for future `add()` calls.",
        "throwOnTimeout": "Controls whether a timeout rejects instead of resolving with no value.",
        "autoStart": "Starts queued work as soon as capacity is available.",
        "queueClass": "Supplies a queue implementation with enqueue, dequeue, and size support. See [Custom queueClass](#custom-queueclass).",
        "intervalCap": "Limits how many runs can start during one interval window.",
        "interval": "Defines the interval window in milliseconds.",
        "carryoverConcurrencyCount": "Counts pending tasks against the next interval window when enabled.",
    }
    return descriptions[name]


def task_option_description(name: str, abort_signal_url: str, id_start: str) -> str:
    descriptions = {
        "priority": "Higher values are scheduled before lower values while work is still queued.",
        "id": f"Identifies a queued task so its priority can be updated before execution. Auto-assigned ids start at `{id_start}` in the bundled source.",
        "signal": f"Cancels a queued task or notifies a running task about cancellation. Use [`AbortSignal`]({abort_signal_url}) when you need cancellation to reach queued work and running work.",
        "timeout": "Overrides the queue-level timeout for one task.",
        "throwOnTimeout": "Overrides timeout rejection behavior for one task.",
    }
    return descriptions[name]


def method_rows() -> list[list[str]]:
    return [
        ["`add(fn, options?)`", "`Promise<TResult | void>`", "Adds a sync or async task. Always returns a promise. The task receives `{signal}` as the first argument when it runs."],
        ["`addAll(functions, options?)`", "`Promise<Array<TResult | void>>`", "Accepts an array of sync or async functions. Resolves when all queued functions settle."],
        ["`start()`", "`this`", "Starts or resumes queued work. Returns the queue instance."],
        ["`pause()`", "`void`", "Puts queue execution on hold."],
        ["`clear()`", "`void`", "Clears queued work that has not started yet."],
        ["`onEmpty()`", "`Promise<void>`", "Settles when the queue becomes empty."],
        ["`onIdle()`", "`Promise<void>`", "Settles when the queue is empty and no tasks are still pending."],
        ["`onSizeLessThan(limit)`", "`Promise<void>`", "Waits until `queue.size < limit`. Counts queued tasks waiting to start."],
        ["`sizeBy(options)`", "`number`", "Returns the queue size filtered by matching options. Can be used to inspect queued work for one priority level."],
        ["`setPriority(id, priority)`", "`void`", "Updates the priority of a queued task by id. A defined concurrency limit is required for this to affect execution order."],
    ]


def property_rows() -> list[list[str]]:
    return [
        ["`concurrency`", "`number`", "get/set", "Gets or sets the concurrency limit. Values below `1` throw a `TypeError`."],
        ["`timeout`", "`number | undefined`", "get/set", "Stores the default timeout in milliseconds for future tasks."],
        ["`size`", "`number`", "readonly", "Counts queued items waiting to run."],
        ["`pending`", "`number`", "readonly", "Counts running items that are no longer in the queue."],
        ["`isPaused`", "`boolean`", "readonly", "Reports whether the queue is currently paused."],
    ]


def event_rows() -> list[list[str]]:
    return [
        ["`active`", "None", "Fires when a task starts running."],
        ["`completed`", "`result`", "Fires when a task resolves successfully."],
        ["`error`", "`error`", "Fires when a task rejects or throws."],
        ["`empty`", "None", "Fires when the queue becomes empty."],
        ["`idle`", "None", "Fires when all running work has completed."],
        ["`add`", "None", "Fires when work is added to the queue."],
        ["`next`", "None", "Fires when the queue moves to the next slot."],
    ]


def documented_api_items(contract: dict) -> list[dict[str, object]]:
    items: list[dict[str, object]] = [
        {
            "name": contract["constructor"]["signature"],
            "kind": "constructor",
            "required_sections": ["Constructor"],
        }
    ]
    for option in contract["queue_options"]:
        items.append(
            {
                "name": option["name"],
                "kind": "option",
                "required_sections": ["Queue options"],
            }
        )
    for option in contract["task_options"]:
        items.append(
            {
                "name": option["name"],
                "kind": "option",
                "required_sections": ["Task options"],
            }
        )
    for item in contract["methods"]:
        items.append(
            {
                "name": item["name"],
                "kind": item["kind"],
                "required_sections": item["required_sections"],
            }
        )
    for item in contract["properties"]:
        items.append(
            {
                "name": item["name"],
                "kind": item["kind"],
                "required_sections": item["required_sections"],
            }
        )
    for item in contract["events"]:
        items.append(
            {
                "name": item["name"],
                "kind": item["kind"],
                "required_sections": item["required_sections"],
            }
        )
    return items


def highlight_for_lines(lines: list[str]) -> int:
    for index, line in enumerate(lines, start=1):
        if "new PQueue(" in line or ".setPriority(" in line or "controller.abort()" in line or "throwOnTimeout" in line:
            return index
    return 1


def render_examples(examples: list[dict]) -> list[str]:
    sections: list[str] = []
    for example in examples:
        sections.extend(
            [
                f"### {example['title']}",
                "",
                example["summary"],
                "",
                render_code_block(
                    "ts",
                    example["ts_filename"],
                    example["ts_code"],
                    highlight_for_lines(example["ts_code"]),
                ),
                "",
                render_code_block(
                    "js",
                    example["js_filename"],
                    example["js_code"],
                    highlight_for_lines(example["js_code"]),
                ),
                "",
            ]
        )
    return sections


def build_page(bundle_root: Path, workspace_root: Path, output_root: Path) -> tuple[str, dict]:
    del output_root
    contract = load_json(bundle_root / "contracts" / "page_contract.json")
    rules = load_json(bundle_root / "contracts" / "reference_rules.json")
    version_notes = load_json(bundle_root / "contracts" / "version_notes.json")["entries"]
    package = load_json(bundle_root / "upstream" / "package.json")
    source_index = load_text(bundle_root / "upstream" / "source" / "index.ts")
    source_tests = load_text(bundle_root / "upstream" / "test" / "test.ts")
    release_filename = Path(contract["source_files"][-1]).name
    release_html = load_text(bundle_root / "upstream" / release_filename)

    id_start = id_assigner_start(source_index)
    initial_timeout, updated_timeout = timeout_update_values(source_tests)
    priority_pairs = size_by_expectations(source_tests)
    release_note = release_highlight(release_html)
    top_example = next(
        example
        for example in contract["required_examples"]
        if example["id"] == contract["intro"]["top_example_id"]
    )

    queue_rows: list[list[str]] = []
    for option in contract["queue_options"]:
        queue_rows.append(
            [
                f"`{option['name']}`",
                f"`{option['type']}`",
                f"`{option['default']}`" if option["default"] else "",
                f"`{option['minimum']}`" if option["minimum"] else "",
                queue_option_description(option["name"]),
            ]
        )

    task_rows: list[list[str]] = []
    for option in contract["task_options"]:
        task_rows.append(
            [
                f"`{option['name']}`",
                f"`{option['type']}`",
                f"`{option['default']}`" if option["default"] else "",
                task_option_description(option["name"], contract["required_links"][0], id_start),
            ]
        )

    size_by_note_lines = [
        f"In the bundled tests, `sizeBy({{priority: {priority}}})` returns `{count}` while the queue stays paused."
        for priority, count in priority_pairs[:2]
    ]

    lines = [
        "---",
        f"title: {contract['frontmatter']['title']}",
        f"description: {contract['frontmatter']['description_template'].format(version=package['version'])}",
        f"nav_title: {contract['frontmatter']['nav_title']}",
        "---",
        "",
        contract["intro"]["opening_sentence"],
        "",
        render_code_block(
            "ts",
            top_example["ts_filename"],
            top_example["ts_code"],
            highlight_for_lines(top_example["ts_code"]),
        ),
        "",
        render_code_block(
            "js",
            top_example["js_filename"],
            top_example["js_code"],
            highlight_for_lines(top_example["js_code"]),
        ),
        "",
        "## Reference",
        "",
        "### Constructor",
        "",
        f"`{contract['constructor']['signature']}`",
        "",
        contract["constructor"]["summary"],
        "",
        "#### Custom queueClass",
        "",
        "Use `queueClass` to swap the scheduling policy behind `PQueue`. The bundled release documents a queue implementation with `enqueue`, `dequeue`, and a `size` getter. If you plan to call `sizeBy()` or `setPriority()`, make sure the supplied implementation also supports the filtering and reprioritization behavior those methods rely on.",
        "",
        "### Queue options",
        "",
        render_table(["Option", "Type", "Default", "Minimum", "Description"], queue_rows),
        "",
        "The `concurrency` and `intervalCap` options are separate limits. `concurrency` bounds how many tasks can run at once, while `intervalCap` bounds how many tasks can start within one `interval` window.",
        "",
        "### Task options",
        "",
        render_table(["Option", "Type", "Default", "Description"], task_rows),
        "",
        "Task functions passed to `add()` receive `{signal}` when they start. That allows the queued work to react to cancellation inside the task body.",
        "",
        f"The bundled timeout update test moves `queue.timeout` from `{initial_timeout}` to `{updated_timeout}` before the second task starts, so future tasks pick up the later default.",
        "",
        f"If a queued task is aborted before it starts, `queue.add()` rejects and the aborted job does not consume interval capacity in this bundled release. The release page highlights the same behavior: {release_note}.",
        "",
        "### Methods",
        "",
        render_table(["Method", "Returns", "Description"], method_rows()),
        "",
        "#### `sizeBy(options)`",
        "",
        "Returns the queue size filtered by matching options. You can use it to inspect queued work for one priority level before the queue resumes processing.",
        "",
        *[line for note in size_by_note_lines for line in (note, "")],
        "#### `setPriority(id, priority)`",
        "",
        "Updates the priority of a queued task by id before it runs. A defined concurrency limit is required for this to affect execution order.",
        "",
        "### Properties",
        "",
        render_table(["Property", "Type", "Access", "Description"], property_rows()),
        "",
        "Changing `queue.concurrency` reprocesses the queue immediately with the new limit. Changing `queue.timeout` updates only the default for future tasks.",
        "",
        "### Events",
        "",
        render_table(["Event", "Payload", "Description"], event_rows()),
        "",
        "Events are emitted from the queue instance itself. `empty` fires when nothing is left waiting in the queue, while `idle` waits for both the queue and the running set to drain.",
        "",
        "## Good to know",
        "",
        "- Greater `priority` values schedule before lower values while work is still queued.",
        "- Queue-level `timeout` can be overridden per `add()` call.",
        "- `onEmpty()` only tracks queued items, while `onIdle()` also waits for running tasks.",
        "- `carryoverConcurrencyCount` controls whether pending work counts against the next `intervalCap` window.",
        f"- Package metadata declares this release line as ESM-only with a Node.js engine floor of `{package['engines']['node']}`.",
        f"- Auto-assigned ids start at `{id_start}` in the bundled source.",
        f"- Bundled release note: {release_note}.",
        "",
        "## Examples",
        "",
        *render_examples(contract["required_examples"]),
        "## Version History",
        "",
        "| Version | Changes |",
        "| --- | --- |",
    ]
    for entry in version_notes:
        lines.append(f"| {entry['version']} | {entry['summary']} |")
    lines.append("")

    page = "\n".join(lines)
    for token in rules["forbidden_tokens"]:
        if token in page:
            raise ValueError(f"forbidden token in page: {token}")
    for phrase in rules["forbidden_phrases"]:
        if phrase in page.lower():
            raise ValueError(f"forbidden phrase in page: {phrase}")

    manifest = {
        "page_path": contract["output_file"],
        "api_name": contract["frontmatter"]["title"],
        "package_name": package["name"],
        "package_version": package["version"],
        "source_files": contract["source_files"],
        "documented_api_items": documented_api_items(contract),
        "example_ids": [example["id"] for example in contract["required_examples"]],
        "version_notes": version_notes,
        "notes": [
            "Generated by /environment/workspace/build_reference.py from the current bundled inputs.",
            f"Auto-assigned ids start at {id_start} in upstream/source/index.ts and queue option defaults are defined in upstream/source/options.ts.",
            f"Bundled tests move queue.timeout from {initial_timeout} to {updated_timeout} in upstream/test/test.ts.",
            *[f"Bundled sizeBy expectation: sizeBy({{priority: {priority}}}) -> {count}." for priority, count in priority_pairs[:2]],
            f"Release page highlight from upstream/release_v8.1.1.html: {release_note}.",
            f"Local reference pages reviewed under {workspace_root / 'docs' / '01-app' / '03-api-reference'}.",
        ],
    }
    return page, manifest


def main() -> int:
    args = parse_args()
    bundle_root = Path(args.bundle_root)
    workspace_root = Path(args.workspace_root)
    output_root = Path(args.output_root)
    output_root.mkdir(parents=True, exist_ok=True)

    page, manifest = build_page(bundle_root, workspace_root, output_root)
    contract = load_json(bundle_root / "contracts" / "page_contract.json")
    (output_root / contract["output_file"]).write_text(page, encoding="utf-8")
    (output_root / contract["manifest_file"]).write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
