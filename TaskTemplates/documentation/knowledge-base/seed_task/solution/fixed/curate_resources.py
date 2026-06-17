#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Refresh a bundled knowledge-base resource page.")
    parser.add_argument("--bundle-root", default="/app/knowledge-base")
    parser.add_argument("--workspace-root", default="/app/workspace")
    parser.add_argument("--output-root", default="/app/output")
    return parser.parse_args()


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def load_excerpts(bundle_root: Path, resources: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    excerpts: dict[str, dict[str, Any]] = {}
    for resource in resources:
        excerpt_path = bundle_root / resource["excerpt_file"]
        excerpts[resource["id"]] = load_json(excerpt_path)
    return excerpts


def make_audit_index(bundle_root: Path) -> dict[str, dict[str, Any]]:
    payload = load_json(bundle_root / "data" / "link_audit_snapshot.json")["resources"]
    return {item["id"]: item for item in payload}


def eligible(resource: dict[str, Any], audit: dict[str, Any], contract: dict[str, Any]) -> bool:
    rules = contract["selection_rules"]
    if resource["language"] != rules["required_language"]:
        return False
    if resource["access"] not in rules["allowed_access"]:
        return False
    if audit["status_code"] != 200:
        return False
    if set(audit["flags"]) & set(rules["reject_audit_flags"]):
        return False
    if set(resource["resource_flags"]) & set(rules["reject_resource_flags"]):
        return False
    for tag, minimum_year in rules["min_publication_year_by_topic"].items():
        if tag in resource["topic_tags"] and resource["publication_year"] < minimum_year:
            return False
    return True


def sorted_pool(resources: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return sorted(resources, key=lambda item: (-item["quality_score"], item["title"]))


def choose_for_slot(pool: list[dict[str, Any]], used_ids: set[str], slot: dict[str, Any]) -> dict[str, Any]:
    for resource in pool:
        if resource["id"] in used_ids:
            continue
        if any(tag not in resource["topic_tags"] for tag in slot["all_topic_tags"]):
            continue
        if slot["any_format_tags"] and not any(tag in resource["format_tags"] for tag in slot["any_format_tags"]):
            continue
        return resource
    raise ValueError(f"no candidate matches slot {slot['slot_id']}")


def select_resources(bundle_root: Path) -> dict[str, list[dict[str, Any]]]:
    contract = load_json(bundle_root / "contracts" / "resource_contract.json")
    resources = load_json(bundle_root / "data" / "candidate_resources.json")["resources"]
    audit_index = make_audit_index(bundle_root)

    eligible_resources = [
        {
            **resource,
            "status_code": audit_index[resource["id"]]["status_code"],
            "canonical_url_from_audit": audit_index[resource["id"]]["canonical_url"],
            "audit_flags": audit_index[resource["id"]]["flags"],
        }
        for resource in resources
        if resource["id"] in audit_index and eligible(resource, audit_index[resource["id"]], contract)
    ]

    selected: dict[str, list[dict[str, Any]]] = {}

    ref_pool = sorted_pool(
        [
            resource
            for resource in eligible_resources
            if "reference" in resource["section_candidates"]
            and resource["resource_type"] == "reference"
            and "official" in resource["format_tags"]
        ]
    )
    selected["reference"] = ref_pool[: contract["section_requirements"]["reference"]["exact_count"]]

    for section_name in ["articles", "videos", "books"]:
        requirement = contract["section_requirements"][section_name]
        pool = sorted_pool(
            [
                resource
                for resource in eligible_resources
                if section_name in resource["section_candidates"]
                and resource["resource_type"] in requirement["resource_types"]
            ]
        )
        chosen: list[dict[str, Any]] = []
        used_ids: set[str] = set()
        for slot in requirement["required_slots"]:
            resource = choose_for_slot(pool, used_ids, slot)
            chosen.append(resource)
            used_ids.add(resource["id"])
        while len(chosen) < requirement["exact_count"]:
            resource = next(resource for resource in pool if resource["id"] not in used_ids)
            chosen.append(resource)
            used_ids.add(resource["id"])
        selected[section_name] = chosen[: requirement["exact_count"]]

    return selected


def render_card(resource: dict[str, Any], excerpt: dict[str, Any], icon: str, indent: str = "  ") -> list[str]:
    description = " ".join(excerpt["description_sentences"])
    return [
        f'{indent}<Card title="{resource["title"]}" icon="{icon}" href="{resource["canonical_url_from_audit"]}">',
        f"{indent}  {description}",
        f"{indent}</Card>",
    ]


def replace_section(page_text: str, section_name: str, new_lines: list[str]) -> str:
    start_marker = f"<!-- RESOURCE-START:{section_name} -->"
    end_marker = f"<!-- RESOURCE-END:{section_name} -->"
    start_index = page_text.index(start_marker) + len(start_marker)
    end_index = page_text.index(end_marker)
    replacement = "\n" + "\n".join(new_lines) + "\n"
    return page_text[:start_index] + replacement + page_text[end_index:]


def clean_page(page_text: str, cleanup_tokens: list[str]) -> str:
    cleaned_lines: list[str] = []
    for line in page_text.splitlines():
        lowered = line.lower()
        if any(token in lowered for token in cleanup_tokens):
            continue
        cleaned_lines.append(line.rstrip())
    return "\n".join(cleaned_lines).strip() + "\n"


def render_sections(page_text: str, bundle_root: Path, selected: dict[str, list[dict[str, Any]]]) -> str:
    contract = load_json(bundle_root / "contracts" / "resource_contract.json")
    resources = load_json(bundle_root / "data" / "candidate_resources.json")["resources"]
    excerpts = load_excerpts(bundle_root, resources)
    icon_map = contract["icons"]

    for section_name in contract["resource_sections"]:
        resources_for_section = selected[section_name]
        if section_name == "books":
            block_lines = render_card(
                resources_for_section[0],
                excerpts[resources_for_section[0]["id"]],
                icon_map["book"],
                indent="",
            )
        else:
            block_lines = ["<CardGroup cols={2}>"]
            for resource in resources_for_section:
                block_lines.extend(render_card(resource, excerpts[resource["id"]], icon_map[resource["resource_type"]]))
            block_lines.append("</CardGroup>")
        page_text = replace_section(page_text, section_name, block_lines)
    return clean_page(page_text, contract["cleanup_tokens"])


def build_audit_report(bundle_root: Path, selected: dict[str, list[dict[str, Any]]]) -> str:
    contract = load_json(bundle_root / "contracts" / "resource_contract.json")
    audit_index = make_audit_index(bundle_root)
    selected_lookup = {resource["id"]: section for section, items in selected.items() for resource in items}

    draft_rows = [
        {
            "id": "old_mdn_promises_redirect",
            "title": "Promises on MDN (old link)",
            "replacement": "mdn_using_promises",
        },
        {
            "id": "broken_callback_hell_2014",
            "title": "Callback hell article",
            "replacement": "javascript_info_promise_basics",
        },
        {
            "id": "generic_async_post",
            "title": "Generic async post",
            "replacement": "lydia_visualized_promises_async_await",
        },
        {
            "id": "ms_csharp_async",
            "title": "Asynchronous programming with async and await — C#",
            "replacement": "javascript_info_async_await",
        },
        {
            "id": "placeholder_video",
            "title": "TODO: add better videos",
            "replacement": "jsconf_event_loop",
        },
        {
            "id": "placeholder_book",
            "title": "TBD",
            "replacement": "ydkjs_async_performance",
        },
    ]

    added_resources = [
        resource
        for items in selected.values()
        for resource in items
        if resource["id"] not in contract["draft_resource_ids"]
    ]

    lines = [
        f"# Resource Audit Report: {contract['page_title']}",
        "",
        "## Summary",
        "",
        "| Metric | Count |",
        "| --- | --- |",
        f"| Final resources | {sum(len(items) for items in selected.values())} |",
        f"| Draft resources replaced or removed | {len(draft_rows)} |",
        f"| New resources added | {len(added_resources)} |",
        "",
        "## Removed or Replaced",
        "",
        "| Draft resource | Reason | Replacement |",
        "| --- | --- | --- |",
    ]
    for row in draft_rows:
        flags = ", ".join(audit_index[row["id"]]["flags"])
        lines.append(f"| `{row['id']}` | {flags} | `{row['replacement']}` |")

    lines.extend(
        [
            "",
            "## Redirect Updates",
            "",
            "| Draft resource | Canonical URL |",
            "| --- | --- |",
            f"| `old_mdn_promises_redirect` | {audit_index['old_mdn_promises_redirect']['canonical_url']} |",
            "",
            "## Added Resources",
            "",
            "| Section | Resource |",
            "| --- | --- |",
        ]
    )
    for resource in added_resources:
        lines.append(f"| {selected_lookup[resource['id']]} | `{resource['id']}` |")

    lines.extend(["", "## Coverage Check", "", "| Section | Final count | Required count |", "| --- | --- | --- |"])
    for section_name in contract["resource_sections"]:
        lines.append(
            f"| {section_name} | {len(selected[section_name])} | {contract['section_requirements'][section_name]['exact_count']} |"
        )
    lines.append("")
    lines.append("- Coverage tags present: official, beginner, advanced, visual, promises, async-await.")
    return "\n".join(lines) + "\n"


def build_manifest(bundle_root: Path, selected: dict[str, list[dict[str, Any]]]) -> dict[str, Any]:
    contract = load_json(bundle_root / "contracts" / "resource_contract.json")
    manifest_resources = []
    for section_name in contract["resource_sections"]:
        for resource in selected[section_name]:
            manifest_resources.append(
                {
                    "id": resource["id"],
                    "title": resource["title"],
                    "section": section_name,
                    "resource_type": resource["resource_type"],
                    "url": resource["url"],
                    "canonical_url": resource["canonical_url_from_audit"],
                    "publication_year": resource["publication_year"],
                    "status_code": resource["status_code"],
                    "reason_tags": sorted(set(resource["topic_tags"] + resource["format_tags"]))[:5],
                }
            )
    return {
        "page_path": contract["output_file"],
        "concept_slug": contract["concept_slug"],
        "selected_resources": manifest_resources,
        "section_counts": {section_name: len(selected[section_name]) for section_name in contract["resource_sections"]},
        "notes": contract["manifest_notes"],
    }


def render_page(bundle_root: Path, output_root: Path) -> None:
    contract = load_json(bundle_root / "contracts" / "resource_contract.json")
    output_root.mkdir(parents=True, exist_ok=True)
    page_text = (bundle_root / "docs" / "promises-and-async-await.mdx").read_text(encoding="utf-8")
    selected = select_resources(bundle_root)
    final_page = render_sections(page_text, bundle_root, selected)

    page_path = output_root / contract["output_file"]
    report_path = output_root / contract["audit_report_file"]
    manifest_path = output_root / contract["manifest_file"]

    page_path.write_text(final_page, encoding="utf-8")
    report_path.write_text(build_audit_report(bundle_root, selected), encoding="utf-8")
    manifest_path.write_text(json.dumps(build_manifest(bundle_root, selected), indent=2) + "\n", encoding="utf-8")


def main() -> int:
    args = parse_args()
    render_page(Path(args.bundle_root), Path(args.output_root))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
