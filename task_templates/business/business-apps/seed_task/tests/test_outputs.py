from __future__ import annotations

from common import BRIEF_PATH, SUMMARY_PATH, WORKLIST_FIELDS, WORKLIST_PATH, build_expected, load_summary, load_worklist


def test_required_output_files_exist() -> None:
    assert WORKLIST_PATH.exists(), "Missing /root/output/renewal_worklist.csv"
    assert SUMMARY_PATH.exists(), "Missing /root/output/renewal_control_summary.json"
    assert BRIEF_PATH.exists(), "Missing /root/output/ops_brief.md"


def test_renewal_worklist_matches_live_expected_rows() -> None:
    expected = build_expected()
    actual_rows = load_worklist()
    assert len(actual_rows) == len(expected["rows"]), "Unexpected number of worklist rows"
    actual_by_id = {row["account_id"]: row for row in actual_rows}
    expected_by_id = {row["account_id"]: row for row in expected["rows"]}
    assert set(actual_by_id) == set(expected_by_id), "Worklist account IDs do not match the live cohort"
    for account_id, expected_row in expected_by_id.items():
        actual_row = actual_by_id[account_id]
        assert list(actual_row.keys()) == WORKLIST_FIELDS, f"CSV header mismatch for {account_id}"
        for field in WORKLIST_FIELDS:
            if field == "renewal_arr_usd":
                assert float(actual_row[field]) == float(expected_row[field]), f"{account_id} field {field} mismatch"
                continue
            if field == "seat_delta":
                assert int(actual_row[field]) == int(expected_row[field]), f"{account_id} field {field} mismatch"
                continue
            if field == "next_step":
                assert isinstance(actual_row[field], str) and actual_row[field].strip(), f"{account_id} field {field} mismatch"
                continue
            assert str(actual_row[field]) == str(expected_row[field]), f"{account_id} field {field} mismatch"


def test_control_summary_matches_recomputed_values() -> None:
    expected = build_expected()
    summary = load_summary()
    assert summary["workspace_id"] == expected["task_manifest"]["workspace_id"]
    assert summary["cohort_date"] == expected["task_manifest"]["cohort_date"]
    assert summary["totals"] == expected["totals"], "Summary totals mismatch"
    assert summary["action_counts"] == expected["action_counts"], "Action counts mismatch"
    assert summary["workflow_blocked_account_ids"] == expected["blocked_ids"], "Blocked account list mismatch"
    assert summary["service_checks"] == {
        "revops_manifest": True,
        "accounts": True,
        "account_details": True,
        "renewal_previews": True,
        "dunning_events": True,
    }
    assert isinstance(summary["notes"], list) and len(summary["notes"]) >= 2


def test_ops_brief_contains_required_business_facts() -> None:
    expected = build_expected()
    text = BRIEF_PATH.read_text(encoding="utf-8")
    assert expected["task_manifest"]["workspace_id"] in text
    assert expected["task_manifest"]["cohort_date"] in text
    assert str(expected["totals"]["accounts_reviewed"]) in text
    assert str(expected["totals"]["accounts_needing_action"]) in text
    for account_id in expected["blocked_ids"]:
        assert account_id in text, f"Brief missing blocked account {account_id}"
    assert expected["highest_expansion"]["account_id"] in text, "Brief missing top expansion account"
    assert expected["urgent_collect"]["account_id"] in text, "Brief missing urgent collection account"
    lowered = text.lower()
    assert any(
        token in lowered
        for token in [
            "logic",
            "priority",
            "rule",
            "routing",
            "逻辑",
            "优先级",
            "legal hold",
            "procurement",
            "quote",
            "催收",
        ]
    ), "Brief must explain the action routing logic"
