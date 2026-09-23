from __future__ import annotations

from pathlib import Path

from common import (
    BATCH_PATH,
    REGISTER_FIELDS,
    REGISTER_PATH,
    REVIEW_PATH,
    build_expected,
    load_batch_payload,
    load_policy,
    load_register_rows,
    same_vendor_alias,
    slugify,
)


def test_required_output_files_exist() -> None:
    assert REGISTER_PATH.exists(), "Missing /root/output/invoice_register.csv"
    assert BATCH_PATH.exists(), "Missing /root/output/payment_batch.json"
    assert REVIEW_PATH.exists(), "Missing /root/output/batch_review.md"


def test_invoice_register_matches_expected_rows() -> None:
    expected = build_expected()
    actual_rows = load_register_rows()
    assert len(actual_rows) == len(expected["register_rows"]), "Unexpected number of invoice register rows"
    actual_by_source = {row["source_file"]: row for row in actual_rows}
    expected_by_source = {row["source_file"]: row for row in expected["register_rows"]}
    assert set(actual_by_source) == set(expected_by_source), "Register source_file values do not match the live review scope"

    for source_file, expected_row in expected_by_source.items():
        actual_row = actual_by_source[source_file]
        assert list(actual_row.keys()) == REGISTER_FIELDS, f"CSV header mismatch for {source_file}"
        for field in ["document_type", "vendor_name_canonical", "invoice_date", "due_date", "currency", "expense_category", "payment_status", "exclusion_reason"]:
            assert actual_row[field] == expected_row[field], f"{source_file} field {field} mismatch"
        if expected_row["exclusion_reason"] == "manual_review_required":
            assert actual_row["invoice_number"].strip(), f"{source_file} invoice_number missing"
        else:
            assert actual_row["invoice_number"] == expected_row["invoice_number"], f"{source_file} invoice_number mismatch"
        assert same_vendor_alias(actual_row["vendor_name_observed"], expected_row["vendor_name_canonical"]), (
            f"{source_file} vendor_name_observed does not map to {expected_row['vendor_name_canonical']}"
        )
        if expected_row["tax_amount"] == "":
            assert actual_row["tax_amount"] in {"", "0.00"}, f"{source_file} tax_amount mismatch"
        else:
            assert actual_row["tax_amount"] == expected_row["tax_amount"], f"{source_file} tax_amount mismatch"
        assert actual_row["total_amount"] == expected_row["total_amount"], f"{source_file} total_amount mismatch"
        assert actual_row["eligible_for_batch"].lower() == str(expected_row["eligible_for_batch"]).lower(), f"{source_file} eligible flag mismatch"
        _assert_organized_path_semantics(source_file, actual_row, expected_row)


def _assert_organized_path_semantics(source_file: str, actual_row: dict, expected_row: dict) -> None:
    policy = load_policy()
    actual_path = actual_row["organized_relative_path"]
    expected_path = expected_row["organized_relative_path"]
    expected_parts = Path(expected_path).parts
    actual_parts = Path(actual_path).parts
    assert len(actual_parts) >= 4, f"{source_file} organized_relative_path too short"
    assert actual_parts[:3] == expected_parts[:3], f"{source_file} organized_relative_path directory mismatch"
    assert Path(actual_path).suffix == Path(expected_path).suffix, f"{source_file} organized_relative_path extension mismatch"
    if actual_row["exclusion_reason"] != "duplicate_document":
        assert actual_path == expected_path, f"{source_file} organized_relative_path mismatch"
        return
    filename = Path(actual_path).name
    expected_name = Path(expected_path).name
    reference = actual_row["invoice_number"] or policy["reference_fallback"]
    reference_sanitized = slugify(reference, lowercase=False, uppercase=True)
    assert reference_sanitized in filename, f"{source_file} duplicate filename missing sanitized reference"
    assert filename.startswith(expected_name.rsplit(".", 1)[0]), f"{source_file} duplicate filename does not preserve base naming"


def test_payment_batch_matches_recomputed_values() -> None:
    expected = build_expected()["batch_payload"]
    actual = load_batch_payload()
    assert actual["batch_id"] == expected["batch_id"]
    assert actual["cutoff_date"] == expected["cutoff_date"]
    assert actual["service_checks"] == expected["service_checks"], "service_checks mismatch"
    assert actual["currency_totals"] == expected["currency_totals"], "currency_totals mismatch"

    assert actual["payable_documents"] == expected["payable_documents"], "payable_documents mismatch"

    actual_excluded = {item["source_file"]: item for item in actual["excluded_documents"]}
    expected_excluded = {item["source_file"]: item for item in expected["excluded_documents"]}
    assert set(actual_excluded) == set(expected_excluded), "excluded_documents coverage mismatch"
    for source_file, expected_item in expected_excluded.items():
        actual_item = actual_excluded[source_file]
        assert actual_item["reason"] == expected_item["reason"], f"{source_file} exclusion reason mismatch"
        assert isinstance(actual_item["note"], str) and actual_item["note"].strip(), f"{source_file} exclusion note missing"

    assert isinstance(actual["notes"], list) and len(actual["notes"]) >= 2


def test_batch_review_contains_required_facts() -> None:
    expected = build_expected()
    payload = expected["batch_payload"]
    text = REVIEW_PATH.read_text(encoding="utf-8")
    lowered = text.lower()

    assert expected["batch"]["batch_id"] in text
    assert str(len(expected["register_rows"])) in text
    assert str(len(payload["payable_documents"])) in text
    for item in payload["excluded_documents"]:
        assert item["source_file"] in text, f"batch_review.md missing excluded document {item['source_file']}"
    assert any(token in lowered or token in text for token in ["manual review", "manual_review_required", "人工复核"])
    assert any(token in lowered or token in text for token in ["duplicate", "duplicate_document", "重复"])
    for total in payload["currency_totals"]:
        assert total["currency"] in text, f"batch_review.md missing currency {total['currency']}"
