from __future__ import annotations

import hashlib
import json
import os
import shutil
from pathlib import Path

import nbformat
import pandas as pd
from nbclient import NotebookClient
from nbclient.exceptions import CellExecutionError
from pandas.testing import assert_frame_equal

import reference_metrics


OUTPUT_DIR = Path(os.environ.get("OUTPUT_DIR", "/root/output"))
DATA_DIR = Path(os.environ.get("DATA_DIR", "/root/data"))
NOTEBOOK_PATH = OUTPUT_DIR / "egfr_bioactivity_review.ipynb"
PANEL_PATH = OUTPUT_DIR / "candidate_panel.csv"
QC_PATH = OUTPUT_DIR / "qc_summary.json"
BRIEF_PATH = OUTPUT_DIR / "review_brief.md"
SCENARIO_PATH = OUTPUT_DIR / "scenario_comparison.csv"
TRACE_PATH = OUTPUT_DIR / "candidate_trace.json"
AUDIT_PATH = OUTPUT_DIR / "filter_audit.csv"
PLOT_PATH = OUTPUT_DIR / "top_candidate_best_ic50_nm.png"
DATA_HASH_PATH = Path(os.environ.get("DATA_HASH_PATH", "/opt/lab-tools-data.sha256"))
SKILL_HASH_PATH = Path(os.environ.get("SKILL_HASH_PATH", "/opt/lab-tools-skill.sha256"))

PANEL_COLUMNS = [
    "rank",
    "molecule_chembl_id",
    "pref_name",
    "n_qualifying_measurements",
    "n_distinct_assays",
    "best_ic50_nM",
    "median_ic50_nM",
    "best_pchembl",
    "max_assay_confidence_score",
    "selection_reason",
]

SCENARIO_COLUMNS = [
    "scenario_id",
    "minimum_confidence_score",
    "minimum_distinct_assays",
    "qualifying_rows",
    "eligible_molecules",
    "panel_size",
    "top_3_ids",
]

AUDIT_COLUMNS = [
    "activity_id",
    "molecule_chembl_id",
    "assay_chembl_id",
    "passes_standard_type",
    "passes_relation",
    "passes_nonnull_value",
    "passes_validity",
    "passes_assay_type",
    "passes_confidence",
    "final_included",
    "exclusion_reason",
]


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read_outputs() -> tuple[pd.DataFrame, dict[str, object], str, pd.DataFrame, dict[str, object], pd.DataFrame]:
    panel = pd.read_csv(PANEL_PATH)
    qc = json.loads(QC_PATH.read_text(encoding="utf-8"))
    brief = BRIEF_PATH.read_text(encoding="utf-8")
    scenarios = pd.read_csv(SCENARIO_PATH)
    trace = json.loads(TRACE_PATH.read_text(encoding="utf-8"))
    audit = pd.read_csv(AUDIT_PATH)
    return panel, qc, brief, scenarios, trace, audit


def normalize_panel(frame: pd.DataFrame) -> pd.DataFrame:
    normalized = frame.copy()
    normalized["rank"] = normalized["rank"].astype(int)
    normalized["n_qualifying_measurements"] = normalized["n_qualifying_measurements"].astype(int)
    normalized["n_distinct_assays"] = normalized["n_distinct_assays"].astype(int)
    normalized["best_ic50_nM"] = normalized["best_ic50_nM"].astype(float).round(3)
    normalized["median_ic50_nM"] = normalized["median_ic50_nM"].astype(float).round(3)
    normalized["best_pchembl"] = normalized["best_pchembl"].astype(float).round(2)
    normalized["max_assay_confidence_score"] = normalized["max_assay_confidence_score"].astype(int)
    normalized["pref_name"] = normalized["pref_name"].fillna("").astype(str)
    normalized["selection_reason"] = normalized["selection_reason"].astype(str)
    return normalized.reset_index(drop=True)


def normalize_scenarios(frame: pd.DataFrame) -> pd.DataFrame:
    normalized = frame.copy()
    for column in [
        "minimum_confidence_score",
        "minimum_distinct_assays",
        "qualifying_rows",
        "eligible_molecules",
        "panel_size",
    ]:
        normalized[column] = normalized[column].astype(int)
    normalized["scenario_id"] = normalized["scenario_id"].astype(str)
    normalized["top_3_ids"] = normalized["top_3_ids"].fillna("").astype(str)
    return normalized.reset_index(drop=True)


def normalize_audit(frame: pd.DataFrame) -> pd.DataFrame:
    normalized = frame.copy()
    normalized["activity_id"] = normalized["activity_id"].astype(int)
    normalized["molecule_chembl_id"] = normalized["molecule_chembl_id"].astype(str)
    normalized["assay_chembl_id"] = normalized["assay_chembl_id"].astype(str)
    for column in [
        "passes_standard_type",
        "passes_relation",
        "passes_nonnull_value",
        "passes_validity",
        "passes_assay_type",
        "passes_confidence",
        "final_included",
    ]:
        normalized[column] = normalized[column].astype(bool)
    normalized["exclusion_reason"] = normalized["exclusion_reason"].astype(str)
    return normalized.reset_index(drop=True)[AUDIT_COLUMNS]


def execute_notebook(path: Path) -> nbformat.NotebookNode:
    notebook = nbformat.read(path, as_version=4)
    client = NotebookClient(notebook, timeout=180, kernel_name="python3")
    try:
        client.execute(cwd=str(OUTPUT_DIR))
    except CellExecutionError as exc:  # pragma: no cover
        raise AssertionError(f"notebook execution failed: {exc}") from exc
    return notebook


def markdown_sources(notebook: nbformat.NotebookNode) -> list[str]:
    return [cell["source"] for cell in notebook.cells if cell.get("cell_type") == "markdown"]


def markdown_headings(notebook: nbformat.NotebookNode) -> list[str]:
    headings = []
    for source in markdown_sources(notebook):
        for line in source.splitlines():
            stripped = line.strip()
            if stripped.startswith("#"):
                headings.append(stripped)
    return headings


def code_cells(notebook: nbformat.NotebookNode) -> list[nbformat.NotebookNode]:
    return [cell for cell in notebook.cells if cell.get("cell_type") == "code"]


def visual_output_count(notebook: nbformat.NotebookNode) -> int:
    total = 0
    for cell in code_cells(notebook):
        for output in cell.get("outputs", []):
            data = output.get("data", {})
            if any(key in data for key in ["image/png", "image/svg+xml", "text/html"]):
                total += 1
    return total


def restore_file(path: Path, backup: Path) -> None:
    if backup.exists():
        shutil.copy2(backup, path)


def test_required_outputs_exist_and_parse() -> None:
    for path in [NOTEBOOK_PATH, PANEL_PATH, QC_PATH, BRIEF_PATH, SCENARIO_PATH, TRACE_PATH, AUDIT_PATH]:
        assert path.exists(), f"missing required output: {path}"
        assert path.stat().st_size > 0, f"empty required output: {path}"
    panel, qc, _, scenarios, trace, audit = read_outputs()
    assert list(panel.columns) == PANEL_COLUMNS
    assert set(qc) == {
        "target_chembl_id",
        "target_name",
        "activity_rows_loaded",
        "activity_rows_after_filters",
        "assay_rows_used",
        "molecules_ranked",
        "candidate_rows",
    }
    assert list(scenarios.columns) == SCENARIO_COLUMNS
    assert set(trace) == {"target_chembl_id", "scenario_id", "panel_size", "candidates"}
    assert list(audit.columns)[: len(AUDIT_COLUMNS)] == AUDIT_COLUMNS


def test_candidate_panel_matches_oracle() -> None:
    actual, _, _, _, _, _ = read_outputs()
    expected = pd.DataFrame(reference_metrics.candidate_panel_rows())
    actual = normalize_panel(actual)
    expected = normalize_panel(expected[PANEL_COLUMNS])
    actual["pref_name"] = actual.apply(
        lambda row: row["pref_name"] or row["molecule_chembl_id"],
        axis=1,
    )
    assert_frame_equal(actual, expected, check_dtype=False, atol=0.0, rtol=0.0)
    assert len(actual) == 10
    assert actual["rank"].tolist() == list(range(1, 11))


def test_qc_summary_matches_oracle() -> None:
    _, actual, _, _, _, _ = read_outputs()
    expected = reference_metrics.qc_summary()
    assert actual == expected


def test_scenario_comparison_matches_oracle() -> None:
    _, _, _, actual, _, _ = read_outputs()
    expected = pd.DataFrame(reference_metrics.scenario_comparison_rows())
    actual = normalize_scenarios(actual)
    expected = normalize_scenarios(expected[SCENARIO_COLUMNS])
    assert_frame_equal(actual, expected, check_dtype=False, atol=0.0, rtol=0.0)
    assert actual["scenario_id"].tolist() == [
        "baseline_contract",
        "strict_confidence",
        "relaxed_assay_support",
    ]


def test_candidate_trace_matches_oracle() -> None:
    _, _, _, _, actual, _ = read_outputs()
    expected = reference_metrics.candidate_trace()
    assert actual["target_chembl_id"] == expected["target_chembl_id"]
    assert actual["scenario_id"] == expected["scenario_id"]
    assert int(actual["panel_size"]) == int(expected["panel_size"])
    assert len(actual["candidates"]) == len(expected["candidates"])
    for actual_row, expected_row in zip(actual["candidates"], expected["candidates"], strict=True):
        for key, value in expected_row.items():
            actual_value = actual_row.get(key)
            if actual_value is None and key == "qualifying_measurement_count":
                actual_value = actual_row.get("n_qualifying_measurements")
            if actual_value is None and key == "triggered_selection_rule":
                actual_value = actual_row.get("selection_reason")
            if key in {"best_ic50_nM", "median_ic50_nM"}:
                assert round(float(actual_value), 3) == round(float(value), 3)
                continue
            assert actual_value == value
    assert len(actual["candidates"]) == int(actual["panel_size"]) == 10


def test_filter_audit_matches_oracle() -> None:
    _, _, _, _, _, actual = read_outputs()
    expected = pd.DataFrame(reference_metrics.filter_audit_rows())
    actual = normalize_audit(actual)
    expected = normalize_audit(expected[AUDIT_COLUMNS])
    assert_frame_equal(
        actual.drop(columns=["exclusion_reason"]),
        expected.drop(columns=["exclusion_reason"]),
        check_dtype=False,
        atol=0.0,
        rtol=0.0,
    )
    assert len(actual) == 300
    assert actual["final_included"].sum() == reference_metrics.qc_summary()["activity_rows_after_filters"]
    raw_actual = pd.read_csv(AUDIT_PATH)
    source_rows = {
        int(row["activity_id"]): row
        for row in reference_metrics.load_activities()
    }
    for row in raw_actual.itertuples(index=False):
        reason = str(row.exclusion_reason)
        source = source_rows[int(row.activity_id)]
        if bool(row.final_included):
            assert reason == "included"
            continue
        assert reason
        if not bool(row.passes_standard_type):
            assert str(source.get("standard_type")) in reason
        if not bool(row.passes_relation):
            assert str(source.get("standard_relation")) in reason
        if not bool(row.passes_nonnull_value):
            assert any(token in reason.lower() for token in ["missing", "null"])
        if not bool(row.passes_validity):
            comment = str(source.get("data_validity_comment"))
            assert comment in reason


def test_review_brief_is_consistent() -> None:
    panel, qc, brief, scenarios, trace, _ = read_outputs()
    headings = ["# Scope", "# Data Quality", "# Candidate Panel", "# Follow-up Notes"]
    last_index = -1
    for heading in headings:
        index = brief.find(heading)
        assert index >= 0, f"missing heading: {heading}"
        assert index > last_index, f"heading out of order: {heading}"
        last_index = index

    assert qc["target_name"] in brief or str(qc["target_chembl_id"]) in brief
    assert str(qc["activity_rows_after_filters"]) in brief
    assert str(qc["candidate_rows"]) in brief

    top_ids = panel["molecule_chembl_id"].astype(str).head(3).tolist()
    for molecule_id in top_ids:
        assert molecule_id in brief, f"brief missing top candidate id: {molecule_id}"

    for token in ["baseline", "strict", "relaxed"]:
        assert token in brief.lower()

    for candidate in trace["candidates"][:2]:
        assert candidate["triggered_selection_rule"] in brief

    assert any(
        token in brief.lower()
        for token in ["legacy_shortlist.csv", "legacy shortlist", "prior export"]
    )
    assert any(token in brief.lower() for token in ["confidence", "assay", "filter", "scenario"])


def test_notebook_is_valid_executable_and_contains_analysis_evidence() -> None:
    notebook = execute_notebook(NOTEBOOK_PATH)
    assert notebook.cells[0]["cell_type"] == "markdown"
    headings = markdown_headings(notebook)
    for heading in ["# Goal", "# Inputs", "# Results", "## Plan", "## Follow-up"]:
        assert heading in headings

    markdown_text = "\n".join(markdown_sources(notebook)).lower()
    for token in ["hypothesis", "variables", "metrics", "baseline", "scenario"]:
        assert token in markdown_text

    code = code_cells(notebook)
    assert len(code) >= 5
    assert visual_output_count(notebook) >= 1

    combined_code = "\n".join(cell.get("source", "") for cell in code).lower()
    for token in [
        "screening_contract",
        "candidate_panel.csv",
        "qc_summary.json",
        "review_brief.md",
        "scenario_comparison.csv",
        "candidate_trace.json",
        "filter_audit.csv",
    ]:
        assert token in combined_code
    for token in ["baseline_contract", "strict_confidence", "relaxed_assay_support", "confidence", "ic50", "assay"]:
        assert token in combined_code


def test_notebook_rerun_recreates_deliverables() -> None:
    backups = {}
    for path in [PANEL_PATH, QC_PATH, BRIEF_PATH, SCENARIO_PATH, TRACE_PATH, AUDIT_PATH, PLOT_PATH]:
        if path.exists():
            backup = path.with_suffix(path.suffix + ".bak")
            shutil.copy2(path, backup)
            backups[path] = backup
            path.unlink()

    try:
        execute_notebook(NOTEBOOK_PATH)
        for path in [PANEL_PATH, QC_PATH, BRIEF_PATH, SCENARIO_PATH, TRACE_PATH, AUDIT_PATH, PLOT_PATH]:
            assert path.exists(), f"notebook did not recreate {path.name}"
            assert path.stat().st_size > 0
    finally:
        for path, backup in backups.items():
            restore_file(path, backup)
            backup.unlink(missing_ok=True)


def test_outputs_do_not_follow_legacy_shortlist() -> None:
    panel, _, _, _, _, _ = read_outputs()
    panel_ids = panel["molecule_chembl_id"].astype(str).tolist()
    legacy_ids = reference_metrics.legacy_shortlist_ids()
    assert panel_ids != legacy_ids
    assert len(set(panel_ids) - set(legacy_ids)) >= 2


def test_exported_plot_exists() -> None:
    assert PLOT_PATH.exists(), "missing exported plot: top_candidate_best_ic50_nm.png"
    assert PLOT_PATH.stat().st_size > 0


def test_no_scaffolding_helper_left_behind() -> None:
    forbidden = [
        Path("/root/build_egfr_review.py"),
        Path("/root/build_egfr_review_notebook.py"),
        Path("/root/tmp/build_egfr_review.py"),
        Path("/root/tmp/build_egfr_review_notebook.py"),
    ]
    for path in forbidden:
        try:
            exists = path.exists()
        except PermissionError:
            continue
        assert not exists, f"helper file should be removed: {path}"


def test_mutating_source_snapshot_changes_rerun_results() -> None:
    source_path = DATA_DIR / "egfr_activity_snapshot.json"
    backup_path = source_path.with_suffix(".json.bak")
    original_panel = pd.read_csv(PANEL_PATH)
    original_qc = json.loads(QC_PATH.read_text(encoding="utf-8"))
    original_scenarios = pd.read_csv(SCENARIO_PATH)
    shutil.copy2(source_path, backup_path)

    try:
        payload = json.loads(source_path.read_text(encoding="utf-8"))
        rows = payload["rows"]
        target_molecule_id = str(original_panel.iloc[0]["molecule_chembl_id"])
        mutated = 0
        for row in rows:
            if row.get("molecule_chembl_id") == target_molecule_id and row.get("standard_relation") == "=":
                row["standard_relation"] = ">"
                mutated += 1
                if mutated == 2:
                    break
        assert mutated >= 1, "expected to mutate at least one qualifying row"
        source_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        execute_notebook(NOTEBOOK_PATH)
        mutated_panel = pd.read_csv(PANEL_PATH)
        mutated_qc = json.loads(QC_PATH.read_text(encoding="utf-8"))
        mutated_scenarios = pd.read_csv(SCENARIO_PATH)
        assert not normalize_panel(mutated_panel).equals(normalize_panel(original_panel))
        assert mutated_qc["activity_rows_after_filters"] < original_qc["activity_rows_after_filters"]
        assert not normalize_scenarios(mutated_scenarios).equals(normalize_scenarios(original_scenarios))
    finally:
        restore_file(source_path, backup_path)
        backup_path.unlink(missing_ok=True)
        execute_notebook(NOTEBOOK_PATH)


def test_mutating_contract_changes_rerun_results() -> None:
    contract_path = DATA_DIR / "screening_contract.json"
    backup_path = contract_path.with_suffix(".json.bak")
    original_panel = pd.read_csv(PANEL_PATH)
    original_scenarios = pd.read_csv(SCENARIO_PATH)
    shutil.copy2(contract_path, backup_path)

    try:
        contract = json.loads(contract_path.read_text(encoding="utf-8"))
        contract["activity_filters"]["minimum_confidence_score"] = int(
            contract["activity_filters"]["minimum_confidence_score"]
        ) + 1
        contract_path.write_text(json.dumps(contract, indent=2), encoding="utf-8")
        execute_notebook(NOTEBOOK_PATH)
        mutated_panel = pd.read_csv(PANEL_PATH)
        mutated_scenarios = pd.read_csv(SCENARIO_PATH)
        assert not normalize_scenarios(mutated_scenarios).equals(normalize_scenarios(original_scenarios))
        baseline_row = normalize_scenarios(mutated_scenarios).iloc[0]
        assert int(baseline_row["minimum_confidence_score"]) == 9
        assert int(baseline_row["qualifying_rows"]) < int(normalize_scenarios(original_scenarios).iloc[0]["qualifying_rows"])
        assert not normalize_panel(mutated_panel).equals(normalize_panel(original_panel))
    finally:
        restore_file(contract_path, backup_path)
        backup_path.unlink(missing_ok=True)
        execute_notebook(NOTEBOOK_PATH)


def test_data_and_skill_payloads_unchanged() -> None:
    expected_data_hashes = {}
    for line in DATA_HASH_PATH.read_text(encoding="utf-8").splitlines():
        digest_value, path = line.split("  ", 1)
        expected_data_hashes[path] = digest_value
    for path, expected_digest in expected_data_hashes.items():
        assert digest(Path(path)) == expected_digest, f"data file changed: {path}"

    if SKILL_HASH_PATH.exists():
        expected_skill_hashes = {}
        for line in SKILL_HASH_PATH.read_text(encoding="utf-8").splitlines():
            digest_value, path = line.split("  ", 1)
            expected_skill_hashes[path] = digest_value
        for path, expected_digest in expected_skill_hashes.items():
            assert digest(Path(path)) == expected_digest, f"skill file changed: {path}"


def test_output_whitelist() -> None:
    expected = {
        "egfr_bioactivity_review.ipynb",
        "candidate_panel.csv",
        "qc_summary.json",
        "review_brief.md",
        "scenario_comparison.csv",
        "candidate_trace.json",
        "filter_audit.csv",
        "top_candidate_best_ic50_nm.png",
    }
    actual = {path.name for path in OUTPUT_DIR.iterdir() if path.is_file()}
    assert expected.issubset(actual)
