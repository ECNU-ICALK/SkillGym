from __future__ import annotations

import hashlib
import html
import json
import os
import re
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Any


TASK_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_BUNDLE_ROOT = Path("/app/knowledge-base")
DEFAULT_WORKSPACE_ROOT = Path("/app/workspace")
DEFAULT_OUTPUT_ROOT = Path("/app/output")

BUNDLE_ROOT = Path(os.environ.get("TASK_BUNDLE_ROOT", DEFAULT_BUNDLE_ROOT))
WORKSPACE_ROOT = Path(os.environ.get("TASK_WORKSPACE_ROOT", DEFAULT_WORKSPACE_ROOT))
OUTPUT_ROOT = Path(os.environ.get("TASK_OUTPUT_ROOT", DEFAULT_OUTPUT_ROOT))

if not BUNDLE_ROOT.exists():
    BUNDLE_ROOT = TASK_ROOT / "environment" / "knowledge_base"
if not WORKSPACE_ROOT.exists():
    WORKSPACE_ROOT = TASK_ROOT / "environment" / "workspace"
if not OUTPUT_ROOT.parent.exists():
    OUTPUT_ROOT = TASK_ROOT / ".tmp_test_output"

BUILD_ENTRYPOINT = WORKSPACE_ROOT / "curate_resources.py"


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def run_build(bundle_root: Path = BUNDLE_ROOT, output_root: Path = OUTPUT_ROOT) -> subprocess.CompletedProcess[str]:
    if output_root.exists():
        shutil.rmtree(output_root)
    output_root.mkdir(parents=True, exist_ok=True)
    return subprocess.run(
        [
            "python3",
            str(BUILD_ENTRYPOINT),
            "--bundle-root",
            str(bundle_root),
            "--workspace-root",
            str(WORKSPACE_ROOT),
            "--output-root",
            str(output_root),
        ],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        check=False,
        cwd=WORKSPACE_ROOT,
    )


def contract(bundle_root: Path = BUNDLE_ROOT) -> dict[str, Any]:
    return load_json(bundle_root / "contracts" / "resource_contract.json")


def candidate_resources(bundle_root: Path = BUNDLE_ROOT) -> list[dict[str, Any]]:
    return load_json(bundle_root / "data" / "candidate_resources.json")["resources"]


def resource_index(bundle_root: Path = BUNDLE_ROOT) -> dict[str, dict[str, Any]]:
    return {item["id"]: item for item in candidate_resources(bundle_root)}


def audit_index(bundle_root: Path = BUNDLE_ROOT) -> dict[str, dict[str, Any]]:
    return {item["id"]: item for item in load_json(bundle_root / "data" / "link_audit_snapshot.json")["resources"]}


def output_page(output_root: Path = OUTPUT_ROOT, bundle_root: Path = BUNDLE_ROOT) -> Path:
    return output_root / contract(bundle_root)["output_file"]


def output_report(output_root: Path = OUTPUT_ROOT, bundle_root: Path = BUNDLE_ROOT) -> Path:
    return output_root / contract(bundle_root)["audit_report_file"]


def output_manifest(output_root: Path = OUTPUT_ROOT, bundle_root: Path = BUNDLE_ROOT) -> Path:
    return output_root / contract(bundle_root)["manifest_file"]


def read_page(output_root: Path = OUTPUT_ROOT, bundle_root: Path = BUNDLE_ROOT) -> str:
    return output_page(output_root, bundle_root).read_text(encoding="utf-8")


def read_manifest(output_root: Path = OUTPUT_ROOT, bundle_root: Path = BUNDLE_ROOT) -> dict[str, Any]:
    return load_json(output_manifest(output_root, bundle_root))


def read_report(output_root: Path = OUTPUT_ROOT, bundle_root: Path = BUNDLE_ROOT) -> str:
    return output_report(output_root, bundle_root).read_text(encoding="utf-8")


def directory_listing(root: Path) -> str:
    if not root.exists():
        return ""
    lines: list[str] = []
    for path in sorted(p for p in root.rglob("*") if p.is_file()):
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        lines.append(f"{digest}  {path.relative_to(root).as_posix()}")
    return "\n".join(lines) + ("\n" if lines else "")


def normalize_listing_text(text: str) -> str:
    lines: list[str] = []
    for line in text.splitlines():
        if not line.strip():
            continue
        digest, _, rel_path = line.partition("  ")
        lines.append(f"{digest}  {rel_path.removeprefix('./')}")
    return "\n".join(lines) + ("\n" if lines else "")


def baseline_bundle_listing() -> str:
    candidate = Path("/opt/task-baselines/knowledge-base.sha256")
    if candidate.exists():
        return normalize_listing_text(candidate.read_text(encoding="utf-8"))
    return directory_listing(BUNDLE_ROOT)


def section_block(page_text: str, section_name: str) -> str:
    start_marker = f"<!-- RESOURCE-START:{section_name} -->"
    end_marker = f"<!-- RESOURCE-END:{section_name} -->"
    pattern = re.compile(re.escape(start_marker) + r"(.*?)" + re.escape(end_marker), re.S)
    match = pattern.search(page_text)
    assert match, f"missing section markers for {section_name}"
    return match.group(1)


def parse_cards(block_text: str) -> list[dict[str, str]]:
    pattern = re.compile(
        r'<Card '
        r'title=(?:"(?P<title_q>[^"]+)"|\{"(?P<title_b>[^"]+)"\}) '
        r'icon=(?:"(?P<icon_q>[^"]+)"|\{"(?P<icon_b>[^"]+)"\}) '
        r'href=(?:"(?P<href_q>[^"]+)"|\{"(?P<href_b>[^"]+)"\})>\s*(?P<body>.*?)\s*</Card>',
        re.S,
    )
    cards = []
    for match in pattern.finditer(block_text):
        cards.append(
            {
                "title": html.unescape(match.group("title_q") or match.group("title_b") or ""),
                "icon": html.unescape(match.group("icon_q") or match.group("icon_b") or ""),
                "href": html.unescape(match.group("href_q") or match.group("href_b") or ""),
                "body": html.unescape(" ".join(match.group("body").split())),
            }
        )
    return cards


def eligible(resource: dict[str, Any], audit: dict[str, Any], payload: dict[str, Any]) -> bool:
    rules = payload["selection_rules"]
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


def sorted_pool(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return sorted(items, key=lambda item: (-item["quality_score"], item["title"]))


def choose_for_slot(pool: list[dict[str, Any]], used_ids: set[str], slot: dict[str, Any]) -> dict[str, Any]:
    for resource in pool:
        if resource["id"] in used_ids:
            continue
        if any(tag not in resource["topic_tags"] for tag in slot["all_topic_tags"]):
            continue
        if slot["any_format_tags"] and not any(tag in resource["format_tags"] for tag in slot["any_format_tags"]):
            continue
        return resource
    raise AssertionError(f"no candidate matches slot {slot['slot_id']}")


def expected_selection(bundle_root: Path = BUNDLE_ROOT) -> dict[str, list[dict[str, Any]]]:
    payload = contract(bundle_root)
    resources = candidate_resources(bundle_root)
    audits = audit_index(bundle_root)
    eligible_resources = [
        {
            **resource,
            "status_code": audits[resource["id"]]["status_code"],
            "canonical_url_from_audit": audits[resource["id"]]["canonical_url"],
        }
        for resource in resources
        if resource["id"] in audits and eligible(resource, audits[resource["id"]], payload)
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
    selected["reference"] = ref_pool[: payload["section_requirements"]["reference"]["exact_count"]]

    for section_name in ["articles", "videos", "books"]:
        requirement = payload["section_requirements"][section_name]
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


def make_alternate_bundle_copy() -> tuple[tempfile.TemporaryDirectory[str], Path]:
    tmpdir = tempfile.TemporaryDirectory(prefix="knowledge-base-alt-")
    alt_root = Path(tmpdir.name) / "knowledge-base"
    shutil.copytree(BUNDLE_ROOT, alt_root)

    candidates = load_json(alt_root / "data" / "candidate_resources.json")
    for item in candidates["resources"]:
        if item["id"] == "webdev_async_functions":
            item["resource_flags"] = ["generic_description"]
        if item["id"] == "freecodecamp_escape_async_await_hell":
            item["quality_score"] = 94
        if item["id"] == "fireship_async_await_100_seconds":
            item["title"] = "Async and Await in 100 Seconds — Fireship"
    (alt_root / "data" / "candidate_resources.json").write_text(json.dumps(candidates, indent=2) + "\n", encoding="utf-8")

    audits = load_json(alt_root / "data" / "link_audit_snapshot.json")
    for item in audits["resources"]:
        if item["id"] == "webdev_async_functions":
            item["flags"] = ["generic_description"]
    (alt_root / "data" / "link_audit_snapshot.json").write_text(json.dumps(audits, indent=2) + "\n", encoding="utf-8")

    fireship_excerpt = load_json(alt_root / "data" / "source_excerpts" / "fireship_async_await_100_seconds.json")
    fireship_excerpt["description_sentences"][0] = "A fast visual recap of how `await` reshapes Promise-driven control flow in modern JavaScript."
    (alt_root / "data" / "source_excerpts" / "fireship_async_await_100_seconds.json").write_text(
        json.dumps(fireship_excerpt, indent=2) + "\n",
        encoding="utf-8",
    )
    return tmpdir, alt_root
