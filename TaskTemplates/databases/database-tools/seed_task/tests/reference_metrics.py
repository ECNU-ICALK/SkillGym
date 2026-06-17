from __future__ import annotations

import json
from collections import defaultdict
from pathlib import Path

import numpy as np
import pandas as pd

DATA_ROOT = Path("/root/data")

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

ROUND_COLUMNS = {
    "median_headway_minutes",
    "p90_headway_minutes",
    "max_headway_minutes",
    "service_gap_score",
}


def load_contract(data_root: Path = DATA_ROOT) -> dict:
    return json.loads((data_root / "release_contract.json").read_text(encoding="utf-8"))


def parse_gtfs_time(value: str) -> int:
    hours, minutes, seconds = [int(part) for part in value.split(":")]
    return hours * 3600 + minutes * 60 + seconds


def format_gtfs_time(seconds: float | int | object) -> str | None:
    if pd.isna(seconds):
        return None
    value = int(seconds)
    return f"{value // 3600:02d}:{(value % 3600) // 60:02d}:{value % 60:02d}"


def round_frame(frame: pd.DataFrame) -> pd.DataFrame:
    rounded = frame.copy()
    for column in rounded.columns:
        if column in ROUND_COLUMNS:
            rounded[column] = pd.to_numeric(rounded[column], errors="coerce").round(6)
    return rounded


def selected_routes(contract: dict) -> list[str]:
    return [row["route_id"] for row in contract["selected_routes"]]


def selected_route_frame(contract: dict) -> pd.DataFrame:
    return pd.DataFrame(contract["selected_routes"], columns=["route_family", "route_id"])


def load_routes(data_root: Path, contract: dict) -> pd.DataFrame:
    routes = pd.read_csv(data_root / "gtfs/routes.txt", dtype=str)
    routes = routes.merge(selected_route_frame(contract), on="route_id", how="inner")
    fallback = contract["output_conventions"]["route_short_name_fallback_to_route_id"]
    if fallback:
        routes["route_short_name"] = routes["route_short_name"].fillna(routes["route_id"])
        routes["route_short_name"] = routes["route_short_name"].replace("", pd.NA).fillna(
            routes["route_id"]
        )
    return routes


def load_stops(data_root: Path) -> pd.DataFrame:
    return pd.read_csv(data_root / "gtfs/stops.txt", dtype=str)


def load_trip_dates(data_root: Path, contract: dict) -> pd.DataFrame:
    trips = pd.read_csv(data_root / "gtfs/trips.txt", dtype=str)
    trips = trips[trips["route_id"].isin(selected_routes(contract))].copy()

    calendar = pd.read_csv(data_root / "gtfs/calendar.txt", dtype=str)
    calendar_dates = pd.read_csv(data_root / "gtfs/calendar_dates.txt", dtype=str)
    calendar["start_date"] = pd.to_datetime(calendar["start_date"], format="%Y%m%d")
    calendar["end_date"] = pd.to_datetime(calendar["end_date"], format="%Y%m%d")
    calendar_dates["date"] = pd.to_datetime(calendar_dates["date"], format="%Y%m%d")

    analysis_window = contract["analysis_window"]
    start_date = pd.Timestamp(analysis_window["start_date"])
    end_date = pd.Timestamp(analysis_window["end_date"])
    weekday_values = set(analysis_window["weekday_isodow_values"])
    weekday_columns = [
        "monday",
        "tuesday",
        "wednesday",
        "thursday",
        "friday",
        "saturday",
        "sunday",
    ]

    service_dates: dict[str, set[pd.Timestamp]] = defaultdict(set)
    for row in calendar.itertuples(index=False):
        current = row.start_date
        while current <= row.end_date:
            if current.isoweekday() in weekday_values and int(
                getattr(row, weekday_columns[current.dayofweek])
            ) == 1:
                service_dates[row.service_id].add(current)
            current += pd.Timedelta(days=1)

    for row in calendar_dates.itertuples(index=False):
        if row.date < start_date or row.date > end_date or row.date.isoweekday() not in weekday_values:
            continue
        if row.exception_type == "1" or row.exception_type == 1:
            service_dates[row.service_id].add(row.date)
        elif row.exception_type == "2" or row.exception_type == 2:
            service_dates[row.service_id].discard(row.date)

    rows: list[dict[str, object]] = []
    for trip in trips.itertuples(index=False):
        for service_date in sorted(
            service_date
            for service_date in service_dates[trip.service_id]
            if start_date <= service_date <= end_date
        ):
            rows.append(
                {
                    "route_id": trip.route_id,
                    "service_id": trip.service_id,
                    "trip_id": trip.trip_id,
                    "direction_id": int(trip.direction_id),
                    "service_date": service_date,
                }
            )

    return pd.DataFrame(rows)


def build_station_departures(data_root: Path = DATA_ROOT, contract: dict | None = None) -> pd.DataFrame:
    if contract is None:
        contract = load_contract(data_root)

    routes = load_routes(data_root, contract)[["route_family", "route_id", "route_short_name"]]
    trip_dates = load_trip_dates(data_root, contract)
    stop_times = pd.read_csv(data_root / "gtfs/stop_times.txt", dtype=str)
    stop_times["stop_sequence"] = stop_times["stop_sequence"].astype(int)
    stop_times["departure_seconds"] = stop_times["departure_time"].map(parse_gtfs_time)
    stops = load_stops(data_root)

    parents = stops[["stop_id", "stop_name"]].rename(
        columns={"stop_id": "parent_station_id", "stop_name": "parent_station_name"}
    )
    station_departures = (
        stop_times.merge(trip_dates, on="trip_id", how="inner")
        .merge(routes, on="route_id", how="left")
        .merge(stops[["stop_id", "stop_name", "parent_station"]], on="stop_id", how="left")
    )
    station_departures["parent_station_id"] = station_departures["parent_station"].fillna(
        station_departures["stop_id"]
    )
    station_departures = station_departures.merge(
        parents, on="parent_station_id", how="left"
    )
    station_departures["parent_station_name"] = station_departures[
        "parent_station_name"
    ].fillna(station_departures["stop_name"])
    window_specs = {
        row["window_name"]: (
            parse_gtfs_time(row["start_time"]),
            parse_gtfs_time(row["end_time"]),
        )
        for row in contract["time_windows"]
    }

    def map_window(seconds: int) -> str | None:
        for window_name, (start_seconds, end_seconds) in window_specs.items():
            if start_seconds <= seconds <= end_seconds:
                return window_name
        return None

    station_departures["window_name"] = station_departures["departure_seconds"].map(map_window)
    station_departures = station_departures.sort_values(
        ["service_date", "trip_id", "stop_sequence"]
    ).reset_index(drop=True)
    station_departures["stop_sequence_rank"] = (
        station_departures.groupby(["service_date", "trip_id"]).cumcount() + 1
    )
    return station_departures


def build_panel(station_departures: pd.DataFrame) -> pd.DataFrame:
    in_window = station_departures[station_departures["window_name"].notna()].copy()

    station_scope = in_window[
        [
            "route_family",
            "route_id",
            "route_short_name",
            "direction_id",
            "parent_station_id",
            "parent_station_name",
        ]
    ].drop_duplicates()
    active_route_dates = station_departures[
        [
            "route_family",
            "route_id",
            "route_short_name",
            "direction_id",
            "service_date",
        ]
    ].drop_duplicates()
    window_names = in_window[["window_name"]].drop_duplicates().reset_index(drop=True)

    active_route_dates["merge_key"] = 1
    station_scope["merge_key"] = 1
    panel_grid = (
        active_route_dates.merge(
            station_scope,
            on=["route_family", "route_id", "route_short_name", "direction_id", "merge_key"],
            how="inner",
        )
        .merge(window_names.assign(merge_key=1), on="merge_key", how="inner")
        .drop(columns="merge_key")
    )

    counts = (
        in_window.groupby(
            [
                "service_date",
                "route_family",
                "route_id",
                "route_short_name",
                "direction_id",
                "parent_station_id",
                "parent_station_name",
                "window_name",
            ],
            as_index=False,
        )
        .agg(
            scheduled_trip_count=("trip_id", "size"),
            first_departure_seconds=("departure_seconds", "min"),
            last_departure_seconds=("departure_seconds", "max"),
        )
    )

    panel = panel_grid.merge(
        counts,
        on=[
            "service_date",
            "route_family",
            "route_id",
            "route_short_name",
            "direction_id",
            "parent_station_id",
            "parent_station_name",
            "window_name",
        ],
        how="left",
    )
    panel["scheduled_trip_count"] = panel["scheduled_trip_count"].fillna(0).astype(int)
    panel["first_departure_local"] = panel["first_departure_seconds"].map(format_gtfs_time)
    panel["last_departure_local"] = panel["last_departure_seconds"].map(format_gtfs_time)
    panel = panel[PANEL_COLUMNS].sort_values(
        ["service_date", "route_id", "direction_id", "parent_station_name", "window_name"]
    )
    panel = panel.reset_index(drop=True)
    return panel


def build_leaderboard(station_departures: pd.DataFrame, contract: dict) -> pd.DataFrame:
    origin_events = station_departures[
        (station_departures["stop_sequence_rank"] == 1)
        & (station_departures["window_name"].notna())
    ].copy()

    terminal_scope = (
        origin_events.groupby(["route_id", "direction_id", "parent_station_id"], as_index=False)
        .agg(active_service_days=("service_date", "nunique"))
    )
    terminal_scope = terminal_scope[
        terminal_scope["active_service_days"]
        >= contract["terminal_origin_rules"]["candidate_min_active_service_days_in_analysis_window"]
    ][["route_id", "direction_id", "parent_station_id"]]

    origin_events = origin_events.merge(
        terminal_scope,
        on=["route_id", "direction_id", "parent_station_id"],
        how="inner",
    )

    rolling_days = int(contract["terminal_origin_rules"]["rolling_window_days_inclusive"])
    min_snapshot_days = int(contract["terminal_origin_rules"]["min_active_service_days_per_snapshot"])
    min_snapshot_departures = int(
        contract["terminal_origin_rules"]["min_scheduled_departure_count_per_snapshot"]
    )
    weights = contract["ranking_weights"]

    rows: list[dict[str, object]] = []
    for snapshot_text in contract["terminal_origin_rules"]["snapshot_dates"]:
        snapshot_date = pd.Timestamp(snapshot_text)
        lookback_start = snapshot_date - pd.Timedelta(days=rolling_days - 1)
        scoped = origin_events[
            origin_events["service_date"].between(lookback_start, snapshot_date)
        ].copy()

        for keys, group in scoped.groupby(
            [
                "route_family",
                "route_id",
                "route_short_name",
                "direction_id",
                "window_name",
                "parent_station_id",
                "parent_station_name",
            ]
        ):
            headways: list[float] = []
            departure_count = 0
            active_days = 0
            for _, day_frame in group.sort_values(
                ["service_date", "departure_seconds"]
            ).groupby("service_date"):
                active_days += 1
                departure_count += len(day_frame)
                if len(day_frame) >= 2:
                    headways.extend(
                        np.diff(np.sort(day_frame["departure_seconds"].to_numpy(dtype=float)))
                        / 60.0
                    )

            if (
                active_days < min_snapshot_days
                or departure_count < min_snapshot_departures
                or not headways
            ):
                continue

            headways_array = np.array(headways, dtype=float)
            median_headway = float(np.median(headways_array))
            p90_headway = float(np.quantile(headways_array, 0.9, method="linear"))
            max_headway = float(np.max(headways_array))
            score = (
                median_headway * weights["median_headway_minutes"]
                + p90_headway * weights["p90_headway_minutes"]
                + max_headway * weights["max_headway_minutes"]
            )
            rows.append(
                {
                    "snapshot_date": snapshot_date,
                    "route_family": keys[0],
                    "route_id": keys[1],
                    "route_short_name": keys[2],
                    "direction_id": keys[3],
                    "window_name": keys[4],
                    "terminal_station_id": keys[5],
                    "terminal_station_name": keys[6],
                    "active_service_days": active_days,
                    "scheduled_departure_count": departure_count,
                    "median_headway_minutes": median_headway,
                    "p90_headway_minutes": p90_headway,
                    "max_headway_minutes": max_headway,
                    "service_gap_score": score,
                }
            )

    leaderboard = pd.DataFrame(rows)
    if leaderboard.empty:
        return pd.DataFrame(columns=LEADERBOARD_COLUMNS)

    leaderboard = leaderboard.sort_values(
        [
            "snapshot_date",
            "route_id",
            "window_name",
            "service_gap_score",
            "max_headway_minutes",
            "p90_headway_minutes",
            "terminal_station_name",
            "terminal_station_id",
        ],
        ascending=[True, True, True, False, False, False, True, True],
    ).reset_index(drop=True)
    leaderboard["rank"] = (
        leaderboard.groupby(["snapshot_date", "route_id", "window_name"]).cumcount() + 1
    )
    leaderboard = leaderboard[LEADERBOARD_COLUMNS]
    return round_frame(leaderboard)


def expected_bundle(data_root: Path = DATA_ROOT) -> dict[str, pd.DataFrame]:
    contract = load_contract(data_root)
    station_departures = build_station_departures(data_root, contract)
    panel = build_panel(station_departures)
    leaderboard = build_leaderboard(station_departures, contract)
    return {
        "panel": panel,
        "leaderboard": leaderboard,
    }
