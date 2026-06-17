from __future__ import annotations

import csv
import json
import urllib.request
from pathlib import Path

import yaml


PRIORITY_RANK = {"P0": 0, "P1": 1, "P2": 2, "P3": 3}


def get_json(url: str) -> dict:
    req = urllib.request.Request(url, headers={"X-Client": "skill-build-sprint-plan"})
    with urllib.request.urlopen(req, timeout=10) as resp:
        return json.loads(resp.read().decode("utf-8"))


def read_capacity() -> dict:
    totals = {
        "story_points_available": 0,
        "qa_slots_available": 0,
        "review_slots_available": 0,
    }
    with Path("/root/data/team_capacity.csv").open(newline="", encoding="utf-8") as fh:
        for row in csv.DictReader(fh):
            totals["story_points_available"] += int(row["story_points_available"])
            totals["qa_slots_available"] += int(row["qa_slots_available"])
            totals["review_slots_available"] += int(row["review_slots_available"])
    return totals


def sort_key(item: dict) -> tuple:
    return (
        PRIORITY_RANK[item["priority"]],
        item["milestone_date"],
        -int(item["downstream_blocked_count"]),
        int(item["story_points"]),
        item["item_id"],
    )


def can_select(item: dict, selected_ids: set[str], items_by_id: dict[str, dict], usage: dict, totals: dict, buffer_points: int) -> str | None:
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
    if usage["story_points_committed"] + item["story_points"] > totals["story_points_available"] - buffer_points:
        return "insufficient_story_points"
    next_qa = usage["qa_slots_used"] + (1 if item["qa_required"] else 0)
    if next_qa > totals["qa_slots_available"]:
        return "insufficient_qa_capacity"
    next_reviews = usage["review_slots_used"] + item["review_slots_required"]
    if next_reviews > totals["review_slots_available"]:
        return "insufficient_review_capacity"
    return None


def main() -> None:
    manifest = json.loads(Path("/root/data/planning_manifest.json").read_text(encoding="utf-8"))
    policy = yaml.safe_load(Path("/root/data/delivery_policy.yaml").read_text(encoding="utf-8"))
    totals = read_capacity()
    base_url = manifest["service_urls"]["planning_api"].rstrip("/")
    page_size = int(manifest.get("page_size_hint", 5))

    items = []
    page = 1
    while True:
        page_payload = get_json(f"{base_url}/items?page={page}&page_size={page_size}")
        for summary in page_payload["items"]:
            items.append(get_json(f"{base_url}/items/{summary['item_id']}"))
        if page_payload["next_page"] is None:
            break
        page = int(page_payload["next_page"])

    items = sorted(items, key=lambda item: item["item_id"])
    items_by_id = {item["item_id"]: item for item in items}
    usage = {"story_points_committed": 0, "qa_slots_used": 0, "review_slots_used": 0}
    selected_ids: list[str] = []
    selected_lookup: set[str] = set()
    decisions: dict[str, str] = {}
    buffer_points = int(policy["sprint_story_point_buffer"])

    must_ship = [item for item in items if item["must_ship"]]
    normal = [item for item in items if not item["must_ship"]]

    for group in (sorted(must_ship, key=sort_key), sorted(normal, key=sort_key)):
        for item in group:
            reason = can_select(item, selected_lookup, items_by_id, usage, totals, buffer_points)
            if reason is None:
                selected_ids.append(item["item_id"])
                selected_lookup.add(item["item_id"])
                usage["story_points_committed"] += item["story_points"]
                usage["qa_slots_used"] += 1 if item["qa_required"] else 0
                usage["review_slots_used"] += item["review_slots_required"]
                decisions[item["item_id"]] = ""
            else:
                decisions[item["item_id"]] = reason

    triage = []
    for item in items:
        triage.append(
            {
                "item_id": item["item_id"],
                "title": item["title"],
                "priority": item["priority"],
                "story_points": item["story_points"],
                "owner_role": item["owner_role"],
                "milestone_date": item["milestone_date"],
                "ready": item["ready"],
                "blocked": item["blocked"],
                "must_ship": item["must_ship"],
                "qa_required": item["qa_required"],
                "selected": item["item_id"] in selected_lookup,
                "rejection_reason": decisions[item["item_id"]],
            }
        )

    committed_items = []
    deferred_items = []
    for item_id in selected_ids:
        item = items_by_id[item_id]
        committed_items.append(
            {
                "item_id": item_id,
                "title": item["title"],
                "priority": item["priority"],
                "story_points": item["story_points"],
                "owner_role": item["owner_role"],
                "depends_on": item["hard_dependencies"],
            }
        )
    for item in items:
        reason = decisions[item["item_id"]]
        if reason and reason != "already_closed":
            deferred_items.append(
                {
                    "item_id": item["item_id"],
                    "rejection_reason": reason,
                }
            )

    print(
        json.dumps(
            {
                "triage": triage,
                "committed_item_ids": selected_ids,
                "committed_items": committed_items,
                "deferred_items": deferred_items,
                "capacity_summary": {
                    "story_points_available": totals["story_points_available"],
                    "buffer_points_reserved": buffer_points,
                    "story_points_committed": usage["story_points_committed"],
                    "qa_slots_available": totals["qa_slots_available"],
                    "qa_slots_used": usage["qa_slots_used"],
                    "review_slots_available": totals["review_slots_available"],
                    "review_slots_used": usage["review_slots_used"]
                }
            },
            indent=2,
            sort_keys=True
        )
    )


if __name__ == "__main__":
    main()
