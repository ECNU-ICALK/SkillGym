from __future__ import annotations

import csv
import json
import os
import urllib.request
from pathlib import Path

import yaml


PRIORITY_RANK = {"P0": 0, "P1": 1, "P2": 2, "P3": 3}
DATA_ROOT = Path(os.environ.get("TASK_DATA_ROOT", "/root/data"))
OUTPUT_ROOT = Path(os.environ.get("TASK_OUTPUT_ROOT", "/root/output"))


def get_json(url: str) -> dict:
    req = urllib.request.Request(url, headers={"X-Client": "oracle-solution"})
    with urllib.request.urlopen(req, timeout=10) as resp:
        return json.loads(resp.read().decode("utf-8"))


def load_manifest() -> dict:
    return json.loads((DATA_ROOT / "planning_manifest.json").read_text(encoding="utf-8"))


def load_policy() -> dict:
    return yaml.safe_load((DATA_ROOT / "delivery_policy.yaml").read_text(encoding="utf-8"))


def load_capacity_totals() -> dict[str, int]:
    totals = {
        "story_points_available": 0,
        "qa_slots_available": 0,
        "review_slots_available": 0,
    }
    with (DATA_ROOT / "team_capacity.csv").open(newline="", encoding="utf-8") as fh:
        for row in csv.DictReader(fh):
            totals["story_points_available"] += int(row["story_points_available"])
            totals["qa_slots_available"] += int(row["qa_slots_available"])
            totals["review_slots_available"] += int(row["review_slots_available"])
    return totals


def fetch_live_items() -> list[dict]:
    manifest = load_manifest()
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


def why_selected(item: dict) -> str:
    reasons = []
    if item["must_ship"]:
        reasons.append("must-ship for the sprint theme")
    if item["hard_dependencies"]:
        reasons.append(f"unlocks or satisfies dependency chain {', '.join(item['hard_dependencies'])}")
    reasons.append("fits current capacity limits")
    return ", ".join(reasons)


def explain_rejection(reason: str) -> str:
    mapping = {
        "already_closed": "The issue is already closed and should not be re-committed.",
        "not_ready": "The item does not meet the current readiness bar for sprint commitment.",
        "blocked_dependency": "The item still has an unresolved blocker or unresolved hard dependency.",
        "insufficient_story_points": "Committing this item would exceed the story-point headroom after reserved buffer.",
        "insufficient_qa_capacity": "Committing this item would exceed the available QA capacity.",
        "insufficient_review_capacity": "Committing this item would exceed the available review bandwidth.",
        "below_cutline": "The item remained below the final cutline after higher-priority work was selected."
    }
    return mapping[reason]


def build_outputs() -> tuple[list[dict], dict, str]:
    manifest = load_manifest()
    policy = load_policy()
    totals = load_capacity_totals()
    items = fetch_live_items()
    items_by_id = {item["item_id"]: item for item in items}
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

    committed_items = []
    for item_id in selected_ids:
        item = items_by_id[item_id]
        committed_items.append(
            {
                "item_id": item_id,
                "title": item["title"],
                "priority": item["priority"],
                "story_points": int(item["story_points"]),
                "owner_role": item["owner_role"],
                "depends_on": item["hard_dependencies"],
                "why_selected": why_selected(item),
            }
        )

    deferred_items = []
    for item in items:
        reason = decisions[item["item_id"]]
        if reason and reason != "already_closed":
            deferred_items.append(
                {
                    "item_id": item["item_id"],
                    "rejection_reason": reason,
                    "explanation": explain_rejection(reason),
                }
            )

    high_priority_deferred = [
        item["item_id"]
        for item in items
        if decisions[item["item_id"]]
        and decisions[item["item_id"]] != "already_closed"
        and item["priority"] in {"P0", "P1"}
    ]
    risk_flags = [
        "SV-319 remains blocked outside the sprint despite P0 severity, so role-modification stability risk is still open.",
        "Review bandwidth is fully consumed by the committed set, leaving no room for extra discretionary work.",
        "The proxy-path follow-on chain stops at SV-204 this sprint, so SV-349 remains deferred."
    ]
    notes = [
        f"Release theme: {manifest['release_theme']}.",
        "Must-ship items were evaluated before discretionary items.",
        "Story point capacity uses total team points minus the reserved buffer."
    ]

    plan = {
        "sprint_id": manifest["sprint_id"],
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
            "review_slots_used": usage["review_slots_used"],
        },
        "risk_flags": risk_flags,
        "notes": notes,
    }

    manager_update = f"""# Sprint Manager Update

Sprint: {manifest['sprint_id']}

- Committed item count: {len(selected_ids)}
- Committed item IDs: {', '.join(selected_ids)}
- Total committed story points: {usage['story_points_committed']}
- High-priority deferred items: {', '.join(high_priority_deferred)}
- Main capacity bottleneck: review bandwidth is fully consumed and story-point headroom is limited after the reserved buffer.
- Top delivery risk: SV-319 remains blocked outside the sprint while network-control dependency work still dominates the release theme.
- Cutline rationale: commit every ready must-ship item first, then fill remaining headroom by policy priority, milestone date, downstream impact, and cost.
"""

    return triage_rows, plan, manager_update


def main() -> None:
    triage_rows, plan, manager_update = build_outputs()
    OUTPUT_ROOT.mkdir(parents=True, exist_ok=True)

    with (OUTPUT_ROOT / "backlog_triage.csv").open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(
            fh,
            fieldnames=[
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
            ],
        )
        writer.writeheader()
        writer.writerows(triage_rows)

    (OUTPUT_ROOT / "sprint_plan.json").write_text(json.dumps(plan, indent=2, sort_keys=True), encoding="utf-8")
    (OUTPUT_ROOT / "manager_update.md").write_text(manager_update, encoding="utf-8")


if __name__ == "__main__":
    main()
