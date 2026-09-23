from __future__ import annotations

import csv
import hashlib
import json
import os
import shutil
import subprocess
from pathlib import Path
from typing import Any

import yaml


TASK_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DATA_ROOT = Path("/root/data")
DEFAULT_WORKSPACE_ROOT = Path("/root/workspace")
DEFAULT_OUTPUT_ROOT = Path("/root/output")

DATA_ROOT = Path(os.environ.get("TASK_DATA_ROOT", DEFAULT_DATA_ROOT))
WORKSPACE_ROOT = Path(os.environ.get("TASK_WORKSPACE_ROOT", DEFAULT_WORKSPACE_ROOT))
OUTPUT_ROOT = Path(os.environ.get("TASK_OUTPUT_ROOT", DEFAULT_OUTPUT_ROOT))
SKILL_ROOT = Path(os.environ.get("TASK_SKILL_ROOT", "/root/.codex/skills/axiom"))

if not DATA_ROOT.exists():
    DATA_ROOT = TASK_ROOT / "environment" / "data"
if not WORKSPACE_ROOT.exists():
    WORKSPACE_ROOT = TASK_ROOT / "environment" / "workspace"
if not OUTPUT_ROOT.parent.exists():
    OUTPUT_ROOT = TASK_ROOT / ".tmp_output"

BUILD_ENTRYPOINT = WORKSPACE_ROOT / "build_decision_packet.py"


def parse_bool(value: Any) -> bool:
    return str(value).strip().lower() in {"1", "true", "yes"}


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line:
            rows.append(json.loads(line))
    return rows


def load_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def load_tsv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle, delimiter="\t"))


def normalize_listing_text(text: str, root: Path) -> str:
    lines: list[str] = []
    root_prefix = f"{root.as_posix().rstrip('/')}/"
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        if "  " not in line:
            lines.append(line)
            continue
        digest, rel = line.split("  ", 1)
        rel = rel.strip()
        if rel.startswith(root_prefix):
            rel = rel[len(root_prefix):]
        if rel.startswith("./"):
            rel = rel[2:]
        lines.append(f"{digest}  {rel}")
    return "\n".join(lines) + ("\n" if lines else "")


def run_build(data_root: Path = DATA_ROOT, output_root: Path = OUTPUT_ROOT) -> subprocess.CompletedProcess[str]:
    if output_root.exists():
        shutil.rmtree(output_root)
    output_root.mkdir(parents=True, exist_ok=True)
    return subprocess.run(
        [
            "python3",
            str(BUILD_ENTRYPOINT),
            "--data",
            str(data_root),
            "--output",
            str(output_root),
        ],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        cwd=WORKSPACE_ROOT,
        check=False,
    )


def built_output() -> Path:
    result = run_build()
    assert result.returncode == 0, f"build failed\nSTDOUT:\n{result.stdout}\nSTDERR:\n{result.stderr}"
    return OUTPUT_ROOT


def contract(data_root: Path = DATA_ROOT) -> dict[str, Any]:
    return load_json(data_root / "policy" / "decision_contract.json")


def brief(data_root: Path = DATA_ROOT) -> dict[str, Any]:
    return load_json(data_root / "brief" / "committee_brief.json")


def options(data_root: Path = DATA_ROOT) -> list[dict[str, str]]:
    return load_csv(data_root / "options" / "deployment_options.csv")


def evidence_index(data_root: Path = DATA_ROOT) -> dict[str, dict[str, Any]]:
    return {row["evidence_id"]: row for row in load_jsonl(data_root / "evidence" / "public_evidence.jsonl")}


def source_inventory_expected() -> list[dict[str, str]]:
    return [
        {
            "source_name": "committee_brief",
            "path": "/root/data/brief/committee_brief.json",
            "source_type": "json",
            "coverage": "board scope and non-negotiables",
            "note": "allowed outcomes and hard constraints"
        },
        {
            "source_name": "deployment_options",
            "path": "/root/data/options/deployment_options.csv",
            "source_type": "csv",
            "coverage": "candidate options",
            "note": "operating characteristics for each option"
        },
        {
            "source_name": "decision_contract",
            "path": "/root/data/policy/decision_contract.json",
            "source_type": "json",
            "coverage": "output contract and scoring rules",
            "note": "controls, columns, and consistency rules"
        },
        {
            "source_name": "policy_clauses",
            "path": "/root/data/policy/policy_clauses.json",
            "source_type": "json",
            "coverage": "governance requirements",
            "note": "policy clauses tied to the packet"
        },
        {
            "source_name": "public_evidence",
            "path": "/root/data/evidence/public_evidence.jsonl",
            "source_type": "jsonl",
            "coverage": "evidence summaries",
            "note": "board-facing evidence pack"
        },
        {
            "source_name": "stakeholder_notes",
            "path": "/root/data/stakeholders",
            "source_type": "directory",
            "coverage": "board, teacher, family, and accessibility notes",
            "note": "stakeholder conditions that the packet must address"
        },
        {
            "source_name": "reference_index",
            "path": "/root/data/reference/source_index.json",
            "source_type": "json",
            "coverage": "public source index",
            "note": "stable source metadata for the local pack"
        }
    ]


def hard_fail_reasons(option: dict[str, str], local_brief: dict[str, Any]) -> list[str]:
    if option["outcome_id"] == "defer_pilot":
        return []
    reasons: list[str] = []
    if int(option["budget_usd"]) > int(local_brief["budget_cap_usd"]):
        reasons.append("budget_cap")
    if int(option["prompt_retention_days"]) > int(local_brief["max_prompt_retention_days"]):
        reasons.append("retention_limit")
    if parse_bool(option["student_data_used_for_model_training"]) != bool(local_brief["non_negotiables"]["student_data_used_for_model_training"]):
        reasons.append("model_training")
    if option["human_review_for_graded_work"] != local_brief["non_negotiables"]["human_review_for_graded_work"]:
        reasons.append("graded_use_review")
    if parse_bool(option["teacher_opt_in_first_semester"]) != bool(local_brief["non_negotiables"]["teacher_opt_in_first_semester"]):
        reasons.append("teacher_opt_in")
    if option["family_notice_plan"] != local_brief["non_negotiables"]["family_notice_plan"]:
        reasons.append("family_notice")
    if parse_bool(option["student_opt_out"]) != bool(local_brief["non_negotiables"]["student_opt_out"]):
        reasons.append("student_opt_out")
    return reasons


def governance_score(option: dict[str, str], local_brief: dict[str, Any]) -> int:
    if option["outcome_id"] == "defer_pilot" or hard_fail_reasons(option, local_brief):
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


def delivery_score(option: dict[str, str], local_brief: dict[str, Any]) -> int:
    if option["outcome_id"] == "defer_pilot" or hard_fail_reasons(option, local_brief):
        return 0
    score = 0
    scope = int(option["scope_schools"])
    training_hours = int(option["teacher_training_hours"])
    if 1 <= scope <= 2:
        score += 3
    if option["multilingual_support_level"] in {"strong", "medium"}:
        score += 2
    if 4 <= training_hours <= 10:
        score += 2
    if option["evaluation_plan"] == "semester_review":
        score += 1
    if parse_bool(option["student_opt_out"]):
        score += 1
    return score


def summarize_option(option: dict[str, str], local_brief: dict[str, Any]) -> dict[str, Any]:
    reasons = hard_fail_reasons(option, local_brief)
    if option["outcome_id"] == "defer_pilot":
        decision_status = "fallback"
    elif reasons:
        decision_status = "blocked"
    else:
        decision_status = "eligible"
    g_score = governance_score(option, local_brief)
    d_score = delivery_score(option, local_brief)
    if decision_status == "fallback":
        total_score = 3.0
    elif decision_status == "blocked":
        total_score = 0.0
    else:
        total_score = round(g_score * 0.6 + d_score * 0.4, 2)
    return {
        "option_id": option["option_id"],
        "outcome_id": option["outcome_id"],
        "decision_status": decision_status,
        "hard_fail_reasons": ",".join(reasons) if reasons else "none",
        "governance_score": g_score,
        "delivery_score": d_score,
        "total_score": total_score,
        "budget_status": "within_cap" if int(option["budget_usd"]) <= int(local_brief["budget_cap_usd"]) else "over_cap",
        "data_status": "compliant" if not parse_bool(option["student_data_used_for_model_training"]) and int(option["prompt_retention_days"]) <= int(local_brief["max_prompt_retention_days"]) else "non_compliant",
        "oversight_status": "ready" if option["human_review_for_graded_work"] == "required" and option["incident_response_playbook"] == "yes" else "gap",
        "recommended_next_step": (
            "prepare_board_packet" if decision_status == "eligible"
            else "reject_for_current_cycle" if decision_status == "blocked"
            else "procurement_readiness_only"
        ),
    }


def expected_assessment(data_root: Path = DATA_ROOT) -> list[dict[str, Any]]:
    local_brief = brief(data_root)
    return [summarize_option(option, local_brief) for option in options(data_root)]


def selected_summary(data_root: Path = DATA_ROOT) -> dict[str, Any]:
    summaries = expected_assessment(data_root)
    eligible = [row for row in summaries if row["decision_status"] == "eligible"]
    if eligible:
        return sorted(eligible, key=lambda row: (-float(row["total_score"]), row["option_id"]))[0]
    return next(row for row in summaries if row["outcome_id"] == "defer_pilot")


def expected_issue_rows(data_root: Path = DATA_ROOT) -> list[dict[str, Any]]:
    payload = contract(data_root)
    selected = selected_summary(data_root)
    option_rows = options(data_root)
    selected_option = next(row for row in option_rows if row["option_id"] == selected["option_id"])
    linked_ids = ",".join(sorted(row["option_id"] for row in option_rows if row["outcome_id"] != "defer_pilot"))
    rows: list[dict[str, Any]] = []
    for rule in payload["issue_rules"]:
        issue_id = rule["issue_id"]
        if selected["outcome_id"] == "defer_pilot":
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
        rows.append(
            {
                "issue_id": issue_id,
                "category": rule["category"],
                "status": status,
                "severity": rule["severity"],
                "linked_option_ids": linked_ids,
                "evidence_ids": ",".join(rule["evidence_ids"]),
                "required_control": rule["required_control"],
                "owner": rule["owner"],
                "next_review": rule["next_review"],
            }
        )
    return rows


def expected_control_ids(data_root: Path = DATA_ROOT) -> list[str]:
    selected = selected_summary(data_root)
    if selected["outcome_id"] == "defer_pilot":
        return []
    return [item["control_id"] for item in contract(data_root)["controls"]]


def expected_bundle(data_root: Path = DATA_ROOT) -> dict[str, Any]:
    selected = selected_summary(data_root)
    all_rows = expected_assessment(data_root)
    option_lookup = {row["option_id"]: row for row in options(data_root)}
    control_ids = expected_control_ids(data_root)
    return {
        "selected_outcome": selected["outcome_id"],
        "selected_option_id": selected["option_id"],
        "selected_option_name": option_lookup[selected["option_id"]]["option_name"],
        "rejected_outcomes": sorted(row["outcome_id"] for row in all_rows if row["outcome_id"] != selected["outcome_id"]),
        "required_controls": control_ids,
        "open_questions": contract(data_root)["open_question_rules"],
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


def assumption_rows_expected(data_root: Path = DATA_ROOT) -> list[dict[str, Any]]:
    local_brief = brief(data_root)
    selected = selected_summary(data_root)
    selected_option = next(row for row in options(data_root) if row["option_id"] == selected["option_id"])
    deployable = selected["outcome_id"] != "defer_pilot"
    data_fragility = 2 if deployable and not parse_bool(selected_option["student_data_used_for_model_training"]) else 4
    oversight_fragility = 2 if selected_option["human_review_for_graded_work"] == local_brief["non_negotiables"]["human_review_for_graded_work"] else 4
    return [
        {
            "assumption_id": "asm_01",
            "layer": "surface",
            "assumption_type": "physical_fact",
            "assumption_statement": "The bounded pilot can stay inside the current board budget without cutting required safeguards.",
            "fragility": 2,
            "impact": 4,
            "risk_score": 8,
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
            "risk_score": data_fragility * 5,
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
            "risk_score": oversight_fragility * 5,
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
            "risk_score": 16,
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
            "risk_score": 12,
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
            "risk_score": 20,
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
            "risk_score": 12,
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
            "risk_score": 16,
            "linked_issue_id": "",
            "linked_control_id": "semester_end_evaluation",
            "verification_question": "Define the semester-end evaluation metrics and reporting date.",
        },
    ]


def read_bundle(output_root: Path = OUTPUT_ROOT) -> dict[str, Any]:
    return load_json(output_root / "decision_bundle.json")


def read_plan(output_root: Path = OUTPUT_ROOT) -> dict[str, Any]:
    return yaml.safe_load((output_root / "safeguard_plan.yaml").read_text(encoding="utf-8"))


def output_listing(root: Path) -> list[str]:
    return sorted(path.name for path in root.iterdir())


def path_exists_readable(path: Path) -> bool:
    try:
        path.stat()
    except (FileNotFoundError, PermissionError):
        return False
    return True


def directory_listing(root: Path) -> str:
    if not root.exists():
        return ""
    lines: list[str] = []
    for path in sorted(p for p in root.rglob("*") if p.is_file()):
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        lines.append(f"{digest}  {path.relative_to(root).as_posix()}")
    return normalize_listing_text("\n".join(lines), root)


def baseline_data_listing() -> str:
    candidate = Path("/opt/task-baselines/data.sha256")
    if candidate.exists():
        return normalize_listing_text(candidate.read_text(encoding="utf-8"), DATA_ROOT)
    return directory_listing(DATA_ROOT)
