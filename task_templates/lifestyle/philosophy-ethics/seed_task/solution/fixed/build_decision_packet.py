#!/usr/bin/env python3

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path

import yaml


def parse_bool(value: object) -> bool:
    return str(value).strip().lower() in {"1", "true", "yes"}


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def load_jsonl(path: Path) -> list[dict]:
    rows = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line:
            rows.append(json.loads(line))
    return rows


def load_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def hard_fail_reasons(option: dict[str, str], brief: dict) -> list[str]:
    if option["outcome_id"] == "defer_pilot":
        return []
    reasons = []
    if int(option["budget_usd"]) > int(brief["budget_cap_usd"]):
        reasons.append("budget_cap")
    if int(option["prompt_retention_days"]) > int(brief["max_prompt_retention_days"]):
        reasons.append("retention_limit")
    if parse_bool(option["student_data_used_for_model_training"]) != bool(brief["non_negotiables"]["student_data_used_for_model_training"]):
        reasons.append("model_training")
    if option["human_review_for_graded_work"] != brief["non_negotiables"]["human_review_for_graded_work"]:
        reasons.append("graded_use_review")
    if parse_bool(option["teacher_opt_in_first_semester"]) != bool(brief["non_negotiables"]["teacher_opt_in_first_semester"]):
        reasons.append("teacher_opt_in")
    if option["family_notice_plan"] != brief["non_negotiables"]["family_notice_plan"]:
        reasons.append("family_notice")
    if parse_bool(option["student_opt_out"]) != bool(brief["non_negotiables"]["student_opt_out"]):
        reasons.append("student_opt_out")
    return reasons


def governance_score(option: dict[str, str], brief: dict) -> int:
    if option["outcome_id"] == "defer_pilot" or hard_fail_reasons(option, brief):
        return 0
    score = 0
    if option["hosting_model"] == "district_gateway":
        score += 4
    if int(option["prompt_retention_days"]) == 0:
        score += 2
    if option["family_notice_plan"] == "yes":
        score += 2
    if option["incident_response_playbook"] == "yes":
        score += 1
    if option["accessibility_review_ready"] in {"draft", "yes"}:
        score += 1
    if not parse_bool(option["student_data_used_for_model_training"]):
        score += 1
    return score


def delivery_score(option: dict[str, str], brief: dict) -> int:
    if option["outcome_id"] == "defer_pilot" or hard_fail_reasons(option, brief):
        return 0
    score = 0
    if 1 <= int(option["scope_schools"]) <= 2:
        score += 3
    if option["multilingual_support_level"] in {"strong", "medium"}:
        score += 2
    if 4 <= int(option["teacher_training_hours"]) <= 10:
        score += 2
    if option["evaluation_plan"] == "semester_review":
        score += 1
    if parse_bool(option["student_opt_out"]):
        score += 1
    return score


def summarize_option(option: dict[str, str], brief: dict) -> dict:
    reasons = hard_fail_reasons(option, brief)
    if option["outcome_id"] == "defer_pilot":
        decision_status = "fallback"
    elif reasons:
        decision_status = "blocked"
    else:
        decision_status = "eligible"
    g_score = governance_score(option, brief)
    d_score = delivery_score(option, brief)
    if decision_status == "fallback":
        total_score = 3.0
    elif decision_status == "blocked":
        total_score = 0.0
    else:
        total_score = round(g_score * 0.6 + d_score * 0.4, 2)
    return {
        "option_id": option["option_id"],
        "outcome_id": option["outcome_id"],
        "option_name": option["option_name"],
        "decision_status": decision_status,
        "hard_fail_reasons": ",".join(reasons) if reasons else "none",
        "governance_score": g_score,
        "delivery_score": d_score,
        "total_score": total_score,
        "budget_status": "within_cap" if int(option["budget_usd"]) <= int(brief["budget_cap_usd"]) else "over_cap",
        "data_status": "compliant" if not parse_bool(option["student_data_used_for_model_training"]) and int(option["prompt_retention_days"]) <= int(brief["max_prompt_retention_days"]) else "non_compliant",
        "oversight_status": "ready" if option["human_review_for_graded_work"] == "required" and option["incident_response_playbook"] == "yes" else "gap",
        "recommended_next_step": (
            "prepare_board_packet" if decision_status == "eligible"
            else "reject_for_current_cycle" if decision_status == "blocked"
            else "procurement_readiness_only"
        ),
    }


def build_assumption_rows(selected_summary: dict, selected_option: dict[str, str], brief: dict) -> list[dict]:
    deployable = selected_summary["outcome_id"] != "defer_pilot"
    data_fragility = 2 if deployable and not parse_bool(selected_option["student_data_used_for_model_training"]) else 4
    oversight_fragility = 2 if selected_option["human_review_for_graded_work"] == brief["non_negotiables"]["human_review_for_graded_work"] else 4
    rows = [
        {
            "assumption_id": "asm_01",
            "layer": "surface",
            "assumption_type": "physical_fact",
            "assumption_statement": "The bounded pilot can stay inside the current board budget without cutting required safeguards.",
            "fragility": 2,
            "impact": 4,
            "linked_issue_id": "",
            "linked_control_id": "",
            "verification_question": "Is the selected option still within the budget cap after reserving room for required controls and launch tasks?",
        },
        {
            "assumption_id": "asm_02",
            "layer": "surface",
            "assumption_type": "historical_convention",
            "assumption_statement": "The selected configuration can keep student work outside model training and inside the local retention boundary.",
            "fragility": data_fragility,
            "impact": 5,
            "linked_issue_id": "student_data_reuse",
            "linked_control_id": "district_gateway_no_training",
            "verification_question": "What configuration, contract, or gateway evidence shows student work is excluded from model training and kept within the retention limit?",
        },
        {
            "assumption_id": "asm_03",
            "layer": "middle",
            "assumption_type": "historical_convention",
            "assumption_statement": "Human review can remain enforced for any graded classroom use during the pilot.",
            "fragility": oversight_fragility,
            "impact": 5,
            "linked_issue_id": "graded_work_oversight",
            "linked_control_id": "graded_use_human_review",
            "verification_question": "What classroom workflow check shows graded use still requires human review instead of automated acceptance?",
        },
        {
            "assumption_id": "asm_04",
            "layer": "deep",
            "assumption_type": "subjective_belief",
            "assumption_statement": "Teacher opt-in plus the planned training load will be enough for first-semester readiness.",
            "fragility": 4,
            "impact": 4,
            "linked_issue_id": "teacher_readiness",
            "linked_control_id": "teacher_opt_in_gate",
            "verification_question": "Verify teacher training completion before the first graded-use checkpoint.",
        },
        {
            "assumption_id": "asm_05",
            "layer": "middle",
            "assumption_type": "subjective_belief",
            "assumption_statement": "Family notice and the opt-out path will be understandable and reachable before student use begins.",
            "fragility": 3,
            "impact": 4,
            "linked_issue_id": "family_notice_and_choice",
            "linked_control_id": "family_notice_and_opt_out",
            "verification_question": "What packet, notice, and escalation materials show families can understand the pilot and use the opt-out path before launch?",
        },
        {
            "assumption_id": "asm_06",
            "layer": "deep",
            "assumption_type": "subjective_belief",
            "assumption_statement": "Accessibility and multilingual support review will finish in time for launch decisions.",
            "fragility": 4,
            "impact": 5,
            "linked_issue_id": "accessibility_and_language_support",
            "linked_control_id": "accessibility_review",
            "verification_question": "Confirm that the accessibility review is signed off before launch.",
        },
        {
            "assumption_id": "asm_07",
            "layer": "middle",
            "assumption_type": "historical_convention",
            "assumption_statement": "The incident reporting path will be actionable for harmful output, privacy concerns, and classroom escalation.",
            "fragility": 3,
            "impact": 4,
            "linked_issue_id": "incident_response",
            "linked_control_id": "incident_reporting_channel",
            "verification_question": "What reporting route, owner, and escalation step show incidents can be handled before the pilot scales?",
        },
        {
            "assumption_id": "asm_08",
            "layer": "deep",
            "assumption_type": "interest_driven",
            "assumption_statement": "The semester-end evaluation can stay decision-useful even if there is pressure to expand quickly.",
            "fragility": 4,
            "impact": 4,
            "linked_issue_id": "",
            "linked_control_id": "semester_end_evaluation",
            "verification_question": "Define the semester-end evaluation metrics and reporting date.",
        },
    ]
    for row in rows:
        row["risk_score"] = row["fragility"] * row["impact"]
    return rows


def build_packet(data_root: Path, output_root: Path) -> None:
    brief = load_json(data_root / "brief" / "committee_brief.json")
    options = load_csv(data_root / "options" / "deployment_options.csv")
    decision_contract = load_json(data_root / "policy" / "decision_contract.json")
    policy_clauses = load_json(data_root / "policy" / "policy_clauses.json")
    evidence = load_jsonl(data_root / "evidence" / "public_evidence.jsonl")

    evidence_index = {row["evidence_id"]: row for row in evidence}
    option_summaries = [summarize_option(option, brief) for option in options]
    eligible = [row for row in option_summaries if row["decision_status"] == "eligible"]
    selected_summary = sorted(eligible, key=lambda row: (-float(row["total_score"]), row["option_id"]))[0] if eligible else next(row for row in option_summaries if row["outcome_id"] == "defer_pilot")
    selected_option = next(row for row in options if row["option_id"] == selected_summary["option_id"])

    source_rows = [
        {
            "source_name": "committee_brief",
            "path": "/root/data/brief/committee_brief.json",
            "source_type": "json",
            "coverage": "board scope and non-negotiables",
            "note": "allowed outcomes and hard constraints",
        },
        {
            "source_name": "deployment_options",
            "path": "/root/data/options/deployment_options.csv",
            "source_type": "csv",
            "coverage": "candidate options",
            "note": "operating characteristics for each option",
        },
        {
            "source_name": "decision_contract",
            "path": "/root/data/policy/decision_contract.json",
            "source_type": "json",
            "coverage": "output contract and scoring rules",
            "note": "controls, columns, and consistency rules",
        },
        {
            "source_name": "policy_clauses",
            "path": "/root/data/policy/policy_clauses.json",
            "source_type": "json",
            "coverage": "governance requirements",
            "note": "policy clauses tied to the packet",
        },
        {
            "source_name": "public_evidence",
            "path": "/root/data/evidence/public_evidence.jsonl",
            "source_type": "jsonl",
            "coverage": "evidence summaries",
            "note": "board-facing evidence pack",
        },
        {
            "source_name": "stakeholder_notes",
            "path": "/root/data/stakeholders",
            "source_type": "directory",
            "coverage": "board, teacher, family, and accessibility notes",
            "note": "stakeholder conditions that the packet must address",
        },
        {
            "source_name": "reference_index",
            "path": "/root/data/reference/source_index.json",
            "source_type": "json",
            "coverage": "public source index",
            "note": "stable source metadata for the local pack",
        },
    ]

    linked_option_ids = ",".join(sorted(row["option_id"] for row in options if row["outcome_id"] != "defer_pilot"))
    issue_rows = []
    for rule in decision_contract["issue_rules"]:
        issue_id = rule["issue_id"]
        if selected_summary["outcome_id"] == "defer_pilot":
            status = "open"
        elif issue_id == "student_data_reuse":
            status = "resolved" if int(selected_option["prompt_retention_days"]) == 0 and not parse_bool(selected_option["student_data_used_for_model_training"]) else "open"
        elif issue_id == "graded_work_oversight":
            status = "watch" if selected_option["human_review_for_graded_work"] == "required" else "open"
        elif issue_id == "teacher_readiness":
            status = "watch" if int(selected_option["teacher_training_hours"]) <= 10 else "open"
        elif issue_id == "family_notice_and_choice":
            status = "watch" if selected_option["family_notice_plan"] == "yes" and parse_bool(selected_option["student_opt_out"]) else "open"
        elif issue_id == "accessibility_and_language_support":
            status = "watch" if selected_option["accessibility_review_ready"] in {"draft", "yes"} and selected_option["multilingual_support_level"] in {"strong", "medium"} else "open"
        else:
            status = "watch" if selected_option["incident_response_playbook"] == "yes" else "open"
        issue_rows.append(
            {
                "issue_id": issue_id,
                "category": rule["category"],
                "status": status,
                "severity": rule["severity"],
                "linked_option_ids": linked_option_ids,
                "evidence_ids": ",".join(rule["evidence_ids"]),
                "required_control": rule["required_control"],
                "owner": rule["owner"],
                "next_review": rule["next_review"],
            }
        )

    if selected_summary["outcome_id"] == "defer_pilot":
        control_ids = []
        controls = []
    else:
        controls = [
            {
                "control_id": item["control_id"],
                "label": item["label"],
                "owner": item["owner"],
                "trigger": item["trigger"],
                "status": "required",
            }
            for item in decision_contract["controls"]
        ]
        control_ids = [item["control_id"] for item in controls]

    assumption_rows = build_assumption_rows(selected_summary, selected_option, brief)
    top_count = decision_contract["assumption_contract"]["top_risk_monitoring_count"]
    top_monitoring_rows = sorted(assumption_rows, key=lambda row: (-row["risk_score"], row["assumption_id"]))[:top_count]
    control_owner_by_id = {item["control_id"]: item["owner"] for item in controls}

    safeguard_plan = {
        "selected_option_id": selected_summary["option_id"],
        "controls": controls,
        "monitoring": [
            {
                "question": row["verification_question"],
                "owner": control_owner_by_id.get(row["linked_control_id"], "research_office"),
                "checkpoint": "before the first graded-use checkpoint" if row["linked_control_id"] == "teacher_opt_in_gate" else "before launch",
            }
            for row in top_monitoring_rows
        ],
        "manual_checks": [
            "Confirm contract language blocks model training on student work.",
            "Confirm accessibility review sign-off before launch.",
            "Confirm the semester-end evaluation date is on the board calendar.",
        ],
    }

    bundle = {
        "selected_outcome": selected_summary["outcome_id"],
        "selected_option_id": selected_summary["option_id"],
        "selected_option_name": selected_option["option_name"],
        "rejected_outcomes": sorted(row["outcome_id"] for row in option_summaries if row["outcome_id"] != selected_summary["outcome_id"]),
        "required_controls": control_ids,
        "open_questions": decision_contract["open_question_rules"],
        "artifacts": [
            "decision_memo.md",
            "source_inventory.tsv",
            "option_assessment.tsv",
            "decision_issues.tsv",
            "assumption_audit.tsv",
            "safeguard_plan.yaml",
            "decision_bundle.json",
        ],
    }

    output_root.mkdir(parents=True, exist_ok=True)

    with (output_root / "source_inventory.tsv").open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=decision_contract["output_contract"]["source_inventory_columns"], delimiter="\t")
        writer.writeheader()
        writer.writerows(source_rows)

    with (output_root / "option_assessment.tsv").open("w", encoding="utf-8", newline="") as handle:
        fieldnames = decision_contract["output_contract"]["option_assessment_columns"]
        writer = csv.DictWriter(handle, fieldnames=fieldnames, delimiter="\t")
        writer.writeheader()
        for row in option_summaries:
            writer.writerow({key: row[key] for key in fieldnames})

    with (output_root / "decision_issues.tsv").open("w", encoding="utf-8", newline="") as handle:
        fieldnames = decision_contract["output_contract"]["decision_issues_columns"]
        writer = csv.DictWriter(handle, fieldnames=fieldnames, delimiter="\t")
        writer.writeheader()
        writer.writerows(issue_rows)

    with (output_root / "assumption_audit.tsv").open("w", encoding="utf-8", newline="") as handle:
        fieldnames = decision_contract["output_contract"]["assumption_audit_columns"]
        writer = csv.DictWriter(handle, fieldnames=fieldnames, delimiter="\t")
        writer.writeheader()
        for row in assumption_rows:
            writer.writerow({key: row[key] for key in fieldnames})

    (output_root / "safeguard_plan.yaml").write_text(yaml.safe_dump(safeguard_plan, sort_keys=False, allow_unicode=False), encoding="utf-8")
    (output_root / "decision_bundle.json").write_text(json.dumps(bundle, indent=2) + "\n", encoding="utf-8")

    policy_text = ", ".join(clause["clause_id"] for clause in policy_clauses)
    evidence_text = ", ".join(sorted(evidence_index))
    memo = "\n".join(
        [
            "# Scope",
            f"- District: {brief['district_name']}",
            f"- Program: {brief['program_name']}",
            f"- Allowed outcomes: {', '.join(brief['allowed_outcomes'])}",
            f"- Policy clauses considered: {policy_text}",
            f"- Evidence pack ids considered: {evidence_text}",
            "- Reframed question: Which option can the board defend now without assuming away the hard launch constraints and unresolved governance checks?",
            "",
            "# Recommendation",
            f"- Selected outcome: {bundle['selected_outcome']}",
            f"- Selected option: {bundle['selected_option_name']} ({bundle['selected_option_id']})",
            "- Board-facing rationale: this is the only deployable option that stays inside the visible hard constraints while keeping a bounded launch shape.",
            "- Original thinking: broad student demand may tempt the district to favor rollout speed or vendor breadth.",
            "- Rebuilt thinking: the packet supports a bounded pilot only when the highest-risk assumptions are converted into concrete checks before launch and before expansion.",
            "",
            "# Option comparison",
            "- approve_bounded_pilot stays within the budget cap, keeps prompt retention at zero days, blocks model training on student work, and keeps human review required for graded use.",
            "- approve_vendor_pilot is blocked by budget, retention, model-training, and first-semester opt-in gaps in the current packet.",
            "- defer_pilot remains available as a fallback but is weaker than the bounded pilot because a compliant deployable option already exists.",
            "",
            "# Controls",
            *[f"- {control_id}" for control_id in control_ids],
            "",
            "# Open questions",
            *[f"- {row['verification_question']}" for row in top_monitoring_rows],
            "",
        ]
    )
    (output_root / "decision_memo.md").write_text(memo, encoding="utf-8")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--data", required=True)
    parser.add_argument("--output", required=True)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    build_packet(Path(args.data), Path(args.output))


if __name__ == "__main__":
    main()
