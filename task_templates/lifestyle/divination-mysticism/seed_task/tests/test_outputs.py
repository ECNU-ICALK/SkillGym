from __future__ import annotations

from pathlib import Path

from test_helpers import (
    ARCHIVE_NATIVE_HEADER,
    AUDIT_PATH,
    CCAL_HEADER,
    EVIDENCE_DIR,
    REPORT_PATH,
    RESOLUTION_PATH,
    SCHEDULE_PATH,
    catalog,
    evidence_rows,
    expected_selection,
    load_json,
    resolve_candidates,
)


def test_required_outputs_exist() -> None:
    assert SCHEDULE_PATH.exists(), "observance_schedule.json is missing"
    assert RESOLUTION_PATH.exists(), "date_resolution.json is missing"
    assert AUDIT_PATH.exists(), "source_audit.json is missing"
    assert REPORT_PATH.exists(), "selection_report.md is missing"
    assert EVIDENCE_DIR.exists() and EVIDENCE_DIR.is_dir(), "evidence directory is missing"


def test_date_resolution_contract_and_values() -> None:
    resolved = resolve_candidates()
    payload = load_json(RESOLUTION_PATH)
    for key in ["year", "resolutions", "dataset_summary", "cross_checks"]:
        assert key in payload, f"date_resolution missing {key}"
    assert payload["year"] == 2026
    records = {entry["observance_id"]: entry for entry in payload["resolutions"]}
    assert len(records) == len(catalog())
    assert sorted(records) == sorted(item["observance_id"] for item in catalog())
    for observance_id, expected in resolved.items():
        entry = records[observance_id]
        assert entry["lunar_rule"] == expected["lunar_rule"]
        assert entry["gregorian_date"] == expected["gregorian_date"]
        assert entry["weekday"] == expected["weekday"]
        assert entry["resolution_status"], f"{observance_id} resolution_status is empty"
        assert entry["cross_check_status"], f"{observance_id} cross_check_status is empty"


def test_selected_schedule_matches_expected_solution() -> None:
    payload = load_json(SCHEDULE_PATH)
    for key in ["program_name", "year", "selected_observances", "rejected_observances", "policy_summary", "open_questions"]:
        assert key in payload, f"observance_schedule missing {key}"
    assert payload["year"] == 2026
    expected = expected_selection()
    selected = payload["selected_observances"]
    assert len(selected) == 4
    assert [item["observance_id"] for item in selected] == [item["observance_id"] for item in expected]
    for actual, wanted in zip(selected, expected):
        assert actual["title"] == wanted["title"]
        assert actual["lunar_rule"] == wanted["lunar_rule"]
        assert actual["gregorian_date"] == wanted["gregorian_date"]
        assert actual["weekday"] == wanted["weekday"]
        assert actual["audience_tag"] == wanted["audience_tag"]
        assert actual["format"] == wanted["format"]
        assert actual["evidence_id"] == f"{wanted['observance_id']}.tsv"
    rejected_ids = sorted(item["observance_id"] for item in payload["rejected_observances"])
    expected_rejected = sorted(
        item["observance_id"] for item in resolve_candidates().values() if item["observance_id"] not in {entry["observance_id"] for entry in expected}
    )
    assert rejected_ids == expected_rejected
    assert isinstance(payload["open_questions"], list) and payload["open_questions"], "open_questions is empty"


def test_evidence_files_match_selected_rows() -> None:
    resolved = resolve_candidates()
    selected_ids = [item["observance_id"] for item in expected_selection()]
    rows = evidence_rows()
    assert sorted(rows) == sorted(selected_ids), "Evidence files do not match the selected observances"
    accepted_headers = {"\t".join(CCAL_HEADER), ARCHIVE_NATIVE_HEADER}
    for observance_id in selected_ids:
        lines = rows[observance_id]
        assert len(lines) == 2, f"{observance_id} evidence file must contain header and one data row"
        header = lines[0]
        if header not in accepted_headers:
            cols = header.split("\t")
            assert len(cols) == len(CCAL_HEADER), f"{observance_id} evidence header has unexpected column count"
            assert cols[0] in {"gregorian_date", "Date"}, f"{observance_id} evidence header has unexpected first column"
            assert cols[-1] in {"ji", "Ji"}, f"{observance_id} evidence header has unexpected last column"
        assert lines[1] == resolved[observance_id]["source_row"]


def test_source_audit_contract_and_consistency() -> None:
    audit = load_json(AUDIT_PATH)
    for key in ["source_checked", "sources_used", "evidence_records", "notes"]:
        assert key in audit, f"source_audit missing {key}"
    assert audit["source_checked"] is True
    assert isinstance(audit["sources_used"], list) and audit["sources_used"], "sources_used is empty"
    expected_ids = [item["observance_id"] for item in expected_selection()]
    assert sorted(Path(name).stem for name in audit["evidence_records"]) == sorted(expected_ids)


def test_cross_file_consistency() -> None:
    schedule = load_json(SCHEDULE_PATH)
    resolution = load_json(RESOLUTION_PATH)
    resolution_by_id = {item["observance_id"]: item for item in resolution["resolutions"]}
    for entry in schedule["selected_observances"]:
        resolved = resolution_by_id[entry["observance_id"]]
        assert entry["gregorian_date"] == resolved["gregorian_date"]
        assert entry["weekday"] == resolved["weekday"]


def test_report_structure_and_order() -> None:
    text = REPORT_PATH.read_text(encoding="utf-8")
    first_line = text.splitlines()[0].strip()
    assert first_line, "selection_report first line is empty"
    expected_titles = [item["title"] for item in expected_selection()]
    positions = []
    for title in expected_titles:
        header = f"## {title}"
        assert header in text, f"selection_report missing section {header}"
        positions.append(text.index(header))
    assert positions == sorted(positions), "selection_report sections are not in chronological order"
