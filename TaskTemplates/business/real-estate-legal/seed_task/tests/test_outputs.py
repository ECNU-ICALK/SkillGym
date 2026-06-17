from __future__ import annotations

import csv
import json
import os
import urllib.parse
import urllib.request
from pathlib import Path


DATA_DIR = Path(os.environ.get("DATA_DIR", "/root/data"))
OUTPUT_DIR = Path(os.environ.get("OUTPUT_DIR", "/root/output"))
MANIFEST = json.loads((DATA_DIR / "job_manifest.json").read_text(encoding="utf-8"))
SERVICE_URLS = MANIFEST["service_urls"]
PAGE_LIMIT = 3

NOTICE_FIELDS = [
    "asset_id",
    "edital_id",
    "item_number",
    "auction_type",
    "auctioneer_name",
    "auctioneer_registry",
    "first_auction_at",
    "second_auction_at",
    "appraisal_value_brl",
    "first_min_bid_brl",
    "second_min_bid_brl",
    "payment_mode",
    "fgts_allowed",
    "financing_allowed",
    "address",
    "city",
    "state",
    "registry_office",
    "property_registry_number",
    "private_area_m2",
    "total_area_m2",
    "taxes_responsibility",
    "condo_responsibility",
    "encumbrance_notes",
    "regularization_notes",
    "publication_at",
]

CASH_FIELDS = [
    "asset_id",
    "pricing_basis",
    "min_bid_brl",
    "auctioneer_fee_brl",
    "itbi_rate_pct",
    "itbi_brl",
    "registry_cost_brl",
    "modeled_tax_debts_brl",
    "modeled_condo_debts_brl",
    "modeled_regularization_brl",
    "total_cash_out_brl",
    "cash_only_flag",
    "financing_flag",
    "fgts_flag",
]


def round2(value: float) -> float:
    return round(float(value) + 1e-9, 2)


def get_json(url: str) -> dict:
    req = urllib.request.Request(url, headers={"X-Client": "verifier-main"})
    with urllib.request.urlopen(req, timeout=10) as resp:
        return json.loads(resp.read().decode("utf-8"))


def paginate(url: str) -> list[dict]:
    items: list[dict] = []
    cursor: str | None = None
    while True:
        params = {"limit": str(PAGE_LIMIT)}
        if cursor is not None:
            params["cursor"] = cursor
        payload = get_json(f"{url}?{urllib.parse.urlencode(params)}")
        items.extend(payload["items"])
        cursor = payload["page_info"]["next_cursor"]
        if cursor is None:
            return items


def expected_asset() -> dict:
    return get_json(SERVICE_URLS["asset_current"])


def expected_cost_model() -> dict:
    return get_json(SERVICE_URLS["cost_model_current"])


def expected_risk_rows() -> list[dict]:
    return paginate(SERVICE_URLS["risk_signals"])


def expected_policy() -> dict:
    return get_json(SERVICE_URLS["decision_policy_current"])


def expected_recommendation() -> str:
    policy = expected_policy()
    cash = expected_cost_model()
    risk_rows = expected_risk_rows()
    high_count = sum(row["risk_level"] == "high" for row in risk_rows)
    if float(cash["total_cash_out_brl"]) > float(policy["budget_cap_brl"]):
        return "NO_BID"
    if high_count <= int(policy["max_high_risks_for_bid"]):
        return "BID"
    if high_count <= int(policy["max_high_risks_for_watch_only"]):
        return "WATCH_ONLY"
    return "NO_BID"


def load_json_output(name: str) -> dict:
    return json.loads((OUTPUT_DIR / name).read_text(encoding="utf-8"))


def load_csv_output(name: str) -> list[dict]:
    with (OUTPUT_DIR / name).open(newline="", encoding="utf-8") as fh:
        return list(csv.DictReader(fh))


def test_required_output_files_exist() -> None:
    for filename in ["notice_extract.json", "risk_register.csv", "cash_requirements.json", "investment_committee_memo.md"]:
        assert (OUTPUT_DIR / filename).exists(), f"Missing required output file: {filename}"


def test_notice_extract_matches_authority_record() -> None:
    payload = load_json_output("notice_extract.json")
    expected = expected_asset()
    assert list(payload.keys()) == NOTICE_FIELDS, "notice_extract.json fields do not match the required schema"
    for key in NOTICE_FIELDS:
        if key == "payment_mode":
            assert payload[key] == expected[key]
            continue
        if isinstance(expected[key], bool):
            assert payload[key] is expected[key], f"Incorrect boolean value for {key}"
            continue
        if isinstance(expected[key], (int, float)):
            assert isinstance(payload[key], (int, float)), f"{key} must be numeric"
            assert abs(float(payload[key]) - round2(expected[key])) <= 0.01, f"Incorrect value for {key}"
            assert round(float(payload[key]), 2) == float(payload[key]), f"{key} must keep 2 decimals"
            continue
        assert payload[key] == expected[key], f"Incorrect value for {key}"


def test_risk_register_matches_full_live_risk_set() -> None:
    rows = load_csv_output("risk_register.csv")
    expected_rows = expected_risk_rows()
    assert rows, "risk_register.csv is empty"
    assert list(rows[0].keys()) == ["risk_code", "risk_title", "risk_level", "evidence_source", "summary"]
    assert len(rows) == len(expected_rows), f"Expected {len(expected_rows)} risk rows, got {len(rows)}"
    by_code = {row["risk_code"]: row for row in rows}
    assert set(by_code) == {row["risk_code"] for row in expected_rows}
    for expected in expected_rows:
        row = by_code[expected["risk_code"]]
        assert row["risk_title"] == expected["risk_title"]
        assert row["risk_level"] == expected["risk_level"]
        assert row["evidence_source"] == expected["evidence_source"]
        assert row["summary"] == expected["summary"]


def test_cash_requirements_match_live_cost_model() -> None:
    payload = load_json_output("cash_requirements.json")
    expected = expected_cost_model()
    assert list(payload.keys()) == CASH_FIELDS, "cash_requirements.json fields do not match the required schema"
    for key in CASH_FIELDS:
        if isinstance(expected[key], bool):
            assert payload[key] is expected[key], f"Incorrect boolean value for {key}"
            continue
        if isinstance(expected[key], (int, float)):
            assert isinstance(payload[key], (int, float)), f"{key} must be numeric"
            assert abs(float(payload[key]) - round2(expected[key])) <= 0.01, f"Incorrect value for {key}"
            assert round(float(payload[key]), 2) == float(payload[key]), f"{key} must keep 2 decimals"
            continue
        assert payload[key] == expected[key], f"Incorrect value for {key}"

    recomputed_total = round2(
        payload["min_bid_brl"]
        + payload["auctioneer_fee_brl"]
        + payload["itbi_brl"]
        + payload["registry_cost_brl"]
        + payload["modeled_tax_debts_brl"]
        + payload["modeled_condo_debts_brl"]
        + payload["modeled_regularization_brl"]
    )
    assert abs(recomputed_total - float(payload["total_cash_out_brl"])) <= 0.01, "total_cash_out_brl does not equal the component sum"


def test_memo_is_consistent_with_outputs() -> None:
    memo = (OUTPUT_DIR / "investment_committee_memo.md").read_text(encoding="utf-8")
    asset = expected_asset()
    cash = expected_cost_model()
    recommendation = expected_recommendation()
    for heading in [
        "# Executive Summary",
        "# Auction Facts",
        "# Risks",
        "# Cash Requirement",
        "# Recommendation",
    ]:
        assert heading in memo, f"Missing heading: {heading}"

    assert asset["asset_id"] in memo
    assert asset["edital_id"] in memo
    assert f"R$ {round2(cash['total_cash_out_brl']):.2f}" in memo
    assert f"R$ {round2(cash['min_bid_brl']):.2f}" in memo
    assert recommendation in memo
    assert "regularization" in memo.lower()
    assert "cash" in memo.lower()
