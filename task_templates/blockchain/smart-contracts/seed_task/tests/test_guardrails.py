from __future__ import annotations

import json
import os
import sys

import pandas as pd

sys.path.insert(0, "/tests")
from common import (
    DATA_HASH_PATH,
    DATA_ROOT,
    OUTPUT_ROOT,
    PIPELINE_ROOT,
    SKILL_ROOT,
    TASK_ROOT,
    output_bytes_map,
    run_review,
    run_review_in_temp,
    sha256sum_style_listing,
)


def test_input_data_is_unchanged() -> None:
    if DATA_HASH_PATH.exists():
        assert sha256sum_style_listing(DATA_ROOT) == DATA_HASH_PATH.read_text(encoding="utf-8")


def test_bound_skill_signature_is_present_when_installed() -> None:
    skill_path = SKILL_ROOT / "SKILL.md"
    if not skill_path.exists():
        return
    content = skill_path.read_text(encoding="utf-8")
    assert "name: token-integration-analyzer" in content
    assert "Trail of Bits' token integration checklist" in content
    assert "weird token patterns" in content


def test_pipeline_source_mentions_policy_and_profiles() -> None:
    joined = "\n".join(path.read_text(encoding="utf-8", errors="ignore") for path in PIPELINE_ROOT.rglob("*.py"))
    assert "listing_policy.json" in joined or "load_policy" in joined
    assert "token_profiles" in joined or "load_token_profiles" in joined


def test_rerun_is_deterministic() -> None:
    first, task_copy, output_root = run_review_in_temp()
    assert first.returncode == 0, f"first run failed\nstdout:\n{first.stdout}\nstderr:\n{first.stderr}"
    first_map = output_bytes_map(output_root)

    second = run_review(task_root=task_copy, output_root=output_root)
    assert second.returncode == 0, f"second run failed\nstdout:\n{second.stdout}\nstderr:\n{second.stderr}"
    second_map = output_bytes_map(output_root)

    assert first_map == second_map


def test_policy_mutation_changes_decision() -> None:
    policy = json.loads((TASK_ROOT / "data" / "listing_policy.json").read_text(encoding="utf-8"))
    policy["overall_risk_by_decision"]["allow_with_conditions"] = "high"

    result, _, output_root = run_review_in_temp(policy_override=policy)
    assert result.returncode == 0, f"mutated run failed\nstdout:\n{result.stdout}\nstderr:\n{result.stderr}"

    decisions = pd.read_csv(output_root / "token_decisions.tsv", sep="\t")
    wbtc_row = decisions.loc[decisions["token_id"] == "wbtc"].iloc[0]
    assert wbtc_row["overall_risk"] == "high"


def test_decisions_require_analysis_not_static_files() -> None:
    result, _, output_root = run_review_in_temp()
    assert result.returncode == 0, f"temp run failed\nstdout:\n{result.stdout}\nstderr:\n{result.stderr}"

    decisions = pd.read_csv(output_root / "token_decisions.tsv", sep="\t").set_index("token_id")
    coverage = pd.read_csv(output_root / "guardrail_coverage.tsv", sep="\t").set_index("measure_id")

    assert decisions.loc["ampl", "decision"] == "reject"
    assert decisions.loc["usdc", "decision"] == "review_required"
    assert decisions.loc["sta", "decision"] == "allow_with_conditions"
    assert coverage.loc["share_price_recalc", "coverage_status"] == "missing"
    assert coverage.loc["upgrade_watch", "coverage_status"] == "partial"
