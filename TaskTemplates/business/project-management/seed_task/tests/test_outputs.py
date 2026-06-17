from __future__ import annotations

import re

from common import (
    PLAN_PATH,
    TRIAGE_FIELDS,
    TRIAGE_PATH,
    UPDATE_PATH,
    build_expected,
    load_plan,
    load_triage_rows,
    normalize_bool,
)


def test_required_output_files_exist() -> None:
    assert TRIAGE_PATH.exists(), "Missing /root/output/backlog_triage.csv"
    assert PLAN_PATH.exists(), "Missing /root/output/sprint_plan.json"
    assert UPDATE_PATH.exists(), "Missing /root/output/manager_update.md"


def test_backlog_triage_matches_expected_live_facts() -> None:
    expected = build_expected()
    actual_rows = load_triage_rows()
    assert len(actual_rows) == len(expected["triage_rows"]), "Unexpected number of triage rows"

    actual_by_id = {row["item_id"]: row for row in actual_rows}
    expected_by_id = {row["item_id"]: row for row in expected["triage_rows"]}
    assert set(actual_by_id) == set(expected_by_id), "Triage item IDs do not match the live backlog"

    for item_id, expected_row in expected_by_id.items():
        actual_row = actual_by_id[item_id]
        assert list(actual_row.keys()) == TRIAGE_FIELDS, f"Triage header mismatch for {item_id}"
        for field in ["story_points", "milestone_date", "priority", "owner_role", "title", "rejection_reason"]:
            assert actual_row[field] == expected_row[field], f"{item_id} field {field} mismatch"
        for field in ["ready", "blocked", "must_ship", "qa_required", "selected"]:
            assert normalize_bool(actual_row[field]) == expected_row[field], f"{item_id} field {field} mismatch"


def test_sprint_plan_matches_expected_commitment() -> None:
    expected = build_expected()
    items_by_id = expected["items_by_id"]
    plan = load_plan()

    assert plan["sprint_id"] == "SPR-2026-11"
    assert plan["committed_item_ids"] == expected["selected_ids"], "Committed item order is incorrect"

    committed_items = plan["committed_items"]
    assert len(committed_items) == len(expected["selected_ids"])
    for item, expected_id in zip(committed_items, expected["selected_ids"]):
        source = items_by_id[expected_id]
        assert item["item_id"] == expected_id
        assert item["title"] == source["title"]
        assert item["priority"] == source["priority"]
        assert int(item["story_points"]) == int(source["story_points"])
        assert item["owner_role"] == source["owner_role"]
        assert item["depends_on"] == source["hard_dependencies"]
        assert isinstance(item["why_selected"], str) and item["why_selected"].strip(), f"why_selected missing for {expected_id}"

    deferred_map = {item["item_id"]: item for item in plan["deferred_items"]}
    assert set(deferred_map) == set(expected["deferred_ids"]), "Deferred item coverage is incorrect"
    for item_id in expected["deferred_ids"]:
        assert deferred_map[item_id]["rejection_reason"] == expected["decisions"][item_id]
        assert isinstance(deferred_map[item_id]["explanation"], str) and deferred_map[item_id]["explanation"].strip()

    assert plan["capacity_summary"] == expected["capacity_summary"], "Capacity summary mismatch"
    assert isinstance(plan["risk_flags"], list) and len(plan["risk_flags"]) >= 2
    assert isinstance(plan["notes"], list) and len(plan["notes"]) >= 2
    assert any("SV-319" in flag for flag in plan["risk_flags"]), "Risk flags must mention blocked P0 item SV-319"
    assert any("review" in flag.lower() for flag in plan["risk_flags"]), "Risk flags must mention review bandwidth"


def test_manager_update_contains_required_business_facts() -> None:
    expected = build_expected()
    text = UPDATE_PATH.read_text(encoding="utf-8")

    assert "SPR-2026-11" in text
    assert re.search(r"5", text), "Manager update must mention committed item count"
    for item_id in expected["selected_ids"]:
        assert item_id in text, f"Manager update missing committed ID {item_id}"
    assert "24" in text, "Manager update must mention total committed story points"
    for item_id in expected["high_priority_deferred"]:
        assert item_id in text, f"Manager update missing deferred high-priority ID {item_id}"
    assert "review" in text.lower() or "story point" in text.lower(), "Manager update must mention capacity bottleneck"
    assert "SV-319" in text, "Manager update must mention the key blocked risk"
