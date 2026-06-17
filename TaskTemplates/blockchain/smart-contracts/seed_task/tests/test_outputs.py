from __future__ import annotations

import json
import re
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, "/tests")
import reference_model
from common import OUTPUT_ROOT, TASK_ROOT


def _read_outputs() -> dict[str, object]:
    return {
        "review": (OUTPUT_ROOT / "token_onboarding_review.md").read_text(encoding="utf-8"),
        "decisions": pd.read_csv(OUTPUT_ROOT / "token_decisions.tsv", sep="\t", keep_default_na=False),
        "findings": pd.read_csv(OUTPUT_ROOT / "token_behavior_findings.tsv", sep="\t", keep_default_na=False),
        "coverage": pd.read_csv(OUTPUT_ROOT / "guardrail_coverage.tsv", sep="\t", keep_default_na=False),
        "evidence": json.loads((OUTPUT_ROOT / "evidence_index.json").read_text(encoding="utf-8")),
    }


def _split_multi(value: str) -> list[str]:
    return [item for item in value.split(";") if item]


def _ref_path(ref: str) -> str:
    if "#L" in ref:
        return ref.split("#L", 1)[0]
    return ref.split(":", 1)[0]


def _extract_protocol_file_paths(protocol_files: object) -> set[str]:
    paths: set[str] = set()
    if isinstance(protocol_files, list):
        for item in protocol_files:
            if isinstance(item, dict) and isinstance(item.get("path"), str):
                paths.add(item["path"])
            elif isinstance(item, str):
                paths.add(item)
    elif isinstance(protocol_files, dict):
        for key, item in protocol_files.items():
            if isinstance(item, dict) and isinstance(item.get("path"), str):
                paths.add(item["path"])
            elif isinstance(key, str):
                paths.add(key)
    return paths


def _extract_mapping_rows(node: object) -> dict[str, dict]:
    if isinstance(node, dict):
        return {str(key): value for key, value in node.items() if isinstance(value, dict)}
    if isinstance(node, list):
        rows = {}
        for item in node:
            if not isinstance(item, dict):
                continue
            key = item.get("token_id") or item.get("measure_id")
            if isinstance(key, str):
                rows[key] = item
        return rows
    return {}


def _measure_requirement_map() -> dict[str, str]:
    policy = reference_model.expected_bundle(TASK_ROOT)["policy"]
    return {
        item["requirement"]: item["measure_id"]
        for item in policy["protocol_measures"]
    }


def _normalize_measure_value(value: str) -> str:
    requirement_map = _measure_requirement_map()
    return requirement_map.get(value, value)


def test_required_outputs_exist_and_parse() -> None:
    required = [
        OUTPUT_ROOT / "token_onboarding_review.md",
        OUTPUT_ROOT / "token_decisions.tsv",
        OUTPUT_ROOT / "token_behavior_findings.tsv",
        OUTPUT_ROOT / "guardrail_coverage.tsv",
        OUTPUT_ROOT / "evidence_index.json",
    ]
    for path in required:
        assert path.exists(), f"missing required output: {path}"
        assert path.stat().st_size > 0, f"empty required output: {path}"

    expected = reference_model.expected_bundle(TASK_ROOT)
    actual = _read_outputs()
    assert list(actual["decisions"].columns) == expected["policy"]["output_contract"]["token_decisions_columns"]
    assert list(actual["findings"].columns) == expected["policy"]["output_contract"]["token_behavior_findings_columns"]
    assert list(actual["coverage"].columns) == expected["policy"]["output_contract"]["guardrail_coverage_columns"]


def test_decisions_match_oracle_core() -> None:
    expected = reference_model.expected_bundle(TASK_ROOT)["decisions"].set_index("token_id")
    actual = _read_outputs()["decisions"].set_index("token_id")

    assert list(actual.index) == list(expected.index)
    assert actual["symbol"].to_dict() == expected["symbol"].to_dict()
    assert actual["decision"].to_dict() == expected["decision"].to_dict()
    assert actual["overall_risk"].to_dict() == expected["overall_risk"].to_dict()

    for token_id in expected.index:
        assert _split_multi(actual.at[token_id, "required_protocol_measures"]) == _split_multi(
            expected.at[token_id, "required_protocol_measures"]
        )

        blockers = _split_multi(actual.at[token_id, "blocking_conditions"])
        if expected.at[token_id, "decision"] == "allow":
            assert not blockers
        else:
            assert blockers, f"{token_id} should document at least one blocking condition"

        evidence_refs = _split_multi(actual.at[token_id, "evidence_refs"])
        assert evidence_refs, f"{token_id} should include evidence refs"
        assert any(
            ref.startswith(f"data/token_profiles/{token_id}.json")
            for ref in evidence_refs
        ), f"{token_id} is missing a token profile evidence ref"


def test_findings_match_oracle_core() -> None:
    expected = reference_model.expected_bundle(TASK_ROOT)["findings"]
    actual = _read_outputs()["findings"]
    coverage = _read_outputs()["coverage"].set_index("measure_id")

    expected_requirements = {
        token_id: sorted(_normalize_measure_value(value) for value in group["protocol_requirement"].tolist())
        for token_id, group in expected.groupby("token_id")
    }
    actual_requirements = {
        token_id: sorted(_normalize_measure_value(value) for value in group["protocol_requirement"].tolist())
        for token_id, group in actual.groupby("token_id")
    }
    assert actual_requirements == expected_requirements

    assert actual.groupby(["token_id", "protocol_requirement"]).size().max() == 1
    assert actual["severity"].isin({"info", "low", "medium", "high", "critical"}).all()
    assert actual["integration_impact"].map(lambda value: len(str(value).strip()) >= 20).all()
    assert actual["evidence_refs"].map(lambda value: bool(_split_multi(str(value)))).all()


def test_coverage_matches_oracle_core() -> None:
    expected = reference_model.expected_bundle(TASK_ROOT)["coverage"]
    actual = _read_outputs()["coverage"].set_index("measure_id").sort_index()
    expected = expected.set_index("measure_id").sort_index()

    assert list(actual.index) == list(expected.index)
    assert actual["requirement"].to_dict() == expected["requirement"].to_dict()
    for measure_id, expected_status in expected["coverage_status"].items():
        actual_status = actual.at[measure_id, "coverage_status"]
        if measure_id == "pause_blocklist_runbook":
            assert actual_status in {"missing", "partial"}
        else:
            assert actual_status == expected_status
    assert set(actual["coverage_status"]) == {"supported", "partial", "missing"}

    for measure_id in expected.index:
        assert _split_multi(actual.at[measure_id, "covered_tokens"]) == _split_multi(
            expected.at[measure_id, "covered_tokens"]
        )
        refs = _split_multi(actual.at[measure_id, "protocol_location"])
        if actual.at[measure_id, "coverage_status"] == "missing":
            continue
        assert refs, f"{measure_id} should cite protocol locations when coverage is not missing"
        for ref in refs:
            if not ref.startswith("protocol/"):
                continue
            path = TASK_ROOT / _ref_path(ref)
            assert path.exists(), f"{measure_id} references missing protocol path {ref}"


def test_evidence_index_is_consistent() -> None:
    actual = _read_outputs()["evidence"]
    decisions = _read_outputs()["decisions"].set_index("token_id")
    coverage = _read_outputs()["coverage"].set_index("measure_id")

    for key in ["protocol_files", "candidate_tokens", "decisions", "coverage", "notes"]:
        assert key in actual, f"missing top-level key {key}"

    expected_protocol_paths = {
        f"protocol/contracts/{path.name}"
        for path in sorted((TASK_ROOT / "protocol" / "contracts").glob("*.sol"))
    }
    assert _extract_protocol_file_paths(actual["protocol_files"]) == expected_protocol_paths

    candidate_rows = _extract_mapping_rows(actual["candidate_tokens"])
    assert set(candidate_rows) == set(decisions.index)

    decision_rows = _extract_mapping_rows(actual["decisions"])
    assert set(decision_rows) == set(decisions.index)
    for token_id, row in decision_rows.items():
        if "decision" in row:
            assert row["decision"] == decisions.at[token_id, "decision"]
        if "overall_risk" in row:
            assert row["overall_risk"] == decisions.at[token_id, "overall_risk"]

    coverage_rows = _extract_mapping_rows(actual["coverage"])
    assert set(coverage_rows) == set(coverage.index)
    for measure_id, row in coverage_rows.items():
        if "coverage_status" in row:
            assert row["coverage_status"] == coverage.at[measure_id, "coverage_status"]

    assert actual["notes"], "evidence_index notes should not be empty"


def test_review_markdown_is_traceable() -> None:
    bundle = reference_model.expected_bundle(TASK_ROOT)
    review = _read_outputs()["review"]

    for heading in bundle["policy"]["markdown_headings"]:
        assert re.search(rf"(?m)^#{{1,6}}\s+{re.escape(heading)}\s*$", review), f"missing heading {heading}"

    decisions = bundle["decisions"]
    for row in decisions.itertuples(index=False):
        assert row.symbol in review
        assert row.decision in review

    for measure_id in bundle["coverage"]["measure_id"].tolist():
        assert measure_id in review
