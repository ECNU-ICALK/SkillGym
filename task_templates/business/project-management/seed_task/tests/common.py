from __future__ import annotations

import csv
import json
import os
import urllib.request
from pathlib import Path

import yaml


DATA_ROOT = Path(os.environ.get("TASK_DATA_ROOT", "/root/data"))
OUTPUT_DIR = Path(os.environ.get("TASK_OUTPUT_ROOT", "/root/output"))
TRIAGE_PATH = OUTPUT_DIR / "backlog_triage.csv"
PLAN_PATH = OUTPUT_DIR / "sprint_plan.json"
UPDATE_PATH = OUTPUT_DIR / "manager_update.md"
MANIFEST_PATH = DATA_ROOT / "planning_manifest.json"
CAPACITY_PATH = DATA_ROOT / "team_capacity.csv"
POLICY_PATH = DATA_ROOT / "delivery_policy.yaml"

PRIORITY_RANK = {"P0": 0, "P1": 1, "P2": 2, "P3": 3}
TRIAGE_FIELDS = [
    "item_id",
    "title",
    "priority",
    "story_points",
    "owner_role",
    "milestone_date",
    "ready",
    "blocked",
    "must_ship",
    "qa_required",
    "selected",
    "rejection_reason",
]


def get_json(url: str, client: str = "verifier-main") -> dict:
    req = urllib.request.Request(url, headers={"X-Client": client})
    with urllib.request.urlopen(req, timeout=10) as resp:
        return json.loads(resp.read().decode("utf-8"))


def load_manifest() -> dict:
    return json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))


def load_policy() -> dict:
    return yaml.safe_load(POLICY_PATH.read_text(encoding="utf-8"))


def load_capacity_totals() -> dict[str, int]:
    totals = {
        "story_points_available": 0,
        "qa_slots_available": 0,
        "review_slots_available": 0,
    }
    with CAPACITY_PATH.open(newline="", encoding="utf-8") as fh:
        for row in csv.DictReader(fh):
            totals["story_points_available"] += int(row["story_points_available"])
            totals["qa_slots_available"] += int(row["qa_slots_available"])
            totals["review_slots_available"] += int(row["review_slots_available"])
    return totals


def fetch_live_items(client: str = "verifier-main") -> list[dict]:
    manifest = load_manifest()
    base_url = manifest["service_urls"]["planning_api"].rstrip("/")
    page_size = int(manifest.get("page_size_hint", 5))
    items = []
    page = 1
    while True:
        page_payload = get_json(f"{base_url}/items?page={page}&page_size={page_size}", client=client)
        for summary in page_payload["items"]:
            items.append(get_json(f"{base_url}/items/{summary['item_id']}", client=client))
        if page_payload["next_page"] is None:
            break
        page = int(page_payload["next_page"])
    return sorted(items, key=lambda item: item["item_id"])


def sort_key(item: dict) -> tuple:
    return (
        PRIORITY_RANK[item["priority"]],
        item["milestone_date"],
        -int(item["downstream_blocked_count"]),
        int(item["story_points"]),
        item["item_id"],
    )


def reason_if_not_selectable(
    item: dict,
    selected_ids: set[str],
    items_by_id: dict[str, dict],
    usage: dict[str, int],
    totals: dict[str, int],
    buffer_points: int,
) -> str | None:
    if item["current_status"] in {"closed", "done", "cancelled", "archived"} or item["source_state"] == "closed":
        return "already_closed"
    if not item["ready"]:
        return "not_ready"
    if item["blocked"]:
        return "blocked_dependency"
    for dep_id in item["hard_dependencies"]:
        dep = items_by_id[dep_id]
        dep_closed = dep["current_status"] in {"closed", "done", "cancelled", "archived"} or dep["source_state"] == "closed"
        if not dep_closed and dep_id not in selected_ids:
            return "blocked_dependency"
    if usage["story_points_committed"] + int(item["story_points"]) > totals["story_points_available"] - buffer_points:
        return "insufficient_story_points"
    next_qa = usage["qa_slots_used"] + (1 if item["qa_required"] else 0)
    if next_qa > totals["qa_slots_available"]:
        return "insufficient_qa_capacity"
    next_reviews = usage["review_slots_used"] + int(item["review_slots_required"])
    if next_reviews > totals["review_slots_available"]:
        return "insufficient_review_capacity"
    return None


def build_expected() -> dict:
    items = fetch_live_items()
    items_by_id = {item["item_id"]: item for item in items}
    policy = load_policy()
    totals = load_capacity_totals()
    buffer_points = int(policy["sprint_story_point_buffer"])

    usage = {"story_points_committed": 0, "qa_slots_used": 0, "review_slots_used": 0}
    selected_ids: list[str] = []
    selected_lookup: set[str] = set()
    decisions: dict[str, str] = {}

    must_ship = [item for item in items if item["must_ship"]]
    normal = [item for item in items if not item["must_ship"]]

    for group in (sorted(must_ship, key=sort_key), sorted(normal, key=sort_key)):
        for item in group:
            reason = reason_if_not_selectable(item, selected_lookup, items_by_id, usage, totals, buffer_points)
            if reason is None:
                selected_ids.append(item["item_id"])
                selected_lookup.add(item["item_id"])
                usage["story_points_committed"] += int(item["story_points"])
                usage["qa_slots_used"] += 1 if item["qa_required"] else 0
                usage["review_slots_used"] += int(item["review_slots_required"])
                decisions[item["item_id"]] = ""
            else:
                decisions[item["item_id"]] = reason

    triage_rows = []
    for item in items:
        triage_rows.append(
            {
                "item_id": item["item_id"],
                "title": item["title"],
                "priority": item["priority"],
                "story_points": str(item["story_points"]),
                "owner_role": item["owner_role"],
                "milestone_date": item["milestone_date"],
                "ready": "true" if item["ready"] else "false",
                "blocked": "true" if item["blocked"] else "false",
                "must_ship": "true" if item["must_ship"] else "false",
                "qa_required": "true" if item["qa_required"] else "false",
                "selected": "true" if item["item_id"] in selected_lookup else "false",
                "rejection_reason": decisions[item["item_id"]],
            }
        )

    deferred_ids = [
        item["item_id"]
        for item in items
        if decisions[item["item_id"]] and decisions[item["item_id"]] != "already_closed"
    ]
    high_priority_deferred = [
        item["item_id"]
        for item in items
        if decisions[item["item_id"]]
        and decisions[item["item_id"]] != "already_closed"
        and item["priority"] in {"P0", "P1"}
    ]

    return {
        "items": items,
        "items_by_id": items_by_id,
        "selected_ids": selected_ids,
        "decisions": decisions,
        "triage_rows": triage_rows,
        "deferred_ids": deferred_ids,
        "high_priority_deferred": high_priority_deferred,
        "capacity_summary": {
            "story_points_available": totals["story_points_available"],
            "buffer_points_reserved": buffer_points,
            "story_points_committed": usage["story_points_committed"],
            "qa_slots_available": totals["qa_slots_available"],
            "qa_slots_used": usage["qa_slots_used"],
            "review_slots_available": totals["review_slots_available"],
            "review_slots_used": usage["review_slots_used"],
        },
    }


def load_triage_rows() -> list[dict]:
    with TRIAGE_PATH.open(newline="", encoding="utf-8") as fh:
        return list(csv.DictReader(fh))


def load_plan() -> dict:
    return json.loads(PLAN_PATH.read_text(encoding="utf-8"))


def normalize_bool(value: str) -> str:
    lowered = value.strip().lower()
    if lowered not in {"true", "false"}:
        raise AssertionError(f"Expected true/false string, got {value!r}")
    return lowered
