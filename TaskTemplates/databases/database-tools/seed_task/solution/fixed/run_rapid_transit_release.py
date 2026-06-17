#!/usr/bin/env python3

from __future__ import annotations

import argparse
import json
import subprocess
from pathlib import Path
from textwrap import dedent

import psycopg2

PGHOST = "/tmp/rapid-transit-pg"
PGPORT = 55434
PGUSER = "postgres"
DB_NAME = "rapid_transit_release"

PANEL_COLUMNS = [
    "service_date",
    "route_family",
    "route_id",
    "route_short_name",
    "direction_id",
    "parent_station_id",
    "parent_station_name",
    "window_name",
    "scheduled_trip_count",
    "first_departure_local",
    "last_departure_local",
]

LEADERBOARD_COLUMNS = [
    "snapshot_date",
    "route_family",
    "route_id",
    "route_short_name",
    "direction_id",
    "window_name",
    "rank",
    "terminal_station_id",
    "terminal_station_name",
    "active_service_days",
    "scheduled_departure_count",
    "median_headway_minutes",
    "p90_headway_minutes",
    "max_headway_minutes",
    "service_gap_score",
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--data", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    return parser.parse_args()


def sql_literal(value: str) -> str:
    return "'" + value.replace("'", "''") + "'"


def time_to_seconds(value: str) -> int:
    hours, minutes, seconds = [int(part) for part in value.split(":")]
    return hours * 3600 + minutes * 60 + seconds


def load_contract(data_root: Path) -> dict:
    return json.loads((data_root / "release_contract.json").read_text(encoding="utf-8"))


def build_routes_values(contract: dict) -> str:
    rows = []
    for row in contract["selected_routes"]:
        rows.append(
            f"({sql_literal(row['route_family'])}, {sql_literal(row['route_id'])})"
        )
    return ",\n                ".join(rows)


def build_windows_values(contract: dict) -> str:
    rows = []
    for row in contract["time_windows"]:
        rows.append(
            "("
            f"{sql_literal(row['window_name'])}, "
            f"{time_to_seconds(row['start_time'])}, "
            f"{time_to_seconds(row['end_time'])}"
            ")"
        )
    return ",\n                ".join(rows)


def build_window_names_values(contract: dict) -> str:
    rows = [f"({sql_literal(row['window_name'])})" for row in contract["time_windows"]]
    return ",\n                ".join(rows)


def build_snapshots_values(contract: dict) -> str:
    rows = [
        f"({sql_literal(snapshot)})"
        for snapshot in contract["terminal_origin_rules"]["snapshot_dates"]
    ]
    return ",\n                ".join(rows)


def build_weekday_list(contract: dict) -> str:
    return ", ".join(str(value) for value in contract["analysis_window"]["weekday_isodow_values"])


def build_sql_bundle(contract: dict) -> dict[str, str]:
    analysis_start = contract["analysis_window"]["start_date"]
    analysis_end = contract["analysis_window"]["end_date"]
    route_values = build_routes_values(contract)
    window_values = build_windows_values(contract)
    window_name_values = build_window_names_values(contract)
    snapshot_values = build_snapshots_values(contract)
    weekday_list = build_weekday_list(contract)
    min_candidate_days = int(
        contract["terminal_origin_rules"]["candidate_min_active_service_days_in_analysis_window"]
    )
    rolling_days = int(contract["terminal_origin_rules"]["rolling_window_days_inclusive"])
    min_snapshot_days = int(
        contract["terminal_origin_rules"]["min_active_service_days_per_snapshot"]
    )
    min_snapshot_departures = int(
        contract["terminal_origin_rules"]["min_scheduled_departure_count_per_snapshot"]
    )
    weights = contract["ranking_weights"]

    sql_001 = dedent(
        """
        DROP SCHEMA IF EXISTS mart CASCADE;
        DROP SCHEMA IF EXISTS core CASCADE;
        DROP SCHEMA IF EXISTS raw CASCADE;

        CREATE SCHEMA raw;

        CREATE TABLE raw.gtfs_agency (
            agency_id TEXT,
            agency_name TEXT,
            agency_url TEXT,
            agency_timezone TEXT,
            agency_lang TEXT,
            agency_phone TEXT,
            agency_fare_url TEXT
        );

        CREATE TABLE raw.gtfs_routes (
            route_id TEXT,
            agency_id TEXT,
            route_short_name TEXT,
            route_long_name TEXT,
            route_desc TEXT,
            route_type INTEGER,
            route_url TEXT,
            route_color TEXT,
            route_text_color TEXT,
            route_sort_order INTEGER,
            route_fare_class TEXT,
            line_id TEXT,
            listed_route TEXT,
            network_id TEXT
        );

        CREATE TABLE raw.gtfs_stops (
            stop_id TEXT,
            stop_code TEXT,
            stop_name TEXT,
            stop_desc TEXT,
            platform_code TEXT,
            platform_name TEXT,
            stop_lat TEXT,
            stop_lon TEXT,
            zone_id TEXT,
            stop_address TEXT,
            stop_url TEXT,
            level_id TEXT,
            location_type INTEGER,
            parent_station TEXT,
            wheelchair_boarding TEXT,
            municipality TEXT,
            on_street TEXT,
            at_street TEXT,
            vehicle_type TEXT
        );

        CREATE TABLE raw.gtfs_trips (
            route_id TEXT,
            service_id TEXT,
            trip_id TEXT,
            trip_headsign TEXT,
            trip_short_name TEXT,
            direction_id INTEGER,
            block_id TEXT,
            shape_id TEXT,
            wheelchair_accessible TEXT,
            trip_route_type TEXT,
            route_pattern_id TEXT,
            bikes_allowed TEXT
        );

        CREATE TABLE raw.gtfs_stop_times (
            trip_id TEXT,
            arrival_time TEXT,
            departure_time TEXT,
            stop_id TEXT,
            stop_sequence INTEGER,
            stop_headsign TEXT,
            pickup_type TEXT,
            drop_off_type TEXT,
            timepoint TEXT,
            checkpoint_id TEXT,
            continuous_pickup TEXT,
            continuous_drop_off TEXT
        );

        CREATE TABLE raw.gtfs_calendar (
            service_id TEXT,
            monday INTEGER,
            tuesday INTEGER,
            wednesday INTEGER,
            thursday INTEGER,
            friday INTEGER,
            saturday INTEGER,
            sunday INTEGER,
            start_date TEXT,
            end_date TEXT
        );

        CREATE TABLE raw.gtfs_calendar_dates (
            service_id TEXT,
            date TEXT,
            exception_type INTEGER,
            holiday_name TEXT
        );

        CREATE INDEX idx_raw_gtfs_routes_route_id
            ON raw.gtfs_routes (route_id);
        CREATE INDEX idx_raw_gtfs_trips_service_route_direction
            ON raw.gtfs_trips (service_id, route_id, direction_id, trip_id);
        CREATE INDEX idx_raw_gtfs_stop_times_trip_sequence
            ON raw.gtfs_stop_times (trip_id, stop_sequence);
        CREATE INDEX idx_raw_gtfs_stops_stop_parent
            ON raw.gtfs_stops (stop_id, parent_station);
        CREATE INDEX idx_raw_gtfs_calendar_service
            ON raw.gtfs_calendar (service_id);
        CREATE INDEX idx_raw_gtfs_calendar_dates_service_date
            ON raw.gtfs_calendar_dates (service_id, date);
        """
    ).strip() + "\n"

    sql_002 = dedent(
        f"""
        CREATE SCHEMA IF NOT EXISTS core;

        DROP TABLE IF EXISTS core.service_dates;
        CREATE TABLE core.service_dates AS
        WITH selected_routes(route_family, route_id) AS (
            VALUES
                {route_values}
        ),
        analysis_dates AS (
            SELECT d::date AS service_date
            FROM generate_series(
                {sql_literal(analysis_start)}::date,
                {sql_literal(analysis_end)}::date,
                interval '1 day'
            ) AS d
            WHERE EXTRACT(ISODOW FROM d)::INT IN ({weekday_list})
        ),
        trip_services AS (
            SELECT DISTINCT
                sr.route_family,
                t.route_id,
                COALESCE(NULLIF(r.route_short_name, ''), r.route_id) AS route_short_name,
                t.service_id,
                t.direction_id
            FROM raw.gtfs_trips AS t
            JOIN selected_routes AS sr
              ON sr.route_id = t.route_id
            JOIN raw.gtfs_routes AS r
              ON r.route_id = t.route_id
        ),
        base_service_dates AS (
            SELECT DISTINCT
                ts.route_family,
                ts.route_id,
                ts.route_short_name,
                ts.direction_id,
                ts.service_id,
                d.service_date
            FROM trip_services AS ts
            JOIN raw.gtfs_calendar AS c
              ON c.service_id = ts.service_id
            JOIN analysis_dates AS d
              ON d.service_date BETWEEN to_date(c.start_date, 'YYYYMMDD')
                                   AND to_date(c.end_date, 'YYYYMMDD')
            WHERE CASE EXTRACT(ISODOW FROM d.service_date)::INT
                WHEN 1 THEN c.monday
                WHEN 2 THEN c.tuesday
                WHEN 3 THEN c.wednesday
                WHEN 4 THEN c.thursday
                WHEN 5 THEN c.friday
                WHEN 6 THEN c.saturday
                ELSE c.sunday
            END = 1
        ),
        added_service_dates AS (
            SELECT DISTINCT
                ts.route_family,
                ts.route_id,
                ts.route_short_name,
                ts.direction_id,
                ts.service_id,
                to_date(cd.date, 'YYYYMMDD') AS service_date
            FROM trip_services AS ts
            JOIN raw.gtfs_calendar_dates AS cd
              ON cd.service_id = ts.service_id
            WHERE cd.exception_type = 1
              AND to_date(cd.date, 'YYYYMMDD')
                    BETWEEN {sql_literal(analysis_start)}::date
                        AND {sql_literal(analysis_end)}::date
              AND EXTRACT(ISODOW FROM to_date(cd.date, 'YYYYMMDD'))::INT IN ({weekday_list})
        ),
        removed_service_dates AS (
            SELECT DISTINCT
                ts.route_family,
                ts.route_id,
                ts.route_short_name,
                ts.direction_id,
                ts.service_id,
                to_date(cd.date, 'YYYYMMDD') AS service_date
            FROM trip_services AS ts
            JOIN raw.gtfs_calendar_dates AS cd
              ON cd.service_id = ts.service_id
            WHERE cd.exception_type = 2
              AND to_date(cd.date, 'YYYYMMDD')
                    BETWEEN {sql_literal(analysis_start)}::date
                        AND {sql_literal(analysis_end)}::date
              AND EXTRACT(ISODOW FROM to_date(cd.date, 'YYYYMMDD'))::INT IN ({weekday_list})
        )
        SELECT *
        FROM (
            SELECT * FROM base_service_dates
            UNION
            SELECT * FROM added_service_dates
        ) AS combined
        EXCEPT
        SELECT * FROM removed_service_dates
        ;

        CREATE INDEX idx_core_service_dates_lookup
            ON core.service_dates (route_id, direction_id, service_date, service_id);

        DROP TABLE IF EXISTS core.station_departures;
        CREATE TABLE core.station_departures AS
        WITH configured_windows(window_name, start_seconds, end_seconds) AS (
            VALUES
                {window_values}
        ),
        rolled_stops AS (
            SELECT
                s.stop_id,
                s.stop_name,
                COALESCE(NULLIF(s.parent_station, ''), s.stop_id) AS parent_station_id,
                COALESCE(parent.stop_name, s.stop_name) AS parent_station_name
            FROM raw.gtfs_stops AS s
            LEFT JOIN raw.gtfs_stops AS parent
              ON parent.stop_id = s.parent_station
        )
        SELECT
            sd.route_family,
            sd.route_id,
            sd.route_short_name,
            sd.direction_id,
            sd.service_id,
            sd.service_date,
            t.trip_id,
            rs.stop_id,
            rs.stop_name,
            rs.parent_station_id,
            rs.parent_station_name,
            st.stop_sequence,
            st.departure_time,
            split_part(st.departure_time, ':', 1)::INT * 3600
                + split_part(st.departure_time, ':', 2)::INT * 60
                + split_part(st.departure_time, ':', 3)::INT AS departure_seconds,
            (
                SELECT cw.window_name
                FROM configured_windows AS cw
                WHERE (
                    split_part(st.departure_time, ':', 1)::INT * 3600
                    + split_part(st.departure_time, ':', 2)::INT * 60
                    + split_part(st.departure_time, ':', 3)::INT
                ) BETWEEN cw.start_seconds AND cw.end_seconds
                ORDER BY cw.start_seconds
                LIMIT 1
            ) AS window_name,
            ROW_NUMBER() OVER (
                PARTITION BY sd.service_date, t.trip_id
                ORDER BY st.stop_sequence
            ) AS stop_sequence_rank
        FROM core.service_dates AS sd
        JOIN raw.gtfs_trips AS t
          ON t.service_id = sd.service_id
         AND t.route_id = sd.route_id
         AND t.direction_id = sd.direction_id
        JOIN raw.gtfs_stop_times AS st
          ON st.trip_id = t.trip_id
        JOIN rolled_stops AS rs
          ON rs.stop_id = st.stop_id
        ;

        CREATE INDEX idx_core_station_departures_route_date_station
            ON core.station_departures (
                service_date,
                route_id,
                direction_id,
                parent_station_id,
                departure_seconds
            );
        CREATE INDEX idx_core_station_departures_trip_rank
            ON core.station_departures (
                service_date,
                trip_id,
                stop_sequence_rank
            );
        """
    ).strip() + "\n"

    sql_003 = dedent(
        f"""
        CREATE SCHEMA IF NOT EXISTS mart;

        DROP TABLE IF EXISTS mart.weekday_station_window_panel;
        CREATE TABLE mart.weekday_station_window_panel AS
        WITH configured_windows(window_name) AS (
            VALUES
                {window_name_values}
        ),
        eligible_station_scope AS (
            SELECT DISTINCT
                route_family,
                route_id,
                route_short_name,
                direction_id,
                parent_station_id,
                parent_station_name
            FROM core.station_departures
            WHERE window_name IS NOT NULL
        ),
        active_route_dates AS (
            SELECT DISTINCT
                route_family,
                route_id,
                route_short_name,
                direction_id,
                service_date
            FROM core.station_departures
        ),
        panel_grid AS (
            SELECT
                ard.service_date,
                ess.route_family,
                ess.route_id,
                ess.route_short_name,
                ess.direction_id,
                ess.parent_station_id,
                ess.parent_station_name,
                cw.window_name
            FROM active_route_dates AS ard
            JOIN eligible_station_scope AS ess
              ON ess.route_id = ard.route_id
             AND ess.direction_id = ard.direction_id
            CROSS JOIN configured_windows AS cw
        ),
        observed_counts AS (
            SELECT
                service_date,
                route_family,
                route_id,
                route_short_name,
                direction_id,
                parent_station_id,
                parent_station_name,
                window_name,
                COUNT(*)::INT AS scheduled_trip_count,
                MIN(departure_seconds) AS first_departure_seconds,
                MAX(departure_seconds) AS last_departure_seconds
            FROM core.station_departures
            WHERE window_name IS NOT NULL
            GROUP BY
                service_date,
                route_family,
                route_id,
                route_short_name,
                direction_id,
                parent_station_id,
                parent_station_name,
                window_name
        )
        SELECT
            grid.service_date,
            grid.route_family,
            grid.route_id,
            grid.route_short_name,
            grid.direction_id,
            grid.parent_station_id,
            grid.parent_station_name,
            grid.window_name,
            COALESCE(obs.scheduled_trip_count, 0) AS scheduled_trip_count,
            CASE
                WHEN obs.first_departure_seconds IS NULL THEN NULL
                ELSE LPAD((obs.first_departure_seconds / 3600)::TEXT, 2, '0')
                     || ':' || LPAD(((obs.first_departure_seconds % 3600) / 60)::TEXT, 2, '0')
                     || ':' || LPAD((obs.first_departure_seconds % 60)::TEXT, 2, '0')
            END AS first_departure_local,
            CASE
                WHEN obs.last_departure_seconds IS NULL THEN NULL
                ELSE LPAD((obs.last_departure_seconds / 3600)::TEXT, 2, '0')
                     || ':' || LPAD(((obs.last_departure_seconds % 3600) / 60)::TEXT, 2, '0')
                     || ':' || LPAD((obs.last_departure_seconds % 60)::TEXT, 2, '0')
            END AS last_departure_local
        FROM panel_grid AS grid
        LEFT JOIN observed_counts AS obs
          ON obs.service_date = grid.service_date
         AND obs.route_id = grid.route_id
         AND obs.direction_id = grid.direction_id
         AND obs.parent_station_id = grid.parent_station_id
         AND obs.window_name = grid.window_name
        ;

        CREATE INDEX idx_mart_panel_route_date_window
            ON mart.weekday_station_window_panel (
                service_date,
                route_id,
                direction_id,
                window_name,
                parent_station_id
            );

        DROP TABLE IF EXISTS mart.terminal_service_gap_leaderboard;
        CREATE TABLE mart.terminal_service_gap_leaderboard AS
        WITH snapshot_dates(snapshot_date) AS (
            VALUES
                {snapshot_values}
        ),
        origin_events AS (
            SELECT
                route_family,
                route_id,
                route_short_name,
                direction_id,
                parent_station_id AS terminal_station_id,
                parent_station_name AS terminal_station_name,
                service_date,
                window_name,
                departure_seconds
            FROM core.station_departures
            WHERE stop_sequence_rank = 1
              AND window_name IS NOT NULL
        ),
        terminal_scope AS (
            SELECT
                route_id,
                direction_id,
                terminal_station_id
            FROM origin_events
            GROUP BY route_id, direction_id, terminal_station_id
            HAVING COUNT(DISTINCT service_date) >= {min_candidate_days}
        ),
        scoped_origin_events AS (
            SELECT oe.*
            FROM origin_events AS oe
            JOIN terminal_scope AS ts
              ON ts.route_id = oe.route_id
             AND ts.direction_id = oe.direction_id
             AND ts.terminal_station_id = oe.terminal_station_id
        ),
        rolling_origin_events AS (
            SELECT
                sd.snapshot_date::date AS snapshot_date,
                oe.route_family,
                oe.route_id,
                oe.route_short_name,
                oe.direction_id,
                oe.window_name,
                oe.terminal_station_id,
                oe.terminal_station_name,
                oe.service_date,
                oe.departure_seconds
            FROM snapshot_dates AS sd
            JOIN scoped_origin_events AS oe
              ON oe.service_date BETWEEN sd.snapshot_date::date - interval '{rolling_days - 1} day'
                                   AND sd.snapshot_date::date
        ),
        per_day_headways AS (
            SELECT
                snapshot_date,
                route_family,
                route_id,
                route_short_name,
                direction_id,
                window_name,
                terminal_station_id,
                terminal_station_name,
                service_date,
                departure_seconds,
                LAG(departure_seconds) OVER (
                    PARTITION BY snapshot_date, route_id, direction_id, window_name, terminal_station_id, service_date
                    ORDER BY departure_seconds
                ) AS prior_departure_seconds
            FROM rolling_origin_events
        ),
        headway_intervals AS (
            SELECT
                snapshot_date,
                route_family,
                route_id,
                route_short_name,
                direction_id,
                window_name,
                terminal_station_id,
                terminal_station_name,
                service_date,
                (departure_seconds - prior_departure_seconds) / 60.0 AS headway_minutes
            FROM per_day_headways
            WHERE prior_departure_seconds IS NOT NULL
        ),
        departure_metrics AS (
            SELECT
                roe.snapshot_date,
                roe.route_family,
                roe.route_id,
                roe.route_short_name,
                roe.direction_id,
                roe.window_name,
                roe.terminal_station_id,
                roe.terminal_station_name,
                COUNT(DISTINCT roe.service_date)::INT AS active_service_days,
                COUNT(*)::INT AS scheduled_departure_count
            FROM rolling_origin_events AS roe
            GROUP BY
                roe.snapshot_date,
                roe.route_family,
                roe.route_id,
                roe.route_short_name,
                roe.direction_id,
                roe.window_name,
                roe.terminal_station_id,
                roe.terminal_station_name
            HAVING COUNT(DISTINCT roe.service_date) >= {min_snapshot_days}
               AND COUNT(*) >= {min_snapshot_departures}
        ),
        headway_metrics AS (
            SELECT
                hi.snapshot_date,
                hi.route_family,
                hi.route_id,
                hi.route_short_name,
                hi.direction_id,
                hi.window_name,
                hi.terminal_station_id,
                hi.terminal_station_name,
                percentile_cont(0.5) WITHIN GROUP (ORDER BY hi.headway_minutes) AS median_headway_minutes,
                percentile_cont(0.9) WITHIN GROUP (ORDER BY hi.headway_minutes) AS p90_headway_minutes,
                MAX(hi.headway_minutes) AS max_headway_minutes
            FROM headway_intervals AS hi
            GROUP BY
                hi.snapshot_date,
                hi.route_family,
                hi.route_id,
                hi.route_short_name,
                hi.direction_id,
                hi.window_name,
                hi.terminal_station_id,
                hi.terminal_station_name
        ),
        scored AS (
            SELECT
                dm.snapshot_date,
                dm.route_family,
                dm.route_id,
                dm.route_short_name,
                dm.direction_id,
                dm.window_name,
                dm.terminal_station_id,
                dm.terminal_station_name,
                dm.active_service_days,
                dm.scheduled_departure_count,
                hm.median_headway_minutes,
                hm.p90_headway_minutes,
                hm.max_headway_minutes,
                hm.median_headway_minutes * {weights['median_headway_minutes']}
                    + hm.p90_headway_minutes * {weights['p90_headway_minutes']}
                    + hm.max_headway_minutes * {weights['max_headway_minutes']}
                    AS service_gap_score
            FROM departure_metrics AS dm
            JOIN headway_metrics AS hm
              ON hm.snapshot_date = dm.snapshot_date
             AND hm.route_id = dm.route_id
             AND hm.direction_id = dm.direction_id
             AND hm.window_name = dm.window_name
             AND hm.terminal_station_id = dm.terminal_station_id
        )
        SELECT
            snapshot_date,
            route_family,
            route_id,
            route_short_name,
            direction_id,
            window_name,
            ROW_NUMBER() OVER (
                PARTITION BY snapshot_date, route_id, window_name
                ORDER BY
                    service_gap_score DESC,
                    max_headway_minutes DESC,
                    p90_headway_minutes DESC,
                    terminal_station_name ASC,
                    terminal_station_id ASC
            ) AS rank,
            terminal_station_id,
            terminal_station_name,
            active_service_days,
            scheduled_departure_count,
            ROUND(median_headway_minutes::NUMERIC, 6)::DOUBLE PRECISION AS median_headway_minutes,
            ROUND(p90_headway_minutes::NUMERIC, 6)::DOUBLE PRECISION AS p90_headway_minutes,
            ROUND(max_headway_minutes::NUMERIC, 6)::DOUBLE PRECISION AS max_headway_minutes,
            ROUND(service_gap_score::NUMERIC, 6)::DOUBLE PRECISION AS service_gap_score
        FROM scored
        ;

        CREATE INDEX idx_mart_terminal_gap_partition
            ON mart.terminal_service_gap_leaderboard (
                snapshot_date,
                route_id,
                window_name,
                rank
            );
        """
    ).strip() + "\n"

    return {
        "001_raw_gtfs.sql": sql_001,
        "002_service_core.sql": sql_002,
        "003_release_marts.sql": sql_003,
    }


def run_shell(cmd: list[str]) -> None:
    subprocess.run(cmd, check=True)


def connect_db():
    return psycopg2.connect(
        host=PGHOST,
        port=PGPORT,
        user=PGUSER,
        dbname=DB_NAME,
    )


def write_sql_files(output_root: Path, sql_bundle: dict[str, str]) -> Path:
    migrations_dir = output_root / "migrations"
    migrations_dir.mkdir(parents=True, exist_ok=True)
    for filename, sql_text in sql_bundle.items():
        (migrations_dir / filename).write_text(sql_text, encoding="utf-8")
    return migrations_dir


def execute_sql(conn, sql_text: str) -> None:
    with conn.cursor() as cur:
        cur.execute(sql_text)
    conn.commit()


def load_raw_tables(conn, data_root: Path) -> None:
    copy_specs = [
        ("raw.gtfs_agency", data_root / "gtfs/agency.txt"),
        ("raw.gtfs_routes", data_root / "gtfs/routes.txt"),
        ("raw.gtfs_stops", data_root / "gtfs/stops.txt"),
        ("raw.gtfs_trips", data_root / "gtfs/trips.txt"),
        ("raw.gtfs_stop_times", data_root / "gtfs/stop_times.txt"),
        ("raw.gtfs_calendar", data_root / "gtfs/calendar.txt"),
        ("raw.gtfs_calendar_dates", data_root / "gtfs/calendar_dates.txt"),
    ]
    with conn.cursor() as cur:
        for table_name, path in copy_specs:
            with path.open("r", encoding="utf-8") as handle:
                cur.copy_expert(
                    f"COPY {table_name} FROM STDIN WITH CSV HEADER",
                    handle,
                )
    conn.commit()


def export_query_to_file(conn, query: str, output_path: Path, *, delimiter: str = ",") -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with conn.cursor() as cur, output_path.open("w", encoding="utf-8") as handle:
        if delimiter == ",":
            copy_sql = f"COPY ({query}) TO STDOUT WITH CSV HEADER"
        else:
            copy_sql = (
                f"COPY ({query}) TO STDOUT "
                f"WITH (FORMAT CSV, HEADER TRUE, DELIMITER {sql_literal(delimiter)})"
            )
        cur.copy_expert(copy_sql, handle)


def fetch_rows(conn, query: str) -> list[dict]:
    with conn.cursor() as cur:
        cur.execute(query)
        columns = [desc[0] for desc in cur.description]
        return [dict(zip(columns, row)) for row in cur.fetchall()]


def render_release_notes(
    contract: dict,
    panel_rows: list[dict],
    leaderboard_rows: list[dict],
) -> str:
    analysis_window = contract["analysis_window"]
    snapshots = contract["terminal_origin_rules"]["snapshot_dates"]
    windows = ", ".join(window["window_name"] for window in contract["time_windows"])
    terminal_names = [row["terminal_station_name"] for row in leaderboard_rows]
    unique_terminals = sorted(dict.fromkeys(terminal_names))

    zero_rows = sum(1 for row in panel_rows if int(row["scheduled_trip_count"]) == 0)
    route_summaries = []
    for route_id in sorted(dict.fromkeys(row["route_id"] for row in leaderboard_rows)):
        rows = [row for row in leaderboard_rows if row["route_id"] == route_id]
        top = rows[0]
        route_summaries.append(
            f"- {route_id}: top gap row is {top['window_name']} / rank {top['rank']} at "
            f"{top['terminal_station_name']} with score {float(top['service_gap_score']):.3f}."
        )

    terminal_lines = [f"- {name}" for name in unique_terminals] or ["- none"]
    route_lines = route_summaries or ["- none"]

    lines = [
        "# Scope",
        "",
        f"- Analysis window: {analysis_window['start_date']} through {analysis_window['end_date']}.",
        f"- Snapshot dates: {', '.join(snapshots)}.",
        f"- Configured windows: {windows}.",
        "",
        "# Migration order",
        "",
        "1. `001_raw_gtfs.sql` rebuilds the raw GTFS ingest tables and raw indexes.",
        "2. `002_service_core.sql` expands service dates and materializes station-level departure events.",
        "3. `003_release_marts.sql` creates the panel and terminal leaderboard relations used for export.",
        "",
        "# Panel checks",
        "",
        f"- Exported panel rows: {len(panel_rows)}.",
        f"- Zero-filled panel rows: {zero_rows}.",
        (
            "- The panel follows the contract boundary dates "
            f"{analysis_window['start_date']} and {analysis_window['end_date']}."
        ),
        "",
        "# Leaderboard checks",
        "",
        f"- Exported leaderboard rows: {len(leaderboard_rows)}.",
        "- Terminal stations present in the leaderboard:",
        *terminal_lines,
        "",
        "- Route highlights:",
        *route_lines,
    ]
    return "\n".join(lines) + "\n"


def main() -> int:
    args = parse_args()
    args.output.mkdir(parents=True, exist_ok=True)

    contract = load_contract(args.data)
    sql_bundle = build_sql_bundle(contract)
    write_sql_files(args.output, sql_bundle)

    run_shell(["/root/workspace/bin/init_rapid_transit_release.sh"])

    with connect_db() as conn:
        execute_sql(conn, sql_bundle["001_raw_gtfs.sql"])
        load_raw_tables(conn, args.data)
        execute_sql(conn, sql_bundle["002_service_core.sql"])
        execute_sql(conn, sql_bundle["003_release_marts.sql"])

        panel_query = f"""
            SELECT {", ".join(PANEL_COLUMNS)}
            FROM mart.weekday_station_window_panel
            ORDER BY service_date, route_id, direction_id, parent_station_name, window_name
        """
        leaderboard_query = f"""
            SELECT {", ".join(LEADERBOARD_COLUMNS)}
            FROM mart.terminal_service_gap_leaderboard
            ORDER BY snapshot_date, route_id, window_name, rank, terminal_station_name
        """

        export_query_to_file(
            conn,
            panel_query,
            args.output / "weekday_station_window_panel.csv",
            delimiter=",",
        )
        export_query_to_file(
            conn,
            leaderboard_query,
            args.output / "terminal_service_gap_leaderboard.tsv",
            delimiter="\t",
        )

        panel_rows = fetch_rows(conn, panel_query)
        leaderboard_rows = fetch_rows(conn, leaderboard_query)

    notes = render_release_notes(contract, panel_rows, leaderboard_rows)
    (args.output / "release_notes.md").write_text(notes, encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
