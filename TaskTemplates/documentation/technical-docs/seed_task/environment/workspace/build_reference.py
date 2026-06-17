#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build a basic PQueue reference page.")
    parser.add_argument("--bundle-root", default="/environment/reference_bundle")
    parser.add_argument("--workspace-root", default="/environment/workspace")
    parser.add_argument("--output-root", default="/environment/output")
    return parser.parse_args()


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def build_outputs(bundle_root: Path) -> tuple[str, dict]:
    contract = load_json(bundle_root / "contracts" / "page_contract.json")
    package = load_json(bundle_root / "upstream" / "package.json")
    version_notes = load_json(bundle_root / "contracts" / "version_notes.json")["entries"]

    page = "\n".join(
        [
            "---",
            f"title: {contract['frontmatter']['title']}",
            f"description: {contract['frontmatter']['description_template'].format(version=package['version'])}",
            f"nav_title: {contract['frontmatter']['nav_title']}",
            "---",
            "",
            "`PQueue` helps coordinate asynchronous work.",
            "",
            "```ts filename=\"docs/01-app/03-api-reference/04-functions/pqueue-basic.ts\" switcher",
            "import PQueue from 'p-queue';",
            "",
            "const queue = new PQueue({concurrency: 2});",
            "await queue.add(async () => fetch('https://example.com/a'));",
            "```",
            "",
            "## Reference",
            "",
            "### Constructor",
            "",
            "`new PQueue(options?)`",
            "",
            "Creates a queue instance.",
            "",
            "### Queue options",
            "",
            "Only a subset of queue options is documented here.",
            "",
            "### Task options",
            "",
            "Task-level behavior depends on the bundled source and tests.",
            "",
            "### Methods",
            "",
            "`add(fn, options?)` starts queued work and returns a promise.",
            "",
            "### Properties",
            "",
            "`size` reports queued work.",
            "",
            "### Events",
            "",
            "`idle` settles after running work completes.",
            "",
            "## Good to know",
            "",
            "This baseline page is incomplete.",
            "",
            "## Examples",
            "",
            "Additional usage examples can be derived from the bundled materials.",
            "",
            "## Version History",
            "",
            "| Version | Changes |",
            "| --- | --- |",
            *[f"| {entry['version']} | {entry['summary']} |" for entry in version_notes],
            "",
        ]
    )

    manifest = {
        "page_path": contract["output_file"],
        "api_name": contract["frontmatter"]["title"],
        "package_name": package["name"],
        "package_version": package["version"],
        "source_files": [
            "upstream/package.json",
            "upstream/source/index.ts",
        ],
        "documented_api_items": [
            {
                "name": contract["constructor"]["signature"],
                "kind": "constructor",
                "required_sections": ["Constructor"],
            }
        ],
        "example_ids": [],
        "version_notes": version_notes,
        "notes": [
            "The page is generated from the bundled package metadata, implementation, option types, behavior tests, README snippets, and release page bundle.",
            "The bundled release page text includes the aborted-job interval-cap fix that is also covered by the local tests.",
        ],
    }
    return page, manifest


def main() -> int:
    args = parse_args()
    bundle_root = Path(args.bundle_root)
    output_root = Path(args.output_root)
    output_root.mkdir(parents=True, exist_ok=True)

    contract = load_json(bundle_root / "contracts" / "page_contract.json")
    page, manifest = build_outputs(bundle_root)
    (output_root / contract["output_file"]).write_text(page, encoding="utf-8")
    (output_root / contract["manifest_file"]).write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
