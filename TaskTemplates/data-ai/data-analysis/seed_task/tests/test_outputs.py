from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path

import pandas as pd
from pandas.testing import assert_frame_equal

sys.path.insert(0, "/tests")
import reference_metrics

OUTPUT = Path("/root/output")
WORKSPACE = Path("/root/workspace")
DATA = Path("/root/data")

SOURCE_COLUMNS = reference_metrics.SOURCE_COLUMNS
QUALITY_COLUMNS = reference_metrics.QUALITY_COLUMNS
SUMMARY_COLUMNS = reference_metrics.SUMMARY_COLUMNS
WEATHER_COLUMNS = reference_metrics.WEATHER_COLUMNS
RANKING_COLUMNS = reference_metrics.RANKING_COLUMNS


def sorted_frame(frame: pd.DataFrame, sort_columns: list[str]) -> pd.DataFrame:
    return frame.sort_values(sort_columns).reset_index(drop=True)


def normalize_effect_direction(frame: pd.DataFrame) -> pd.DataFrame:
    normalized = frame.copy()
    if "effect_direction" in normalized.columns:
        normalized["effect_direction"] = normalized["effect_direction"].replace(
            {
                "higher_than_dry": "higher",
                "lower_than_dry": "lower",
                "same_as_dry": "no_change",
            }
        )
    return normalized


def assert_with_tolerance(
    actual: pd.Series,
    expected: pd.Series,
    *,
    atol: float,
    label: str,
) -> None:
    delta = (pd.to_numeric(actual, errors="coerce") - pd.to_numeric(expected, errors="coerce")).abs()
    assert delta.le(atol).all(), f"{label} exceeds tolerance {atol}; max diff={delta.max()}"


def read_outputs() -> dict[str, object]:
    return {
        "analysis_brief": (OUTPUT / "analysis_brief.md").read_text(encoding="utf-8"),
        "source_inventory": pd.read_csv(OUTPUT / "source_inventory.tsv", sep="\t"),
        "quality_checks": pd.read_csv(OUTPUT / "quality_checks.tsv", sep="\t"),
        "period_summary": pd.read_csv(OUTPUT / "airport_partner_zone_period_summary.csv"),
        "weather_sensitivity": pd.read_csv(OUTPUT / "airport_weather_sensitivity.tsv", sep="\t"),
        "rankings": pd.read_csv(OUTPUT / "airport_partner_zone_rankings.tsv", sep="\t"),
        "query_pack": (OUTPUT / "query_pack.sql").read_text(encoding="utf-8"),
    }


def test_required_outputs_exist_and_parse() -> None:
    required = [
        OUTPUT / "analysis_brief.md",
        OUTPUT / "source_inventory.tsv",
        OUTPUT / "quality_checks.tsv",
        OUTPUT / "airport_partner_zone_period_summary.csv",
        OUTPUT / "airport_weather_sensitivity.tsv",
        OUTPUT / "airport_partner_zone_rankings.tsv",
        OUTPUT / "query_pack.sql",
    ]
    for path in required:
        assert path.exists(), f"missing required output: {path}"
        assert path.stat().st_size > 0, f"empty required output: {path}"
    outputs = read_outputs()
    assert list(outputs["source_inventory"].columns) == SOURCE_COLUMNS
    assert list(outputs["quality_checks"].columns) == QUALITY_COLUMNS
    assert list(outputs["period_summary"].columns) == SUMMARY_COLUMNS
    assert list(outputs["weather_sensitivity"].columns) == WEATHER_COLUMNS
    assert list(outputs["rankings"].columns) == RANKING_COLUMNS


def test_bound_data_analyst_skill_is_available_when_present() -> None:
    skill_path = Path("/root/.codex/skills/data-analyst/SKILL.md")
    if not skill_path.exists():
        return
    content = skill_path.read_text(encoding="utf-8")
    assert "name: data-analyst" in content
    assert "SQL, pandas, and statistical analysis" in content
    assert "Performance considerations" in content


def test_source_inventory_and_quality_checks_follow_contract() -> None:
    expected = reference_metrics.expected_bundle()
    actual = read_outputs()
    contract = reference_metrics.load_contract()
    actual_sources = actual["source_inventory"]
    expected_sources = expected["source_inventory"]
    assert set(actual_sources["source_name"]) == set(contract["output_contract"]["source_inventory_expected_sources"])
    merged = actual_sources.merge(
        expected_sources[["source_name", "path"]],
        on="source_name",
        how="left",
        suffixes=("", "_expected"),
    )
    assert merged["path"].equals(merged["path_expected"])

    quality = actual["quality_checks"]
    assert len(quality) >= 6
    assert set(quality["status"].str.lower()).issubset({"pass", "warn"})


def test_period_summary_matches_oracle() -> None:
    expected = sorted_frame(
        reference_metrics.expected_bundle()["period_summary"],
        ["period", "airport_code", "partner_zone_id"],
    )
    actual = sorted_frame(
        read_outputs()["period_summary"],
        ["period", "airport_code", "partner_zone_id"],
    )
    identity_columns = ["period", "airport_code", "partner_zone_id", "partner_zone_name", "borough"]
    assert_frame_equal(actual[identity_columns], expected[identity_columns], check_dtype=False)
    assert actual["active_service_days"].equals(expected["active_service_days"])
    assert_with_tolerance(
        actual["total_airport_trips"],
        expected["total_airport_trips"],
        atol=0.0,
        label="total_airport_trips",
    )
    assert_with_tolerance(
        actual["total_partner_zone_trips"],
        expected["total_partner_zone_trips"],
        atol=5.0,
        label="total_partner_zone_trips",
    )
    assert_with_tolerance(
        actual["avg_airport_trip_share"],
        expected["avg_airport_trip_share"],
        atol=0.02,
        label="avg_airport_trip_share",
    )
    assert set(actual["period"]) == {"morning_departures", "evening_arrivals"}
    assert set(actual["airport_code"]) == {"EWR", "JFK", "LGA"}
    assert actual["avg_airport_trip_share"].between(0.0, 1.0).all()


def test_weather_sensitivity_matches_oracle() -> None:
    expected = normalize_effect_direction(sorted_frame(
        reference_metrics.expected_bundle()["weather_sensitivity"],
        ["period", "airport_code", "weather_bucket"],
    ))
    actual = normalize_effect_direction(sorted_frame(
        read_outputs()["weather_sensitivity"],
        ["period", "airport_code", "weather_bucket"],
    ))
    assert_frame_equal(
        actual[["period", "airport_code", "weather_bucket", "effect_direction"]],
        expected[["period", "airport_code", "weather_bucket", "effect_direction"]],
        check_dtype=False,
    )
    assert_with_tolerance(
        actual["avg_airport_trip_count"],
        expected["avg_airport_trip_count"],
        atol=0.18,
        label="avg_airport_trip_count",
    )
    assert_with_tolerance(
        actual["avg_airport_trip_share"],
        expected["avg_airport_trip_share"],
        atol=0.02,
        label="avg_airport_trip_share",
    )
    pvalues = actual["vs_dry_u_test_pvalue"]
    assert pvalues.dropna().between(0.0, 1.0).all()
    assert set(actual["effect_direction"]).issubset({"reference", "higher", "lower", "no_change"})


def test_rankings_match_oracle() -> None:
    expected = sorted_frame(
        reference_metrics.expected_bundle()["rankings"],
        ["period", "airport_code", "rank", "zone_id"],
    )
    actual = sorted_frame(
        read_outputs()["rankings"],
        ["period", "airport_code", "rank", "zone_id"],
    )
    identity_columns = [
        "period",
        "airport_code",
        "recommendation_type",
        "rank",
        "zone_id",
        "zone_name",
        "borough",
        "recommended_action",
        "reason_code",
    ]
    assert_frame_equal(actual[identity_columns], expected[identity_columns], check_dtype=False)
    assert_with_tolerance(
        actual["avg_airport_trip_share"],
        expected["avg_airport_trip_share"],
        atol=0.02,
        label="ranking avg_airport_trip_share",
    )
    assert set(actual["recommendation_type"]) == {"departure_feeder_coverage", "arrival_return_coverage"}
    assert actual["rank"].ge(1).all()
    assert actual["opportunity_score"].gt(0).all()


def test_analysis_brief_is_traceable() -> None:
    outputs = read_outputs()
    brief = outputs["analysis_brief"]
    rankings = outputs["rankings"]
    for heading in ["Scope", "Morning departures", "Evening arrivals", "Weather notes", "Method notes"]:
        assert re.search(rf"(?m)^#+\s+{re.escape(heading)}\s*$", brief)
    for zone_name in rankings.sort_values(["period", "airport_code", "rank"]).head(8)["zone_name"].tolist():
        assert zone_name in brief, f"{zone_name} missing from analysis_brief.md"
    assert "2023-01-02" in brief and "2023-02-07" in brief


def test_query_pack_documents_reusable_sql() -> None:
    query_pack = read_outputs()["query_pack"]
    assert "-- Query 1:" in query_pack
    assert len(re.findall(r"-- Query \d+:", query_pack)) >= 4
    for table in ["dispatch_batch_a", "dispatch_batch_b", "dispatch_batch_c", "dispatch_batch_d", "zone_lookup"]:
        assert table in query_pack
    for token in ["airport_fee", "Airport_fee", "airport_fee_amount", "airport_fee_paid"]:
        assert token in query_pack
    assert len(re.findall(r"\bSELECT\b", query_pack, flags=re.IGNORECASE)) >= 4
    assert "UNION ALL" in query_pack
    assert re.search(r"GROUP BY|COUNT\s*\(|AVG\s*\(|SUM\s*\(", query_pack, flags=re.IGNORECASE)


def test_guardrail_uses_real_sqlite_and_contract_rerun_changes_output() -> None:
    db = DATA / "trips" / "airport_partner_ops.db"
    assert db.exists() and db.stat().st_size > 1_000_000
    conn = reference_metrics.sqlite3.connect(db)
    try:
        tables = pd.read_sql_query("SELECT name FROM sqlite_master WHERE type='table' ORDER BY 1", conn)["name"].tolist()
    finally:
        conn.close()
    assert {"dispatch_batch_a", "dispatch_batch_b", "dispatch_batch_c", "dispatch_batch_d", "zone_lookup"}.issubset(set(tables))
    source_files = list(WORKSPACE.rglob("*.py")) + list(WORKSPACE.rglob("*.sql")) + list(WORKSPACE.rglob("*.sh"))
    joined = "\n".join(path.read_text(encoding="utf-8", errors="ignore") for path in source_files)
    assert re.search(r"sqlite3|read_sql_query|SELECT\s+.+FROM", joined, re.IGNORECASE | re.DOTALL), "solution does not appear to query SQLite data"
    assert "analysis_contract.json" in joined, "solution does not appear to read the planning contract"

    tmp_root = Path("/tmp/airport_partner_contract_mutation")
    if tmp_root.exists():
        import shutil
        shutil.rmtree(tmp_root)
    import shutil
    data_copy = tmp_root / "data"
    output_copy = tmp_root / "output"
    shutil.copytree(DATA, data_copy)
    contract_path = data_copy / "planning" / "analysis_contract.json"
    contract = json.loads(contract_path.read_text(encoding="utf-8"))
    contract["candidate_market"]["exclude_zone_names"].append("Times Sq/Theatre District")
    contract["periods"]["morning_departures"]["top_k"] = 1
    contract["periods"]["evening_arrivals"]["top_k"] = 2
    contract_path.write_text(json.dumps(contract, ensure_ascii=False, indent=2), encoding="utf-8")
    output_copy.mkdir(parents=True, exist_ok=True)
    subprocess.run(
        [sys.executable, "/root/workspace/run_airport_partner_analysis.py", "--data", str(data_copy), "--output", str(output_copy)],
        check=True,
        timeout=120,
    )
    mutated = pd.read_csv(output_copy / "airport_partner_zone_rankings.tsv", sep="\t")
    assert len(mutated) == 7
    assert "Times Sq/Theatre District" not in set(mutated["zone_name"])


def test_guardrail_no_hardcoded_answer_table_or_external_dependencies() -> None:
    source_files = list(WORKSPACE.rglob("*.py")) + list(WORKSPACE.rglob("*.sh")) + list(WORKSPACE.rglob("*.sql"))
    joined = "\n".join(path.read_text(encoding="utf-8", errors="ignore") for path in source_files)
    forbidden = ["OPENAI_API_KEY", "requests.post", "boto3", "google.cloud", "azure.identity"]
    assert not any(token in joined for token in forbidden), "solution should not depend on external accounts or cloud services"
    suspicious_names = ["Times Sq/Theatre District", "Midtown Center", "Clinton East", "Midtown East"]
    count = sum(joined.count(name) for name in suspicious_names)
    assert count <= 8, "suspicious amount of ranking-name hardcoding"


def test_guardrail_repeated_run_is_deterministic() -> None:
    tracked = [
        OUTPUT / "analysis_brief.md",
        OUTPUT / "source_inventory.tsv",
        OUTPUT / "quality_checks.tsv",
        OUTPUT / "airport_partner_zone_period_summary.csv",
        OUTPUT / "airport_weather_sensitivity.tsv",
        OUTPUT / "airport_partner_zone_rankings.tsv",
        OUTPUT / "query_pack.sql",
    ]
    before = {path.name: path.read_bytes() for path in tracked}
    subprocess.run(
        [sys.executable, "/root/workspace/run_airport_partner_analysis.py", "--data", "/root/data", "--output", "/root/output"],
        check=True,
        timeout=120,
    )
    after = {path.name: path.read_bytes() for path in tracked}
    assert before == after
