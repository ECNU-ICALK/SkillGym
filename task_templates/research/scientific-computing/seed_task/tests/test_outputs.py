from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

import pandas as pd
from lxml import etree
from pandas.testing import assert_frame_equal

sys.path.insert(0, str(Path(__file__).resolve().parent))
import reference_metrics

OUTPUT = Path(os.environ.get("OUTPUT_DIR", "/root/output"))
WORKSPACE = Path(os.environ.get("WORKSPACE_ROOT", "/root/workspace"))
DATA = Path(os.environ.get("DATA_DIR", "/root/data"))
CODEX_SKILLS_DIR = Path(os.environ.get("CODEX_SKILLS_DIR", "/root/.codex/skills"))


def read_outputs() -> dict[str, object]:
    return {
        "analysis_intake": (OUTPUT / "analysis_intake.md").read_text(encoding="utf-8"),
        "input_summary": pd.read_csv(OUTPUT / "input_summary.tsv", sep="\t"),
        "data_issues": pd.read_csv(OUTPUT / "data_issues.tsv", sep="\t"),
        "daily_merged_panel": pd.read_csv(OUTPUT / "daily_merged_panel.csv", dtype={"station_id": str}),
        "candidate_windows": pd.read_csv(OUTPUT / "candidate_windows.csv"),
    }


def sorted_frame(frame: pd.DataFrame, columns: list[str]) -> pd.DataFrame:
    if frame.empty:
        return frame.copy()
    return frame.sort_values(columns).reset_index(drop=True)


def assert_numeric_series_close(actual: pd.Series, expected: pd.Series, label: str) -> None:
    actual_numeric = pd.to_numeric(actual, errors="coerce")
    expected_numeric = pd.to_numeric(expected, errors="coerce")
    delta = (actual_numeric - expected_numeric).abs()
    matches = delta.le(1e-6) | (actual_numeric.isna() & expected_numeric.isna())
    assert matches.all(), f"{label} max diff {delta.max()}"


def normalize_input_summary_formats(frame: pd.DataFrame) -> pd.DataFrame:
    normalized = frame.copy()

    def canonicalize(value: object) -> object:
        if pd.isna(value):
            return value
        raw = str(value).strip().lower()
        compact = re.sub(r"[^a-z0-9]+", "", raw)
        if "netcdf" in compact:
            return "netcdf"
        if any(token in compact for token in ["stdmet", "plaintexttable", "texttable", "fixedwidthtext", "ndbc"]):
            return "plain_text_table"
        if compact == "json":
            return "json"
        if compact == "xml":
            return "xml"
        return compact

    normalized["format"] = normalized["format"].map(canonicalize)
    return normalized


def canonicalize_primary_descriptor(dataset_name: object, value: object) -> object:
    if pd.isna(value):
        return value
    name = str(dataset_name).strip().lower()
    raw = str(value).strip().lower()
    compact = re.sub(r"[^a-z0-9]+", "", raw)
    if name == "oisst_subset":
        return "oisst_descriptor"
    if name == "buoy_stdmet":
        match = re.search(r"(\d+)\s*(?:parsed\s*)?rows?", raw)
        return f"rows={match.group(1)}" if match else "buoy_descriptor"
    if name == "station_metadata":
        match = re.search(r"(\d+)\s*history", raw)
        return f"histories={match.group(1)}" if match else "metadata_descriptor"
    if name == "screening_contract":
        return "contract_descriptor" if compact else compact
    return compact


def canonicalize_coverage_boundary(dataset_name: object, value: object, boundary: str) -> object:
    name = str(dataset_name).strip().lower()
    if name == "station_metadata" and boundary == "start":
        return "metadata_history_start"
    if name == "station_metadata" and boundary == "end":
        return "open"
    if pd.isna(value):
        return value
    raw = str(value).strip().lower()
    raw = re.sub(r"[t ]\d{2}:\d{2}(:\d{2})?z?$", "", raw)
    raw = raw.rstrip("z")
    if raw in {"nan", "none", ""}:
        return pd.NA
    return raw


def canonicalize_key_variables(dataset_name: object, value: object) -> object:
    if pd.isna(value):
        return value
    name = str(dataset_name).strip().lower()
    compact = re.sub(r"[^a-z0-9]+", "", str(value).strip().lower())
    if name == "oisst_subset":
        return "sst_anom" if "sst" in compact and "anom" in compact else compact
    if name == "buoy_stdmet":
        return "wtmp_wspd" if "wtmp" in compact and "wspd" in compact else compact
    if name == "station_metadata":
        return "history_lat_lng" if "history" in compact and "lat" in compact and "lng" in compact else compact
    if name == "screening_contract":
        has_station = "station" in compact
        has_study_window = "studywindow" in compact
        has_window_rules = "windowrules" in compact
        return "station_study_window_window_rules" if has_station and has_study_window and has_window_rules else compact
    return compact


def normalize_input_summary_values(frame: pd.DataFrame) -> pd.DataFrame:
    normalized = normalize_input_summary_formats(frame)
    normalized["coverage_start"] = [
        canonicalize_coverage_boundary(dataset_name, value, "start")
        for dataset_name, value in zip(normalized["dataset_name"], normalized["coverage_start"], strict=False)
    ]
    normalized["coverage_end"] = [
        canonicalize_coverage_boundary(dataset_name, value, "end")
        for dataset_name, value in zip(normalized["dataset_name"], normalized["coverage_end"], strict=False)
    ]
    normalized["primary_dimensions_or_rows"] = [
        canonicalize_primary_descriptor(dataset_name, value)
        for dataset_name, value in zip(normalized["dataset_name"], normalized["primary_dimensions_or_rows"], strict=False)
    ]
    normalized["key_variables"] = [
        canonicalize_key_variables(dataset_name, value)
        for dataset_name, value in zip(normalized["dataset_name"], normalized["key_variables"], strict=False)
    ]
    return normalized


def canonicalize_path(dataset_name: object, value: object) -> object:
    if pd.isna(value):
        return value
    name = str(dataset_name).strip().lower()
    path = Path(str(value).strip())
    if name == "oisst_subset":
        return f"grids/{path.name}"
    if name == "buoy_stdmet":
        return f"buoys/{path.name}"
    if name == "station_metadata":
        return f"metadata/{path.name}"
    if name == "screening_contract":
        return "contracts/screening_contract.json"
    return path.name


def normalize_input_summary_for_compare(frame: pd.DataFrame) -> pd.DataFrame:
    normalized = normalize_input_summary_values(frame)
    normalized["path"] = [
        canonicalize_path(dataset_name, value)
        for dataset_name, value in zip(normalized["dataset_name"], normalized["path"], strict=False)
    ]
    return normalized


def assert_core_input_selection_matches(actual: pd.DataFrame, expected: pd.DataFrame) -> None:
    columns = ["dataset_name", "path", "coverage_start", "coverage_end"]
    assert_frame_equal(
        sorted_frame(normalize_input_summary_for_compare(actual)[columns], ["dataset_name"]),
        sorted_frame(normalize_input_summary_for_compare(expected)[columns], ["dataset_name"]),
        check_dtype=False,
    )


def run_solver(workspace_root: Path, data_root: Path, output_root: Path) -> None:
    output_root.mkdir(parents=True, exist_ok=True)
    subprocess.run(
        [sys.executable, str(workspace_root / "run_marine_heat_intake.py"), "--data", str(data_root), "--output", str(output_root)],
        check=True,
        timeout=180,
    )


def discover_actual_metadata_path(data_root: Path, station_id: str) -> Path:
    for path in sorted((data_root / "metadata").glob("*.xml")):
        xml_root = etree.parse(str(path))
        stations = xml_root.xpath("//station")
        if stations and stations[0].attrib.get("id") == station_id:
            return path
    raise FileNotFoundError(f"No metadata XML matched station {station_id}")


def obfuscate_candidate_filenames(data_root: Path) -> None:
    rename_plan: list[tuple[Path, Path]] = []
    for folder in ["buoys", "grids", "metadata"]:
        directory = data_root / folder
        for index, path in enumerate(sorted(directory.iterdir()), start=1):
            if not path.is_file():
                continue
            temp_path = directory / f"tmp_{index:02d}{path.suffix}"
            path.rename(temp_path)
            rename_plan.append((temp_path, directory / f"{folder[:-1]}_{index:02d}{path.suffix}"))
    for src, dst in rename_plan:
        src.rename(dst)


def test_required_outputs_exist_and_parse() -> None:
    required = [
        OUTPUT / "analysis_intake.md",
        OUTPUT / "input_summary.tsv",
        OUTPUT / "data_issues.tsv",
        OUTPUT / "daily_merged_panel.csv",
        OUTPUT / "candidate_windows.csv",
    ]
    for path in required:
        assert path.exists(), f"missing required output: {path}"
        assert path.stat().st_size > 0, f"empty required output: {path}"
    outputs = read_outputs()
    assert list(outputs["input_summary"].columns) == reference_metrics.INPUT_SUMMARY_COLUMNS
    assert list(outputs["data_issues"].columns) == reference_metrics.DATA_ISSUE_COLUMNS
    assert list(outputs["daily_merged_panel"].columns) == reference_metrics.DAILY_PANEL_COLUMNS
    assert list(outputs["candidate_windows"].columns) == reference_metrics.CANDIDATE_COLUMNS


def test_bound_skill_is_available_and_unchanged() -> None:
    skill_root = CODEX_SKILLS_DIR / "34__exploratory-data-analysis"
    skill_file = skill_root / "SKILL.md"
    script_file = skill_root / "scripts" / "eda_analyzer.py"
    if not skill_file.exists():
        return
    assert "name: exploratory-data-analysis" in skill_file.read_text(encoding="utf-8")
    assert hashlib.sha256(skill_file.read_bytes()).hexdigest() == "8084fae57c4c3fac0db237113ffb40a98046ef8fb163b9e3119f0c29faf9178c"
    assert hashlib.sha256(script_file.read_bytes()).hexdigest() == "fe1600db3d62bff0c2bc7cf638b4640c3464c2cc8fe1fa4c00bcd0291dca0470"


def test_structured_outputs_match_oracle() -> None:
    expected = reference_metrics.expected_bundle()
    actual = read_outputs()

    assert_frame_equal(
        sorted_frame(normalize_input_summary_for_compare(actual["input_summary"])[["dataset_name", "path", "coverage_start", "coverage_end"]], ["dataset_name"]),
        sorted_frame(normalize_input_summary_for_compare(expected["input_summary"])[["dataset_name", "path", "coverage_start", "coverage_end"]], ["dataset_name"]),
        check_dtype=False,
    )
    allowed_analysis_ready = set(reference_metrics.load_contract()["output_contract"]["analysis_ready_values"])
    actual_analysis_ready = {str(value).strip().lower() for value in actual["input_summary"]["analysis_ready"].dropna().tolist()}
    assert actual_analysis_ready.issubset(allowed_analysis_ready)
    actual_issue_text = " ".join(actual["data_issues"].astype(str).fillna("").agg(" ".join, axis=1)).lower()
    for required_marker in ["wtmp", "grid", "row"]:
        assert required_marker in actual_issue_text, f"missing issue coverage for {required_marker}"
    actual_issue_types = {str(value).strip() for value in actual["data_issues"]["issue_type"].dropna().tolist()}
    required_issue_types = {
        "row_structure_drops",
        "missing_water_temperature_rows",
        "longitude_convention_alignment",
    }
    assert required_issue_types.issubset(actual_issue_types), "issue_type values did not align with the preflight output contract"

    actual_panel = sorted_frame(actual["daily_merged_panel"], ["date"])
    expected_panel = sorted_frame(expected["daily_merged_panel"], ["date"])
    assert_frame_equal(
        actual_panel[["date", "station_id", "station_lat", "station_lon", "grid_lat", "grid_lon", "valid_wtmp_obs", "total_timestamp_rows"]],
        expected_panel[["date", "station_id", "station_lat", "station_lon", "grid_lat", "grid_lon", "valid_wtmp_obs", "total_timestamp_rows"]],
        check_dtype=False,
    )
    for column in ["wtmp_completeness_ratio", "mean_buoy_wtmp_c", "oisst_sst_c", "oisst_anom_c"]:
        assert_numeric_series_close(actual_panel[column], expected_panel[column], column)

    actual_windows = sorted_frame(actual["candidate_windows"], ["rank", "start_date"])
    expected_windows = sorted_frame(expected["candidate_windows"], ["rank", "start_date"])
    assert_frame_equal(
        actual_windows[["rank", "start_date", "end_date", "n_days", "selection_note"]],
        expected_windows[["rank", "start_date", "end_date", "n_days", "selection_note"]],
        check_dtype=False,
    )
    for column in [
        "window_mean_sst_anom_c",
        "window_mean_buoy_wtmp_c",
        "window_min_hour_coverage_ratio",
        "window_min_wtmp_completeness_ratio",
    ]:
        assert_numeric_series_close(actual_windows[column], expected_windows[column], column)


def test_analysis_intake_is_traceable() -> None:
    expected = reference_metrics.expected_bundle()
    actual = read_outputs()["analysis_intake"]
    for heading in reference_metrics.load_contract()["output_contract"]["analysis_intake_headings"]:
        assert re.search(rf"^#{{1,2}} {re.escape(heading)}$", actual, re.MULTILINE)
    selected_paths = expected["input_summary"].set_index("dataset_name")["path"].to_dict()
    for dataset_name in ["oisst_subset", "buoy_stdmet", "station_metadata"]:
        assert Path(selected_paths[dataset_name]).name in actual
    for row in expected["candidate_windows"].itertuples(index=False):
        assert row.start_date in actual
        assert row.end_date in actual


def test_guardrail_contract_mutation_changes_shortlist() -> None:
    tmp_root = Path("/tmp/marine_heat_contract_mutation")
    shutil.rmtree(tmp_root, ignore_errors=True)
    data_copy = tmp_root / "data"
    workspace_copy = tmp_root / "workspace"
    output_copy = tmp_root / "output"
    shutil.copytree(DATA, data_copy)
    shutil.copytree(WORKSPACE, workspace_copy)

    contract_path = data_copy / "contracts" / "screening_contract.json"
    contract = json.loads(contract_path.read_text(encoding="utf-8"))
    contract["window_rules"]["top_k"] = 2
    contract["window_rules"]["min_daily_sst_anom_c"] = 1.2
    contract_path.write_text(json.dumps(contract, indent=2), encoding="utf-8")

    run_solver(workspace_copy, data_copy, output_copy)
    actual = pd.read_csv(output_copy / "candidate_windows.csv")
    expected = reference_metrics.expected_bundle(data_copy)["candidate_windows"]
    assert_frame_equal(sorted_frame(actual, ["rank", "start_date"]), sorted_frame(expected, ["rank", "start_date"]), check_dtype=False)
    assert len(actual) == len(expected)


def test_guardrail_window_switch_chooses_alternate_candidates() -> None:
    tmp_root = Path("/tmp/marine_heat_window_switch")
    shutil.rmtree(tmp_root, ignore_errors=True)
    data_copy = tmp_root / "data"
    workspace_copy = tmp_root / "workspace"
    output_copy = tmp_root / "output"
    shutil.copytree(DATA, data_copy)
    shutil.copytree(WORKSPACE, workspace_copy)

    contract_path = data_copy / "contracts" / "screening_contract.json"
    contract = json.loads(contract_path.read_text(encoding="utf-8"))
    contract["study_window"]["start_date"] = "2024-05-01"
    contract["study_window"]["end_date"] = "2024-05-30"
    contract_path.write_text(json.dumps(contract, indent=2), encoding="utf-8")

    run_solver(workspace_copy, data_copy, output_copy)
    actual_summary = pd.read_csv(output_copy / "input_summary.tsv", sep="\t")
    expected_summary = reference_metrics.expected_bundle(data_copy)["input_summary"]
    assert_core_input_selection_matches(actual_summary, expected_summary)
    selected = actual_summary.set_index("dataset_name")["path"].to_dict()
    assert Path(selected["buoy_stdmet"]).name == "coastal_extract_beta.txt"
    assert Path(selected["oisst_subset"]).name == "thermal_subset_beta.nc"


def test_guardrail_metadata_mutation_changes_grid_mapping() -> None:
    tmp_root = Path("/tmp/marine_heat_metadata_mutation")
    shutil.rmtree(tmp_root, ignore_errors=True)
    data_copy = tmp_root / "data"
    workspace_copy = tmp_root / "workspace"
    output_copy = tmp_root / "output"
    shutil.copytree(DATA, data_copy)
    shutil.copytree(WORKSPACE, workspace_copy)

    contract = reference_metrics.load_contract(data_copy)
    metadata_path = discover_actual_metadata_path(data_copy, contract["station"]["station_id"])
    xml_root = etree.parse(str(metadata_path))
    latest = [history for history in xml_root.xpath("//station/history") if history.attrib.get("stop", "") == ""][0]
    latest.attrib["lat"] = "42.846"
    latest.attrib["lng"] = "-70.151"
    metadata_path.write_bytes(etree.tostring(xml_root, encoding="UTF-8", xml_declaration=True, pretty_print=True))

    run_solver(workspace_copy, data_copy, output_copy)
    actual_panel = pd.read_csv(output_copy / "daily_merged_panel.csv", dtype={"station_id": str})
    expected_panel = reference_metrics.expected_bundle(data_copy)["daily_merged_panel"]
    assert_frame_equal(sorted_frame(actual_panel, ["date"]), sorted_frame(expected_panel, ["date"]), check_dtype=False)
    assert not actual_panel["grid_lat"].equals(read_outputs()["daily_merged_panel"]["grid_lat"])


def test_guardrail_filename_obfuscation_preserves_results() -> None:
    tmp_root = Path("/tmp/marine_heat_filename_obfuscation")
    shutil.rmtree(tmp_root, ignore_errors=True)
    data_copy = tmp_root / "data"
    workspace_copy = tmp_root / "workspace"
    output_copy = tmp_root / "output"
    shutil.copytree(DATA, data_copy)
    shutil.copytree(WORKSPACE, workspace_copy)

    obfuscate_candidate_filenames(data_copy)
    run_solver(workspace_copy, data_copy, output_copy)

    actual_summary = pd.read_csv(output_copy / "input_summary.tsv", sep="\t")
    expected = reference_metrics.expected_bundle(data_copy)
    assert_core_input_selection_matches(actual_summary, expected["input_summary"])
    actual_panel = pd.read_csv(output_copy / "daily_merged_panel.csv", dtype={"station_id": str})
    assert_frame_equal(sorted_frame(actual_panel, ["date"]), sorted_frame(expected["daily_merged_panel"], ["date"]), check_dtype=False)


def test_guardrail_repeated_run_is_deterministic() -> None:
    tmp_root = Path("/tmp/marine_heat_repeatability")
    shutil.rmtree(tmp_root, ignore_errors=True)
    data_copy = tmp_root / "data"
    workspace_copy = tmp_root / "workspace"
    output_a = tmp_root / "output_a"
    output_b = tmp_root / "output_b"
    shutil.copytree(DATA, data_copy)
    shutil.copytree(WORKSPACE, workspace_copy)

    run_solver(workspace_copy, data_copy, output_a)
    run_solver(workspace_copy, data_copy, output_b)

    for name in ["analysis_intake.md", "input_summary.tsv", "data_issues.tsv", "daily_merged_panel.csv", "candidate_windows.csv"]:
        assert (output_a / name).read_bytes() == (output_b / name).read_bytes(), f"{name} is not deterministic"


def test_guardrail_no_external_accounts_or_fixed_candidate_names() -> None:
    solution_code = (WORKSPACE / "run_marine_heat_intake.py").read_text(encoding="utf-8")
    for forbidden in ["OPENAI_API_KEY", "requests.post", "boto3", "google.cloud", "azure.identity"]:
        assert forbidden not in solution_code
    for forbidden_name in [
        "coastal_extract_alpha.txt",
        "coastal_extract_beta.txt",
        "thermal_subset_alpha.nc",
        "thermal_subset_beta.nc",
        "platform_record_alpha.xml",
        "platform_record_beta.xml",
    ]:
        assert forbidden_name not in solution_code
    assert any(
        token in solution_code
        for token in ['glob("*.xml")', "glob('*.xml')", 'glob("*.txt")', "glob('*.txt')", 'glob("*.nc")', "glob('*.nc')"]
    )
