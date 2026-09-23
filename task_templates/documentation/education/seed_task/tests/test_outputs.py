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
SOURCE_BUNDLE = Path(os.environ.get("SOURCE_BUNDLE_DIR", "/root/workspace/source_bundle"))
NOTEBOOK_PATH = OUTPUT_DIR / "global_education_tutorial.ipynb"
TABLE_PATH = OUTPUT_DIR / "cohort_indicator_table.csv"
SUMMARY_PATH = OUTPUT_DIR / "lesson_summary.json"
SOURCE_HASH_PATH = Path(os.environ.get("SOURCE_HASH_PATH", "/opt/education-source-bundle.sha256"))

TABLE_COLUMNS = ["entity", "entity_type", "indicator", "year", "value", "unit"]
UNIT_ALIASES = {
    "years": "years",
    "year": "years",
    "percent": "percent",
    "percentage": "percent",
    "percent of gdp": "percent_of_gdp",
    "percent_of_gdp": "percent_of_gdp",
    "% of gdp": "percent_of_gdp",
}


def read_outputs() -> tuple[pd.DataFrame, dict[str, object]]:
    table = pd.read_csv(TABLE_PATH)
    summary = json.loads(SUMMARY_PATH.read_text(encoding="utf-8"))
    return table, summary


def normalize_table(frame: pd.DataFrame) -> pd.DataFrame:
    normalized = frame.copy()
    normalized["year"] = normalized["year"].astype(int)
    normalized["value"] = normalized["value"].astype(float).round(2)
    normalized["unit"] = (
        normalized["unit"]
        .astype(str)
        .str.strip()
        .str.lower()
        .map(lambda value: UNIT_ALIASES.get(value, value))
    )
    return normalized.sort_values(["entity", "indicator", "year"]).reset_index(drop=True)


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def execute_notebook(path: Path) -> nbformat.NotebookNode:
    notebook = nbformat.read(path, as_version=4)
    client = NotebookClient(notebook, timeout=180, kernel_name="python3")
    try:
        client.execute(cwd=str(OUTPUT_DIR))
    except CellExecutionError as exc:  # pragma: no cover - surfaced as assertion text
        raise AssertionError(f"notebook execution failed: {exc}") from exc
    return notebook


def markdown_sources(notebook: nbformat.NotebookNode) -> list[str]:
    return [cell["source"] for cell in notebook.cells if cell.get("cell_type") == "markdown"]


def code_cells(notebook: nbformat.NotebookNode) -> list[nbformat.NotebookNode]:
    return [cell for cell in notebook.cells if cell.get("cell_type") == "code"]


def image_output_count(notebook: nbformat.NotebookNode) -> int:
    total = 0
    for cell in code_cells(notebook):
        for output in cell.get("outputs", []):
            if "image/png" in output.get("data", {}):
                total += 1
    return total


def visual_output_count(notebook: nbformat.NotebookNode) -> int:
    total = 0
    for cell in code_cells(notebook):
        for output in cell.get("outputs", []):
            data = output.get("data", {})
            if any(
                key in data
                for key in [
                    "image/png",
                    "image/svg+xml",
                    "text/html",
                    "application/vnd.plotly.v1+json",
                ]
            ):
                total += 1
    return total


def code_cell_has_text_output(cell: nbformat.NotebookNode) -> bool:
    for output in cell.get("outputs", []):
        if output.get("output_type") == "stream" and str(output.get("text", "")).strip():
            return True
        if output.get("output_type") == "execute_result":
            data = output.get("data", {})
            if any(str(data.get(key, "")).strip() for key in ["text/plain", "text/markdown"]):
                return True
    return False


def code_cell_has_visible_output(cell: nbformat.NotebookNode) -> bool:
    for output in cell.get("outputs", []):
        if output.get("output_type") == "stream" and str(output.get("text", "")).strip():
            return True
        data = output.get("data", {})
        if any(str(data.get(key, "")).strip() for key in ["text/plain", "text/markdown", "text/html"]):
            return True
        if any(key in data for key in ["image/png", "image/svg+xml", "application/vnd.plotly.v1+json"]):
            return True
    return False


def nonempty_code_line_count(cell: nbformat.NotebookNode) -> int:
    return sum(1 for line in cell.get("source", "").splitlines() if line.strip())


def numbered_item_count(source: str) -> int:
    count = 0
    for line in source.splitlines():
        stripped = line.strip()
        if stripped and "." in stripped:
            prefix = stripped.split(".", 1)[0]
            if prefix.isdigit():
                count += 1
    return count


def contains_any_token(source: str, tokens: list[str]) -> bool:
    lowered = source.lower()
    return any(token in lowered for token in tokens)


def first_code_index(notebook: nbformat.NotebookNode) -> int | None:
    for idx, cell in enumerate(notebook.cells):
        if cell.get("cell_type") == "code":
            return idx
    return None


def restore_file(path: Path, backup: Path) -> None:
    if backup.exists():
        shutil.copy2(backup, path)


def summary_evidence_keys(summary: dict[str, object]) -> set[tuple[str, str, int, float]]:
    keys: set[tuple[str, str, int, float]] = set()
    for takeaway in summary["takeaways"]:
        for evidence in takeaway["evidence"]:
            keys.add(
                (
                    evidence["entity"],
                    evidence["indicator"],
                    int(evidence["year"]),
                    round(float(evidence["value"]), 2),
                )
            )
    return keys


def valid_table_keys(table: pd.DataFrame) -> set[tuple[str, str, int, float]]:
    return {
        (row.entity, row.indicator, int(row.year), round(float(row.value), 2))
        for row in table.itertuples(index=False)
    }


def test_required_outputs_exist_and_parse() -> None:
    for path in [NOTEBOOK_PATH, TABLE_PATH, SUMMARY_PATH]:
        assert path.exists(), f"missing required output: {path}"
        assert path.stat().st_size > 0, f"empty required output: {path}"
    table, summary = read_outputs()
    assert list(table.columns) == TABLE_COLUMNS
    assert set(summary) == {
        "lesson_topic",
        "target_audience",
        "latest_common_year",
        "entities_covered",
        "takeaways",
        "caveats",
    }


def test_indicator_table_matches_oracle() -> None:
    actual, _ = read_outputs()
    expected = pd.DataFrame(reference_metrics.table_frame())
    actual = normalize_table(actual)
    expected = normalize_table(expected)
    assert_frame_equal(actual, expected, check_dtype=False, atol=0.0, rtol=0.0)
    assert len(actual) == 90
    assert actual["entity"].tolist() == sorted(actual["entity"].tolist())
    assert set(actual["indicator"]) == set(reference_metrics.INDICATOR_ORDER)
    assert set(actual["year"]) == set(reference_metrics.YEARS)


def test_summary_is_consistent_with_table_and_expected_evidence() -> None:
    table, summary = read_outputs()
    table = normalize_table(table)
    expected = reference_metrics.expected_summary(reference_metrics.table_frame())

    assert summary["lesson_topic"].strip()
    assert summary["target_audience"].strip()
    assert summary["latest_common_year"] == expected["latest_common_year"]
    assert summary["entities_covered"] == expected["entities_covered"]
    assert isinstance(summary["caveats"], list) and len(summary["caveats"]) >= 2
    joined_caveats = " ".join(str(item).lower() for item in summary["caveats"])
    assert any(token in joined_caveats for token in ["gross", "ratio", "share"])
    assert any(
        token in joined_caveats
        for token in ["common year", "latest common year", "shared", "same year", "aligned year", "2022"]
    )

    takeaways = sorted(summary["takeaways"], key=lambda row: row["rank"])
    assert len(takeaways) >= 3
    indicator_coverage: set[str] = set()
    latest_year_takeaway_count = 0
    for idx, takeaway in enumerate(takeaways, start=1):
        assert takeaway["rank"] == idx
        assert isinstance(takeaway["title"], str) and takeaway["title"].strip()
        assert isinstance(takeaway["detail"], str) and takeaway["detail"].strip()
        assert isinstance(takeaway["evidence"], list) and len(takeaway["evidence"]) >= 2
        years = {int(item["year"]) for item in takeaway["evidence"]}
        indicator_coverage.update(str(item["indicator"]) for item in takeaway["evidence"])
        if years == {expected["latest_common_year"]}:
            latest_year_takeaway_count += 1

    assert set(reference_metrics.INDICATOR_ORDER).issubset(indicator_coverage)
    assert latest_year_takeaway_count >= 2

    valid_pairs = valid_table_keys(table)
    for takeaway in takeaways:
        for evidence in takeaway["evidence"]:
            key = (
                evidence["entity"],
                evidence["indicator"],
                int(evidence["year"]),
                round(float(evidence["value"]), 2),
            )
            assert key in valid_pairs, f"summary evidence does not resolve to cohort table: {key}"


def test_notebook_is_valid_executable_and_contains_teaching_sections() -> None:
    notebook = execute_notebook(NOTEBOOK_PATH)
    assert notebook.cells[0]["cell_type"] == "markdown"
    heading_count = sum(
        1
        for source in markdown_sources(notebook)
        for line in source.splitlines()
        if line.lstrip().startswith("#")
    )
    assert heading_count >= 4
    intro_cells = notebook.cells[:4]
    intro_text = "\n\n".join(
        cell.get("source", "")
        for cell in notebook.cells[:6]
        if cell.get("cell_type") == "markdown"
    )
    assert sum(1 for cell in intro_cells if cell.get("cell_type") == "markdown") >= 2
    setup_idx = first_code_index(notebook)
    assert setup_idx is not None and setup_idx <= 3
    first_markdown = notebook.cells[0]["source"]
    setup_source = notebook.cells[setup_idx]["source"]
    assert first_markdown.lstrip().startswith("#")
    assert contains_any_token(
        intro_text,
        ["audience", "target audience", "learner", "participants", "受众", "学员"],
    )
    assert contains_any_token(
        intro_text,
        ["learning goal", "learning goals", "objective", "objectives", "学习目标", "目标"],
    )
    outline_candidates = [
        cell.get("source", "")
        for cell in intro_cells
        if cell.get("cell_type") == "markdown"
    ]
    assert any(numbered_item_count(source) >= 3 for source in outline_candidates)
    outline_sections = [
        source
        for source in outline_candidates
        if any(line.lstrip().startswith("##") for line in source.splitlines())
    ]
    assert any(numbered_item_count(source) >= 3 for source in outline_sections)
    assert "import " in setup_source
    codes = code_cells(notebook)
    assert len(codes) >= 6
    assert any(cell.get("execution_count") for cell in codes)
    assert visual_output_count(notebook) >= 3
    assert max(nonempty_code_line_count(cell) for cell in codes) <= 125
    source_blob = "\n".join(cell["source"] for cell in codes)
    for token in [
        "years_of_schooling.csv",
        "school_enrolment.csv",
        "education_spending.csv",
        "country_cohort.csv",
    ]:
        assert token in source_blob

    image_indices = [
        idx
        for idx, cell in enumerate(notebook.cells)
        if cell.get("cell_type") == "code"
        and any(
            key in output.get("data", {})
            for output in cell.get("outputs", [])
            for key in ["image/png", "image/svg+xml", "text/html", "application/vnd.plotly.v1+json"]
        )
    ]
    assert len(image_indices) >= 3
    for idx in image_indices[:3]:
        assert any(
            idx - offset >= 0 and notebook.cells[idx - offset]["cell_type"] == "markdown"
            for offset in [1, 2]
        )
        assert idx + 1 < len(notebook.cells), "chart cell is missing a follow-up interpretation cell"
        next_cell = notebook.cells[idx + 1]
        assert next_cell["cell_type"] in {"markdown", "code"}
        if next_cell["cell_type"] == "markdown":
            assert next_cell.get("source", "").strip()
        else:
            assert code_cell_has_visible_output(next_cell)

    step_markdown_indices = [
        idx
        for idx, cell in enumerate(notebook.cells)
        if cell.get("cell_type") == "markdown"
        and any(line.lstrip().startswith("##") for line in cell.get("source", "").splitlines())
    ]
    assert len(step_markdown_indices) >= 5
    paired_steps = 0
    for idx in step_markdown_indices:
        if idx + 1 < len(notebook.cells) and notebook.cells[idx + 1].get("cell_type") == "code":
            paired_steps += 1
    assert paired_steps >= 5

    exercise_indices = [
        idx
        for idx, cell in enumerate(notebook.cells)
        if cell.get("cell_type") == "markdown"
        and contains_any_token(
            cell.get("source", ""),
            ["exercise", "practice", "check-in", "your turn", "try it yourself", "练习", "实践"],
        )
    ]
    assert exercise_indices, "notebook is missing a learner practice section"
    assert any(
        idx + 1 < len(notebook.cells) and notebook.cells[idx + 1].get("cell_type") == "code"
        for idx in exercise_indices
    ), "practice section must be followed by a starter code cell"


def test_notebook_recreates_csv_and_json_outputs() -> None:
    table_backup = Path("/tmp/education_table_backup.csv")
    summary_backup = Path("/tmp/education_summary_backup.json")
    shutil.copy2(TABLE_PATH, table_backup)
    shutil.copy2(SUMMARY_PATH, summary_backup)
    original_table = pd.read_csv(table_backup)
    original_summary = json.loads(summary_backup.read_text(encoding="utf-8"))

    TABLE_PATH.unlink()
    SUMMARY_PATH.unlink()

    notebook = execute_notebook(NOTEBOOK_PATH)
    assert TABLE_PATH.exists(), "notebook did not recreate cohort_indicator_table.csv"
    assert SUMMARY_PATH.exists(), "notebook did not recreate lesson_summary.json"

    regenerated_table = pd.read_csv(TABLE_PATH)
    regenerated_summary = json.loads(SUMMARY_PATH.read_text(encoding="utf-8"))
    assert_frame_equal(
        normalize_table(regenerated_table),
        normalize_table(original_table),
        check_dtype=False,
        atol=0.0,
        rtol=0.0,
    )
    assert regenerated_summary == original_summary
    assert visual_output_count(notebook) >= 3


def test_mutating_source_data_changes_regenerated_outputs() -> None:
    spending_path = SOURCE_BUNDLE / "education_spending.csv"
    spending_backup = Path("/tmp/education_spending_backup.csv")
    table_backup = Path("/tmp/education_table_before_mutation.csv")
    summary_backup = Path("/tmp/education_summary_before_mutation.json")
    shutil.copy2(spending_path, spending_backup)
    shutil.copy2(TABLE_PATH, table_backup)
    shutil.copy2(SUMMARY_PATH, summary_backup)

    try:
        rows = list(pd.read_csv(spending_path).to_dict(orient="records"))
        changed = False
        for row in rows:
            if row["country_code"] == "IDN" and int(row["fiscal_year"]) == 2022:
                row["education_spending_pct_gdp"] = 9.86
                changed = True
                break
        assert changed, "failed to locate the mutation target in education_spending.csv"
        pd.DataFrame(rows).to_csv(spending_path, index=False)

        TABLE_PATH.unlink()
        SUMMARY_PATH.unlink()
        execute_notebook(NOTEBOOK_PATH)

        mutated_table = normalize_table(pd.read_csv(TABLE_PATH))
        mutated_summary = json.loads(SUMMARY_PATH.read_text(encoding="utf-8"))
        mutated_value = mutated_table.loc[
            (mutated_table["entity"] == "Indonesia")
            & (mutated_table["indicator"] == "education_spending_pct_gdp")
            & (mutated_table["year"] == 2022),
            "value",
        ].iloc[0]
        assert round(float(mutated_value), 2) == 9.86
        assert digest(TABLE_PATH) != digest(table_backup)

        valid_pairs = valid_table_keys(mutated_table)
        for key in summary_evidence_keys(mutated_summary):
            assert key in valid_pairs

        referenced_mutated_row = [
            key
            for key in summary_evidence_keys(mutated_summary)
            if key[:3] == ("Indonesia", "education_spending_pct_gdp", 2022)
        ]
        for key in referenced_mutated_row:
            assert key[3] == 9.86
    finally:
        restore_file(spending_path, spending_backup)
        restore_file(TABLE_PATH, table_backup)
        restore_file(SUMMARY_PATH, summary_backup)


def test_input_bundle_is_unchanged() -> None:
    if not SOURCE_HASH_PATH.exists():
        return
    current_source = os.popen(
        f"find {SOURCE_BUNDLE} -type f -print0 | sort -z | xargs -0 sha256sum"
    ).read()
    assert current_source == SOURCE_HASH_PATH.read_text(encoding="utf-8")
