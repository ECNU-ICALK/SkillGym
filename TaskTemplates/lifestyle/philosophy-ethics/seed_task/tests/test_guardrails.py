from __future__ import annotations

import json
import shutil
from pathlib import Path

from conftest import (
    DATA_ROOT,
    OUTPUT_ROOT,
    SKILL_ROOT,
    WORKSPACE_ROOT,
    baseline_data_listing,
    built_output,
    directory_listing,
    output_listing,
    path_exists_readable,
    read_bundle,
    run_build,
)


def test_output_whitelist_and_stable_rerun() -> None:
    built_output()
    expected_names = [
        "assumption_audit.tsv",
        "decision_bundle.json",
        "decision_issues.tsv",
        "decision_memo.md",
        "option_assessment.tsv",
        "safeguard_plan.yaml",
        "source_inventory.tsv",
    ]
    assert output_listing(OUTPUT_ROOT) == expected_names
    first_bundle = (OUTPUT_ROOT / "decision_bundle.json").read_text(encoding="utf-8")
    first_memo = (OUTPUT_ROOT / "decision_memo.md").read_text(encoding="utf-8")
    rerun = run_build()
    assert rerun.returncode == 0, rerun.stderr
    assert (OUTPUT_ROOT / "decision_bundle.json").read_text(encoding="utf-8") == first_bundle
    assert (OUTPUT_ROOT / "decision_memo.md").read_text(encoding="utf-8") == first_memo


def test_inputs_are_unchanged() -> None:
    built_output()
    assert directory_listing(DATA_ROOT) == baseline_data_listing()


def test_solver_reads_core_inputs_and_build_script() -> None:
    source_files = list(WORKSPACE_ROOT.rglob("*.py")) + list(WORKSPACE_ROOT.rglob("*.sh"))
    joined = "\n".join(path.read_text(encoding="utf-8", errors="ignore") for path in source_files)
    for token in [
        "committee_brief.json",
        "deployment_options.csv",
        "decision_contract.json",
        "public_evidence.jsonl",
        "policy_clauses.json",
    ]:
        assert token in joined, f"build logic does not appear to read {token}"


def test_budget_mutation_changes_selected_outcome() -> None:
    tmp_root = Path("/tmp/philosophy_ethics_budget_mutation")
    if tmp_root.exists():
        shutil.rmtree(tmp_root)
    shutil.copytree(DATA_ROOT, tmp_root)
    brief_path = tmp_root / "brief" / "committee_brief.json"
    brief = json.loads(brief_path.read_text(encoding="utf-8"))
    brief["budget_cap_usd"] = 80000
    brief_path.write_text(json.dumps(brief, indent=2) + "\n", encoding="utf-8")

    mutated_output = Path("/tmp/philosophy_ethics_budget_output")
    result = run_build(data_root=tmp_root, output_root=mutated_output)
    assert result.returncode == 0, result.stderr
    selected = json.loads((mutated_output / "decision_bundle.json").read_text(encoding="utf-8"))
    assert selected["selected_outcome"] == "defer_pilot"
    assert selected["selected_option_id"] == "defer_and_procure"


def test_optional_skill_consultation_signal_if_logs_exist() -> None:
    agent_log = Path("/logs/agent/codex.txt")
    trajectory_log = Path("/logs/agent/trajectory.json")
    skill_md = Path("/logs/agent/skills/axiom/SKILL.md")
    if not agent_log.exists() or not skill_md.exists():
        return
    text = agent_log.read_text(encoding="utf-8", errors="ignore")
    if "/logs/agent/skills/axiom/SKILL.md" in text or "/root/.codex/skills/axiom/SKILL.md" in text:
        return
    if trajectory_log.exists():
        trajectory_text = trajectory_log.read_text(encoding="utf-8", errors="ignore")
        if "/logs/agent/skills/axiom/SKILL.md" in trajectory_text or "/root/.codex/skills/axiom/SKILL.md" in trajectory_text:
            return
