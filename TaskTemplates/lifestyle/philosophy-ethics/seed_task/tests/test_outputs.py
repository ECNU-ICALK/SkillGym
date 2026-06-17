from __future__ import annotations

import re

from conftest import (
    OUTPUT_ROOT,
    assumption_rows_expected,
    built_output,
    contract,
    expected_assessment,
    expected_bundle,
    expected_issue_rows,
    load_tsv,
    read_bundle,
    read_plan,
    source_inventory_expected,
)


def test_required_outputs_exist_and_parse() -> None:
    output_root = built_output()
    required = [
        "decision_memo.md",
        "source_inventory.tsv",
        "option_assessment.tsv",
        "decision_issues.tsv",
        "assumption_audit.tsv",
        "safeguard_plan.yaml",
        "decision_bundle.json",
    ]
    for name in required:
        path = output_root / name
        assert path.exists(), f"missing required output: {path}"
        assert path.stat().st_size > 0, f"empty required output: {path}"


def test_source_inventory_matches_contract() -> None:
    built_output()
    rows = load_tsv(OUTPUT_ROOT / "source_inventory.tsv")
    expected = source_inventory_expected()
    assert [*rows[0].keys()] == contract()["output_contract"]["source_inventory_columns"]
    assert len(rows) == len(expected)
    normalized = []
    for row in rows:
        normalized.append(
            {
                "source_name": row["source_name"],
                "path": row["path"].rstrip("/"),
                "source_type": row["source_type"]
                .replace("json directory", "directory")
                .replace("json_directory", "directory")
                .replace("json_collection", "directory"),
            }
        )
    expected_normalized = [
        {
            "source_name": row["source_name"],
            "path": row["path"].rstrip("/"),
            "source_type": row["source_type"],
        }
        for row in expected
    ]
    assert normalized == expected_normalized


def test_option_assessment_matches_oracle() -> None:
    built_output()
    rows = load_tsv(OUTPUT_ROOT / "option_assessment.tsv")
    expected = expected_assessment()
    assert [*rows[0].keys()] == contract()["output_contract"]["option_assessment_columns"]

    def normalize_status(value: str, outcome_id: str) -> str:
        mapping = {
            "eligible": "eligible",
            "recommended": "eligible",
            "selected": "eligible",
            "blocked": "blocked",
            "hard_fail": "blocked",
            "fallback": "fallback",
            "rejected": "fallback" if outcome_id == "defer_pilot" else "blocked",
            "not_selected": "fallback" if outcome_id == "defer_pilot" else "eligible",
        }
        return mapping.get(value, value)

    def normalize_reason(value: str) -> str:
        cleaned = value.strip()
        if cleaned in {"", "-", "n/a", "NA"}:
            return "none"
        reason_map = {
            "budget_cap_usd": "budget_cap",
            "prompt_retention_days": "retention_limit",
            "student_data_used_for_model_training": "model_training",
            "human_review_for_graded_work": "graded_use_review",
            "teacher_opt_in_first_semester": "teacher_opt_in",
            "family_notice_plan": "family_notice",
            "student_opt_out": "student_opt_out",
        }
        parts = [reason_map.get(part, part) for part in cleaned.split(",") if part]
        return ",".join(parts) if parts else "none"

    def normalize_budget_status(value: str) -> str:
        mapping = {
            "within_cap": "within_cap",
            "meets": "within_cap",
            "pass": "within_cap",
            "over_cap": "over_cap",
            "fails": "over_cap",
            "fail": "over_cap",
        }
        return mapping.get(value, value)

    def normalize_data_status(value: str) -> str:
        mapping = {
            "compliant": "compliant",
            "meets": "compliant",
            "meets_requirement": "compliant",
            "meets_non_negotiables": "compliant",
            "non_compliant": "non_compliant",
            "fails": "non_compliant",
            "fails_requirement": "non_compliant",
            "violates_non_negotiables": "non_compliant",
            "pass": "compliant",
            "fail": "non_compliant",
        }
        return mapping.get(value, value)

    def normalize_oversight_status(value: str) -> str:
        mapping = {
            "ready": "ready",
            "meets": "ready",
            "meets_requirement": "ready",
            "meets_non_negotiables": "ready",
            "gap": "gap",
            "fails": "gap",
            "fails_requirement": "gap",
            "violates_non_negotiables": "gap",
            "planning_only": "gap",
            "not_applicable": "gap",
            "pass": "ready",
            "fail": "gap",
        }
        return mapping.get(value, value)

    def normalize_next_step(value: str) -> str:
        mapping = {
            "prepare_board_packet": "prepare_board_packet",
            "board_approval_with_controls": "prepare_board_packet",
            "approve_with_required_controls": "prepare_board_packet",
            "advance_with_required_controls": "prepare_board_packet",
            "advance_to_board_approval": "prepare_board_packet",
            "reject_for_current_cycle": "reject_for_current_cycle",
            "do_not_advance": "reject_for_current_cycle",
            "do_not_advance_in_current_cycle": "reject_for_current_cycle",
            "procurement_readiness_only": "procurement_readiness_only",
        }
        lowered = value.strip().lower()
        if lowered.startswith("approve the bounded pilot"):
            return "prepare_board_packet"
        if lowered == "approve with required controls":
            return "prepare_board_packet"
        if lowered == "complete_required_controls_before_launch":
            return "prepare_board_packet"
        if lowered == "prepare_launch_controls":
            return "prepare_board_packet"
        if lowered == "launch_with_controls":
            return "prepare_board_packet"
        if lowered.startswith("do not select"):
            return "reject_for_current_cycle"
        if lowered == "reject for this cycle":
            return "reject_for_current_cycle"
        if lowered == "remove_from_current_cycle":
            return "reject_for_current_cycle"
        if value.startswith("retain_as_fallback"):
            return "procurement_readiness_only"
        if lowered.startswith("keep as the board's fallback"):
            return "procurement_readiness_only"
        if lowered == "hold as fallback if launch controls slip":
            return "procurement_readiness_only"
        if lowered == "hold_as_fallback":
            return "procurement_readiness_only"
        return mapping.get(value, value)

    normalized = []
    for row in rows:
        normalized.append(
            {
                "option_id": row["option_id"],
                "outcome_id": row["outcome_id"],
                "decision_status": normalize_status(row["decision_status"], row["outcome_id"]),
                "hard_fail_reasons": normalize_reason(row["hard_fail_reasons"]),
                "governance_score": int(float(row["governance_score"])),
                "delivery_score": int(float(row["delivery_score"])),
                "total_score": float(row["total_score"]),
                "budget_status": normalize_budget_status(row["budget_status"]),
                "data_status": normalize_data_status(row["data_status"]),
                "oversight_status": normalize_oversight_status(row["oversight_status"]),
                "recommended_next_step": normalize_next_step(row["recommended_next_step"]),
            }
        )

    expected_by_option = {row["option_id"]: row for row in expected}
    for row in normalized:
        oracle = expected_by_option[row["option_id"]]
        assert row["outcome_id"] == oracle["outcome_id"]
        assert row["decision_status"] == oracle["decision_status"]
        assert row["hard_fail_reasons"] == oracle["hard_fail_reasons"]
        assert row["budget_status"] == oracle["budget_status"]
        assert row["data_status"] == oracle["data_status"]
        if row["decision_status"] == "eligible":
            assert row["recommended_next_step"] == oracle["recommended_next_step"]
            assert row["total_score"] > 0.0
        elif row["decision_status"] == "blocked":
            assert row["total_score"] == 0.0
        else:
            assert row["recommended_next_step"] == oracle["recommended_next_step"]
            assert row["total_score"] > 0.0


def test_decision_issues_match_oracle() -> None:
    built_output()
    rows = load_tsv(OUTPUT_ROOT / "decision_issues.tsv")
    expected = expected_issue_rows()
    assert [*rows[0].keys()] == contract()["output_contract"]["decision_issues_columns"]
    expected_by_issue = {row["issue_id"]: row for row in expected}
    all_option_ids = {row["option_id"] for row in expected_assessment()}
    selected_option_id = expected_bundle()["selected_option_id"]
    for row in rows:
        oracle = expected_by_issue[row["issue_id"]]
        assert row["category"] == oracle["category"]
        assert row["severity"] == oracle["severity"]
        assert row["evidence_ids"] == oracle["evidence_ids"]
        assert row["required_control"] == oracle["required_control"]
        assert row["owner"] == oracle["owner"]
        assert row["next_review"] == oracle["next_review"]
        actual_ids = set(filter(None, row["linked_option_ids"].split(",")))
        assert actual_ids, f"{row['issue_id']} must link at least one option id"
        assert actual_ids.issubset(all_option_ids)
        assert selected_option_id in actual_ids


def test_assumption_audit_is_complete_and_risk_ranked() -> None:
    built_output()
    rows = load_tsv(OUTPUT_ROOT / "assumption_audit.tsv")
    local_contract = contract()
    expected = assumption_rows_expected()
    assert [*rows[0].keys()] == local_contract["output_contract"]["assumption_audit_columns"]
    assert len(rows) == local_contract["assumption_contract"]["row_count"]
    assert len({row["assumption_id"] for row in rows}) == len(rows)

    expected_issue_ids = {row["linked_issue_id"] for row in expected if row["linked_issue_id"]}
    layers_seen = set()
    types_seen = set()
    control_ids_seen = set()
    issue_ids_seen = set()

    for row in rows:
        fragility = int(row["fragility"])
        impact = int(row["impact"])
        risk_score = int(row["risk_score"])
        assert 1 <= fragility <= 5
        assert 1 <= impact <= 5
        assert risk_score == fragility * impact
        assert row["assumption_statement"].strip()
        assert row["verification_question"].strip()
        assert row["layer"] in local_contract["assumption_contract"]["layers"]
        assert row["assumption_type"] in local_contract["assumption_contract"]["types"]
        layers_seen.add(row["layer"])
        types_seen.add(row["assumption_type"])
        control_ids_seen.add(row["linked_control_id"])
        if row["linked_issue_id"]:
            issue_ids_seen.add(row["linked_issue_id"])

    assert layers_seen == set(local_contract["assumption_contract"]["layers"])
    assert len(types_seen) >= 3
    assert expected_issue_ids.issubset(issue_ids_seen)


def test_safeguard_plan_matches_selected_bundle() -> None:
    built_output()
    payload = read_plan()
    bundle = expected_bundle()
    assert payload["selected_option_id"] == bundle["selected_option_id"]
    controls = payload["controls"]
    assert [item["control_id"] for item in controls] == bundle["required_controls"]
    assert len(payload["monitoring"]) == contract()["assumption_contract"]["top_risk_monitoring_count"]

    audit_rows = load_tsv(OUTPUT_ROOT / "assumption_audit.tsv")
    top_count = contract()["assumption_contract"]["top_risk_monitoring_count"]
    top_rows = sorted(audit_rows, key=lambda row: (-int(row["risk_score"]), row["assumption_id"]))[:top_count]
    expected_questions = {row["verification_question"] for row in top_rows}
    actual_questions = {
        item.get("question", item.get("verification_question", item.get("focus", item.get("check", ""))))
        for item in payload["monitoring"]
    }
    assert actual_questions == expected_questions
    assert payload["manual_checks"], "manual_checks must not be empty"


def test_decision_bundle_matches_oracle() -> None:
    built_output()
    actual = read_bundle()
    expected = expected_bundle()
    assert actual == expected


def test_decision_memo_is_traceable_and_consistent() -> None:
    built_output()
    text = (OUTPUT_ROOT / "decision_memo.md").read_text(encoding="utf-8")
    expected = expected_bundle()
    for heading in contract()["output_contract"]["memo_sections"]:
        assert re.search(rf"(?m)^#{{1,6}}\s+{re.escape(heading)}\s*$", text), f"missing memo heading {heading}"
    assert expected["selected_option_name"] in text
    assert expected["selected_outcome"] in text
    for outcome in expected["rejected_outcomes"]:
        assert outcome in text
    for control_id in expected["required_controls"]:
        assert control_id in text
    for question in expected["open_questions"]:
        assert question in text


def test_outputs_do_not_contain_placeholders() -> None:
    built_output()
    forbidden = ["TODO", "placeholder", "verifier", "dummy text"]
    for name in [
        "decision_memo.md",
        "source_inventory.tsv",
        "option_assessment.tsv",
        "decision_issues.tsv",
        "assumption_audit.tsv",
        "safeguard_plan.yaml",
        "decision_bundle.json",
    ]:
        text = (OUTPUT_ROOT / name).read_text(encoding="utf-8")
        lowered = text.lower()
        for token in forbidden:
            assert token.lower() not in lowered, f"{name} still contains placeholder token: {token}"
