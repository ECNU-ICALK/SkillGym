from __future__ import annotations

import json
import re
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

PGHOST = "/tmp/rapid-transit-pg"
PGPORT = "55434"
PGUSER = "postgres"
DB_NAME = "rapid_transit_release"


def run(cmd: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(cmd, check=True, capture_output=True, text=True)


def run_script(data_root: Path, output_root: Path) -> None:
    output_root.mkdir(parents=True, exist_ok=True)
    run(
        [
            "python3",
            str(WORKSPACE / "run_rapid_transit_release.py"),
            "--data",
            str(data_root),
            "--output",
            str(output_root),
        ]
    )


def query_to_frame(query: str, *, sep: str = ",") -> pd.DataFrame:
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
    if sep == "\t":
        return pd.read_csv(StringIO(result.stdout), sep=sep)
    return pd.read_csv(StringIO(result.stdout))


def read_outputs(root: Path = OUTPUT) -> dict[str, object]:
    return {
        "panel": pd.read_csv(root / "weekday_station_window_panel.csv", parse_dates=["service_date"]),
        "leaderboard": pd.read_csv(
            root / "terminal_service_gap_leaderboard.tsv",
            sep="\t",
            parse_dates=["snapshot_date"],
        ),
        "release_notes": (root / "release_notes.md").read_text(encoding="utf-8"),
        "migration_001": (root / "migrations/001_raw_gtfs.sql").read_text(encoding="utf-8"),
        "migration_002": (root / "migrations/002_service_core.sql").read_text(encoding="utf-8"),
        "migration_003": (root / "migrations/003_release_marts.sql").read_text(encoding="utf-8"),
    }


def sort_frame(frame: pd.DataFrame, columns: list[str]) -> pd.DataFrame:
    return frame.sort_values(columns).reset_index(drop=True)


def copy_csv_into(table_name: str, path: Path) -> None:
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
            "-c",
            f"\\copy {table_name} FROM '{path}' CSV HEADER",
        ]
    )


def reset_database() -> None:
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
            "postgres",
            "-c",
            (
                "SELECT pg_terminate_backend(pid) "
                "FROM pg_stat_activity "
                f"WHERE datname = '{DB_NAME}' AND pid <> pg_backend_pid();"
            ),
        ]
    )
    run(
        [
            "dropdb",
            "-h",
            PGHOST,
            "-p",
            PGPORT,
            "-U",
            PGUSER,
            "--if-exists",
            DB_NAME,
        ]
    )
    run(
        [
            "createdb",
            "-h",
            PGHOST,
            "-p",
            PGPORT,
            "-U",
            PGUSER,
            DB_NAME,
        ]
    )


def replay_migrations() -> None:
    migrations = [
        OUTPUT / "migrations/001_raw_gtfs.sql",
        OUTPUT / "migrations/002_service_core.sql",
        OUTPUT / "migrations/003_release_marts.sql",
    ]
    reset_database()
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
            str(migrations[0]),
        ]
    )
    copy_csv_into("raw.gtfs_agency", DATA / "gtfs/agency.txt")
    copy_csv_into("raw.gtfs_routes", DATA / "gtfs/routes.txt")
    copy_csv_into("raw.gtfs_stops", DATA / "gtfs/stops.txt")
    copy_csv_into("raw.gtfs_trips", DATA / "gtfs/trips.txt")
    copy_csv_into("raw.gtfs_stop_times", DATA / "gtfs/stop_times.txt")
    copy_csv_into("raw.gtfs_calendar", DATA / "gtfs/calendar.txt")
    copy_csv_into("raw.gtfs_calendar_dates", DATA / "gtfs/calendar_dates.txt")
    for migration in migrations[1:]:
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
                str(migration),
            ]
        )


def index_definitions(schema_name: str, table_name: str) -> list[str]:
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
                f"WHERE schemaname = '{schema_name}' AND tablename = '{table_name}' "
                "ORDER BY indexname"
            ),
        ]
    )
    return [line.strip() for line in result.stdout.splitlines() if line.strip()]


def test_required_outputs_exist_and_parse() -> None:
    required = [
        OUTPUT / "weekday_station_window_panel.csv",
        OUTPUT / "terminal_service_gap_leaderboard.tsv",
        OUTPUT / "migrations/001_raw_gtfs.sql",
        OUTPUT / "migrations/002_service_core.sql",
        OUTPUT / "migrations/003_release_marts.sql",
        OUTPUT / "release_notes.md",
    ]
    for path in required:
        assert path.exists(), f"missing required output: {path}"
        assert path.stat().st_size > 0, f"empty required output: {path}"

    outputs = read_outputs()
    assert list(outputs["panel"].columns) == reference_metrics.PANEL_COLUMNS
    assert list(outputs["leaderboard"].columns) == reference_metrics.LEADERBOARD_COLUMNS


def test_bound_skill_is_available_when_present() -> None:
    skill_path = Path("/root/.codex/skills/database-migrations/SKILL.md")
    if not skill_path.exists():
        return
    content = skill_path.read_text(encoding="utf-8")
    assert "name: database-migrations" in content
    assert "Database migration best practices" in content
    assert "Every change is a migration" in content


def test_panel_matches_oracle() -> None:
    expected = sort_frame(
        reference_metrics.expected_bundle()["panel"],
        ["service_date", "route_id", "direction_id", "parent_station_id", "window_name"],
    )
    actual = sort_frame(
        read_outputs()["panel"],
        ["service_date", "route_id", "direction_id", "parent_station_id", "window_name"],
    )
    assert_frame_equal(actual, expected, check_dtype=False)
    assert set(actual["window_name"]) == {"morning_peak", "evening_peak"}
    assert (actual["scheduled_trip_count"] >= 0).all()
    assert (actual["scheduled_trip_count"] == 0).any()


def test_leaderboard_matches_oracle() -> None:
    expected = sort_frame(
        reference_metrics.expected_bundle()["leaderboard"],
        ["snapshot_date", "route_id", "window_name", "rank", "terminal_station_id"],
    )
    actual = sort_frame(
        read_outputs()["leaderboard"],
        ["snapshot_date", "route_id", "window_name", "rank", "terminal_station_id"],
    )
    assert_frame_equal(actual, expected, check_dtype=False, atol=1e-6)


def test_release_notes_are_traceable() -> None:
    outputs = read_outputs()
    notes = outputs["release_notes"]
    leaderboard = outputs["leaderboard"]
    for heading in ["Scope", "Migration order", "Panel checks", "Leaderboard checks"]:
        assert re.search(rf"(?m)^#+\s+{re.escape(heading)}\s*$", notes)
    assert "2026-05-11" in notes and "2026-05-15" in notes
    for terminal_name in leaderboard["terminal_station_name"].tolist():
        assert terminal_name in notes


def test_migration_files_reference_required_relations() -> None:
    outputs = read_outputs()
    combined = "\n".join(
        [outputs["migration_001"], outputs["migration_002"], outputs["migration_003"]]
    )
    for relation in [
        "raw.gtfs_routes",
        "raw.gtfs_trips",
        "raw.gtfs_stop_times",
        "core.service_dates",
        "core.station_departures",
        "mart.weekday_station_window_panel",
        "mart.terminal_service_gap_leaderboard",
    ]:
        assert relation in combined


def test_migrations_replay_and_match_outputs() -> None:
    replay_migrations()

    panel_query = """
        SELECT service_date, route_family, route_id, route_short_name, direction_id,
               parent_station_id, parent_station_name, window_name, scheduled_trip_count,
               first_departure_local, last_departure_local
        FROM mart.weekday_station_window_panel
        ORDER BY service_date, route_id, direction_id, parent_station_name, window_name
    """
    leaderboard_query = """
        SELECT snapshot_date, route_family, route_id, route_short_name, direction_id,
               window_name, rank, terminal_station_id, terminal_station_name,
               active_service_days, scheduled_departure_count, median_headway_minutes,
               p90_headway_minutes, max_headway_minutes, service_gap_score
        FROM mart.terminal_service_gap_leaderboard
        ORDER BY snapshot_date, route_id, window_name, rank, terminal_station_name
    """

    db_panel = query_to_frame(panel_query)
    db_panel["service_date"] = pd.to_datetime(db_panel["service_date"])
    file_panel = read_outputs()["panel"]
    assert_frame_equal(
        sort_frame(db_panel, ["service_date", "route_id", "direction_id", "parent_station_id", "window_name"]),
        sort_frame(file_panel, ["service_date", "route_id", "direction_id", "parent_station_id", "window_name"]),
        check_dtype=False,
    )

    db_leaderboard = query_to_frame(leaderboard_query)
    db_leaderboard["snapshot_date"] = pd.to_datetime(db_leaderboard["snapshot_date"])
    file_leaderboard = read_outputs()["leaderboard"]
    assert_frame_equal(
        sort_frame(
            db_leaderboard,
            ["snapshot_date", "route_id", "window_name", "rank", "terminal_station_id"],
        ),
        sort_frame(
            file_leaderboard,
            ["snapshot_date", "route_id", "window_name", "rank", "terminal_station_id"],
        ),
        check_dtype=False,
        atol=1e-6,
    )


def test_contract_mutation_changes_outputs() -> None:
    temp_data = Path("/tmp/rapid-transit-mutated-data")
    temp_output = Path("/tmp/rapid-transit-mutated-output")
    if temp_data.exists():
        run(["rm", "-rf", str(temp_data)])
    if temp_output.exists():
        run(["rm", "-rf", str(temp_output)])
    run(["cp", "-R", str(DATA), str(temp_data)])

    contract_path = temp_data / "release_contract.json"
    contract = json.loads(contract_path.read_text(encoding="utf-8"))
    contract["time_windows"][0]["end_time"] = "07:59:59"
    contract_path.write_text(json.dumps(contract, indent=2), encoding="utf-8")

    run_script(temp_data, temp_output)

    base_panel = read_outputs()["panel"]
    mutated_panel = pd.read_csv(
        temp_output / "weekday_station_window_panel.csv", parse_dates=["service_date"]
    )
    assert not base_panel.equals(mutated_panel), "mutated contract should change the panel output"


def test_repeat_runs_are_stable() -> None:
    temp_output = Path("/tmp/rapid-transit-repeat-output")
    if temp_output.exists():
        run(["rm", "-rf", str(temp_output)])
    run_script(DATA, temp_output)

    base_panel = read_outputs()["panel"]
    repeat_panel = pd.read_csv(
        temp_output / "weekday_station_window_panel.csv", parse_dates=["service_date"]
    )
    base_leaderboard = read_outputs()["leaderboard"]
    repeat_leaderboard = pd.read_csv(
        temp_output / "terminal_service_gap_leaderboard.tsv",
        sep="\t",
        parse_dates=["snapshot_date"],
    )
    assert_frame_equal(base_panel, repeat_panel, check_dtype=False)
    assert_frame_equal(base_leaderboard, repeat_leaderboard, check_dtype=False, atol=1e-6)


def test_index_guardrails_exist() -> None:
    replay_migrations()
    stop_time_indexes = index_definitions("raw", "gtfs_stop_times")
    station_indexes = index_definitions("core", "station_departures")
    panel_indexes = index_definitions("mart", "weekday_station_window_panel")

    assert any("trip_id" in index and "stop_sequence" in index for index in stop_time_indexes)
    assert any(
        "service_date" in index and "departure_seconds" in index
        for index in station_indexes
    )
    assert any("service_date" in index and "window_name" in index for index in panel_indexes)
