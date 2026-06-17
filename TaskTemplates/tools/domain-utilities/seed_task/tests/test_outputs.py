from __future__ import annotations

import csv
import json
import os
from pathlib import Path

import pandas as pd
from pandas.testing import assert_frame_equal

import reference_metrics


OUTPUT_DIR = Path(os.environ.get("OUTPUT_DIR", "/root/output"))
SHORTLIST_PATH = OUTPUT_DIR / "domain_shortlist.json"
AUDIT_PATH = OUTPUT_DIR / "availability_audit.csv"


def load_outputs() -> tuple[dict[str, object], pd.DataFrame]:
    shortlist = json.loads(SHORTLIST_PATH.read_text(encoding="utf-8"))
    audit = pd.read_csv(AUDIT_PATH)
    return shortlist, audit


def test_required_outputs_exist_and_parse() -> None:
    assert SHORTLIST_PATH.exists(), "missing domain_shortlist.json"
    assert AUDIT_PATH.exists(), "missing availability_audit.csv"
    shortlist, audit = load_outputs()
    assert shortlist["project_slug"]
    assert shortlist["evaluated_tlds"]
    assert isinstance(shortlist["shortlist"], list)
    assert isinstance(shortlist["runner_ups"], list)
    assert isinstance(shortlist["rejected_taken_domains"], list)
    assert len(audit) > 0


def test_availability_audit_matches_oracle() -> None:
    _, actual = load_outputs()
    expected = reference_metrics.normalized_audit_frame()
    numeric_columns = [
        "score",
        "brandability",
        "pronounceability",
        "developer_fit",
        "length_bonus",
        "tld_bonus",
    ]
    actual = actual.copy()
    actual[numeric_columns] = actual[numeric_columns].astype(float).round(3)
    actual["style_match_count"] = actual["style_match_count"].astype(int)
    actual = actual[
        [
            "base_name",
            "tld",
            "domain",
            "availability",
            "score",
            "brandability",
            "pronounceability",
            "developer_fit",
            "style_match_count",
            "length_bonus",
            "tld_bonus",
        ]
    ]
    assert_frame_equal(actual.reset_index(drop=True), expected.reset_index(drop=True), check_dtype=False, atol=0.0, rtol=0.0)


def test_shortlist_payload_matches_expected_rankings() -> None:
    actual, _ = load_outputs()
    expected = reference_metrics.expected_shortlist_payload()

    assert actual["project_slug"] == expected["project_slug"]
    assert actual["evaluated_tlds"] == expected["evaluated_tlds"]
    assert actual["runner_ups"] == expected["runner_ups"]
    assert actual["rejected_taken_domains"] == expected["rejected_taken_domains"]
    assert actual["top_pick_summary"].strip()
    assert expected["shortlist"][0]["domain"] in actual["top_pick_summary"]

    actual_shortlist = actual["shortlist"]
    expected_shortlist = expected["shortlist"]
    assert len(actual_shortlist) == len(expected_shortlist) == 6

    seen_bases: set[str] = set()
    for actual_row, expected_row in zip(actual_shortlist, expected_shortlist, strict=True):
        assert actual_row["rank"] == expected_row["rank"]
        assert actual_row["domain"] == expected_row["domain"]
        assert actual_row["base_name"] == expected_row["base_name"]
        assert actual_row["tld"] == expected_row["tld"]
        assert actual_row["availability"] == "available"
        assert round(float(actual_row["score"]), 3) == expected_row["score"]
        assert int(actual_row["length"]) == expected_row["length"]
        assert actual_row["style_tags"] == expected_row["style_tags"]
        assert str(actual_row["why_it_fits"]).strip()
        assert actual_row["base_name"] not in seen_bases
        seen_bases.add(actual_row["base_name"])


def test_runner_ups_and_shortlist_stay_base_unique() -> None:
    shortlist, _ = load_outputs()
    all_domains = [row["domain"] for row in shortlist["shortlist"]] + shortlist["runner_ups"]
    all_bases = [row["base_name"] for row in shortlist["shortlist"]] + [domain.split(".", 1)[0] for domain in shortlist["runner_ups"]]
    assert len(all_domains) == len(set(all_domains))
    assert len(all_bases) == len(set(all_bases))
