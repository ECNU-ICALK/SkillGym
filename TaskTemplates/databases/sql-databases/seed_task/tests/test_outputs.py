from __future__ import annotations

import json
import re
import shutil
import subprocess
import sys
from io import StringIO
from pathlib import Path

import pandas as pd
from pandas.testing import assert_frame_equal

sys.path.insert(0, "/tests")
import reference_metrics

OUTPUT = Path("/root/output")
WORKSPACE = Path("/root/workspace")
DATA = Path("/root/data")

PGHOST = "/tmp/sql-databases-pg"
PGPORT = "55433"
PGUSER = "postgres"
DB_NAME = "airport_ops_task"


def run(cmd: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(cmd, check=True, capture_output=True, text=True)


def run_script(data_root: Path, output_root: Path) -> None:
    output_root.mkdir(parents=True, exist_ok=True)
    run(
        [
            "python3",
            str(WORKSPACE / "run_airport_zone_analysis.py"),
            "--data",
            str(data_root),
            "--output",
            str(output_root),
        ]
    )


def query_to_frame(query: str) -> pd.DataFrame:
    result = run(
        [
            "psql",
            "-v",
            "ON_ERROR_STOP=1",
            "-h",
            PGHOST,
            "-p",
            PGPORT,
            "-U",
            PGUSER,
            "-d",
            DB_NAME,
            "-c",
            f"COPY ({query}) TO STDOUT WITH CSV HEADER",
        ]
    )
    return pd.read_csv(StringIO(result.stdout))


def read_outputs(root: Path = OUTPUT) -> dict[str, object]:
    return {
        "daily": pd.read_csv(root / "airport_zone_daily_mart.csv", parse_dates=["service_date"]),
        "leaderboard": pd.read_csv(
            root / "airport_zone_snapshot_leaderboard.tsv",
            sep="\t",
            parse_dates=["snapshot_date"],
        ),
        "benchmark_report": (root / "benchmark_report.md").read_text(encoding="utf-8"),
        "query_pack": (root / "query_pack.sql").read_text(encoding="utf-8"),
    }


def sorted_frame(frame: pd.DataFrame, sort_columns: list[str]) -> pd.DataFrame:
    return frame.sort_values(sort_columns).reset_index(drop=True)


def index_definitions(table_name: str) -> list[str]:
    result = run(
        [
            "psql",
            "-v",
            "ON_ERROR_STOP=1",
            "-Atq",
            "-h",
            PGHOST,
            "-p",
            PGPORT,
            "-U",
            PGUSER,
            "-d",
            DB_NAME,
            "-c",
            (
                "SELECT indexdef FROM pg_indexes "
                f"WHERE schemaname = 'analysis' AND tablename = '{table_name}' "
                "ORDER BY indexname"
            ),
        ]
    )
    return [line.strip() for line in result.stdout.splitlines() if line.strip()]


def test_required_outputs_exist_and_parse() -> None:
    required = [
        OUTPUT / "airport_zone_daily_mart.csv",
        OUTPUT / "airport_zone_snapshot_leaderboard.tsv",
        OUTPUT / "query_pack.sql",
        OUTPUT / "benchmark_report.md",
    ]
    for path in required:
        assert path.exists(), f"missing required output: {path}"
        assert path.stat().st_size > 0, f"empty required output: {path}"

    outputs = read_outputs()
    assert list(outputs["daily"].columns) == reference_metrics.DAILY_COLUMNS
    assert list(outputs["leaderboard"].columns) == reference_metrics.LEADERBOARD_COLUMNS


def test_bound_postgres_skill_is_available_when_present() -> None:
    skill_path = Path("/root/.codex/skills/postgres-patterns/SKILL.md")
    if not skill_path.exists():
        return
    content = skill_path.read_text(encoding="utf-8")
    assert "name: postgres-patterns" in content
    assert "PostgreSQL database patterns for query optimization" in content
    assert "Quick reference for PostgreSQL best practices" in content


def test_daily_mart_matches_oracle() -> None:
    expected = sorted_frame(
        reference_metrics.expected_bundle()["daily"],
        ["service_date", "period", "airport_code", "zone_id"],
    )
    actual = sorted_frame(
        read_outputs()["daily"],
        ["service_date", "period", "airport_code", "zone_id"],
    )
    assert_frame_equal(actual, expected, check_dtype=False, atol=1e-6)
    assert set(actual["period"]) == {"morning_departures", "evening_arrivals"}
    assert set(actual["airport_code"]) == {"EWR", "JFK", "LGA"}
    assert actual["airport_trip_share"].between(0.0, 1.0).all()


def test_snapshot_leaderboard_matches_oracle() -> None:
    expected = sorted_frame(
        reference_metrics.expected_bundle()["leaderboard"],
        ["snapshot_date", "period", "airport_code", "rank", "zone_id"],
    )
    actual = sorted_frame(
        read_outputs()["leaderboard"],
        ["snapshot_date", "period", "airport_code", "rank", "zone_id"],
    )
    assert_frame_equal(actual, expected, check_dtype=False, atol=1e-6)
    assert actual["rolling_airport_trip_share"].between(0.0, 1.0).all()


def test_benchmark_report_is_traceable() -> None:
    outputs = read_outputs()
    report = outputs["benchmark_report"]
    leaderboard = outputs["leaderboard"]
    for heading in ["Scope", "Daily mart", "Snapshot leaderboard", "Index strategy"]:
        assert re.search(rf"(?m)^#+\s+{re.escape(heading)}\s*$", report)
    for zone_name in leaderboard["zone_name"].tolist():
        assert zone_name in report, f"{zone_name} missing from benchmark_report.md"
    assert "2023-01-02" in report and "2023-02-07" in report


def test_query_pack_documents_reusable_sql() -> None:
    query_pack = read_outputs()["query_pack"]
    assert "-- Query 1:" in query_pack
    assert len(re.findall(r"-- Query \d+:", query_pack)) >= 5
    for table in [
        "raw.dispatch_batch_a",
        "raw.dispatch_batch_b",
        "raw.dispatch_batch_c",
        "raw.dispatch_batch_d",
        "raw.zone_lookup",
    ]:
        assert table in query_pack
    for name in [
        "analysis.trip_fact_normalized",
        "analysis.airport_zone_daily",
        "analysis.airport_zone_rolling_7d",
        "analysis.airport_zone_snapshot_leaderboard",
    ]:
        assert name in query_pack
    assert "CREATE INDEX" in query_pack
    assert "MATERIALIZED VIEW" in query_pack


def test_query_pack_executes_and_matches_outputs() -> None:
    run(
        [
            "psql",
            "-v",
            "ON_ERROR_STOP=1",
            "-h",
            PGHOST,
            "-p",
            PGPORT,
            "-U",
            PGUSER,
            "-d",
            DB_NAME,
            "-f",
            str(OUTPUT / "query_pack.sql"),
        ]
    )

    view_daily = sorted_frame(
        query_to_frame(
            """
            SELECT service_date, period, airport_code, zone_id, zone_name, borough,
                   airport_trip_count, total_trip_count, airport_trip_share
            FROM analysis.airport_zone_daily
            ORDER BY service_date, period, airport_code, zone_id
            """
        ),
        ["service_date", "period", "airport_code", "zone_id"],
    )
    view_daily["service_date"] = pd.to_datetime(view_daily["service_date"])
    file_daily = sorted_frame(
        read_outputs()["daily"],
        ["service_date", "period", "airport_code", "zone_id"],
    )
    assert_frame_equal(file_daily, view_daily, check_dtype=False, atol=1e-6)

    view_leaderboard = sorted_frame(
        query_to_frame(
            """
            SELECT snapshot_date, period, airport_code, rank, zone_id, zone_name, borough,
                   active_days_in_window, rolling_airport_trip_count, rolling_total_trip_count,
                   rolling_airport_trip_share, rolling_opportunity_score
            FROM analysis.airport_zone_snapshot_leaderboard
            ORDER BY snapshot_date, period, airport_code, rank, zone_id
            """
        ),
        ["snapshot_date", "period", "airport_code", "rank", "zone_id"],
    )
    view_leaderboard["snapshot_date"] = pd.to_datetime(view_leaderboard["snapshot_date"])
    file_leaderboard = sorted_frame(
        read_outputs()["leaderboard"],
        ["snapshot_date", "period", "airport_code", "rank", "zone_id"],
    )
    assert_frame_equal(file_leaderboard, view_leaderboard, check_dtype=False, atol=1e-6)


def test_index_guardrails_exist_and_are_reported() -> None:
    fact_indexes = index_definitions("trip_fact_normalized")
    daily_indexes = index_definitions("airport_zone_daily")

    assert any("period" in idx.lower() and "service_date" in idx.lower() for idx in fact_indexes)
    assert any("airport_code" in idx.lower() and "service_date" in idx.lower() for idx in daily_indexes)

    report = read_outputs()["benchmark_report"].lower()
    assert "index" in report


def test_guardrails_require_postgres_contract_and_contract_sensitivity() -> None:
    source_files = (
        list(WORKSPACE.rglob("*.py"))
        + list(WORKSPACE.rglob("*.sql"))
        + list(WORKSPACE.rglob("*.sh"))
    )
    joined = "\n".join(path.read_text(encoding="utf-8", errors="ignore") for path in source_files)
    assert re.search(r"psql|postgres|psycopg", joined, re.IGNORECASE), "solution does not appear to query PostgreSQL"
    assert "analysis_contract.json" in joined, "solution does not appear to read the contract"

    tmp_root = Path("/tmp/sql_databases_contract_mutation")
    if tmp_root.exists():
        shutil.rmtree(tmp_root)
    (tmp_root / "data").mkdir(parents=True)
    shutil.copytree(DATA / "reference", tmp_root / "data" / "reference")
    for filename in [
        "dispatch_batch_a.csv",
        "dispatch_batch_b.csv",
        "dispatch_batch_c.csv",
        "dispatch_batch_d.csv",
        "taxi_zone_lookup.csv",
    ]:
        shutil.copy2(DATA / filename, tmp_root / "data" / filename)

    contract = json.loads((DATA / "analysis_contract.json").read_text(encoding="utf-8"))
    contract["rolling_window"]["snapshot_dates"] = ["2023-01-24", "2023-02-07"]
    contract["ranking_score"]["count_weight"] = 0.35
    contract["ranking_score"]["share_weight"] = 0.45
    contract["ranking_score"]["active_days_weight"] = 0.20
    (tmp_root / "data" / "analysis_contract.json").write_text(
        json.dumps(contract, indent=2) + "\n",
        encoding="utf-8",
    )

    mutated_output = tmp_root / "output"
    run_script(tmp_root / "data", mutated_output)

    baseline = read_outputs()["leaderboard"]
    mutated = pd.read_csv(
        mutated_output / "airport_zone_snapshot_leaderboard.tsv",
        sep="\t",
        parse_dates=["snapshot_date"],
    )
    assert not baseline.equals(mutated), "leaderboard did not respond to contract mutation"


def test_repeated_runs_are_stable() -> None:
    rerun_root = Path("/tmp/sql_databases_repeat_run")
    if rerun_root.exists():
        shutil.rmtree(rerun_root)
    rerun_root.mkdir(parents=True)
    run_script(DATA, rerun_root)

    first_daily = sorted_frame(
        read_outputs()["daily"],
        ["service_date", "period", "airport_code", "zone_id"],
    )
    second_daily = sorted_frame(
        pd.read_csv(rerun_root / "airport_zone_daily_mart.csv", parse_dates=["service_date"]),
        ["service_date", "period", "airport_code", "zone_id"],
    )
    assert_frame_equal(first_daily, second_daily, check_dtype=False, atol=1e-6)

    first_leaderboard = sorted_frame(
        read_outputs()["leaderboard"],
        ["snapshot_date", "period", "airport_code", "rank", "zone_id"],
    )
    second_leaderboard = sorted_frame(
        pd.read_csv(
            rerun_root / "airport_zone_snapshot_leaderboard.tsv",
            sep="\t",
            parse_dates=["snapshot_date"],
        ),
        ["snapshot_date", "period", "airport_code", "rank", "zone_id"],
    )
    assert_frame_equal(first_leaderboard, second_leaderboard, check_dtype=False, atol=1e-6)
