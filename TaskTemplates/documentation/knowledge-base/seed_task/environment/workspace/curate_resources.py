#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--bundle-root", default="/app/knowledge-base")
    parser.add_argument("--workspace-root", default="/app/workspace")
    parser.add_argument("--output-root", default="/app/output")
    return parser.parse_args()


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def main() -> int:
    args = parse_args()
    bundle_root = Path(args.bundle_root)
    output_root = Path(args.output_root)
    output_root.mkdir(parents=True, exist_ok=True)

    contract = load_json(bundle_root / "contracts" / "resource_contract.json")
    candidates = load_json(bundle_root / "data" / "candidate_resources.json")["resources"]
    audit_index = {item["id"]: item for item in load_json(bundle_root / "data" / "link_audit_snapshot.json")["resources"]}

    selected = {}
    for section in contract["resource_sections"]:
        exact_count = contract["section_requirements"][section]["exact_count"]
        pool = [item for item in candidates if section in item["section_candidates"]]
        pool.sort(key=lambda item: (-item["quality_score"], item["title"]))
        selected[section] = pool[:exact_count]

    page_lines = [
        "---",
        f"title: {contract['page_title']}",
        f"slug: {contract['concept_slug']}",
        "description: Starter page built from the bundled candidate list.",
        "---",
        "",
        "import { Card, CardGroup } from 'fumadocs-ui/components/card';",
        "",
        f"# {contract['page_title']}",
        "",
    ]

    for section in contract["resource_sections"]:
        page_lines.extend([contract["section_headings"][section], "", "<CardGroup cols={2}>"])
        for resource in selected[section]:
            page_lines.extend(
                [
                    f'  <Card title="{resource["title"]}" icon="{contract["icons"].get(resource["resource_type"], "book")}" href="{resource["url"]}">',
                    f"    A useful {resource['resource_type']} about {contract['page_title']}.",
                    "  </Card>",
                ]
            )
        page_lines.extend(["</CardGroup>", ""])

    manifest = {
        "page_path": contract["output_file"],
        "concept_slug": contract["concept_slug"],
        "selected_resources": [
            {
                "id": resource["id"],
                "title": resource["title"],
                "section": section,
                "resource_type": resource["resource_type"],
                "url": resource["url"],
                "canonical_url": audit_index.get(resource["id"], {}).get("canonical_url", resource["canonical_url"]),
                "publication_year": resource["publication_year"],
                "status_code": audit_index.get(resource["id"], {}).get("status_code", 0),
                "reason_tags": resource["topic_tags"][:2],
            }
            for section, items in selected.items()
            for resource in items
        ],
        "section_counts": {section: len(items) for section, items in selected.items()},
        "notes": ["Starter implementation only."],
    }

    report = "\n".join(
        [
            "# Resource Audit Report",
            "",
            "## Summary",
            "",
            "Starter implementation.",
        ]
    )

    (output_root / contract["output_file"]).write_text("\n".join(page_lines) + "\n", encoding="utf-8")
    (output_root / contract["audit_report_file"]).write_text(report + "\n", encoding="utf-8")
    (output_root / contract["manifest_file"]).write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
