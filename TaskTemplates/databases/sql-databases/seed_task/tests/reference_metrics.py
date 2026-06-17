from __future__ import annotations

import json
import textwrap
from pathlib import Path

import numpy as np
import pandas as pd

DATA_ROOT = Path("/root/data")

DAILY_COLUMNS = [
    "service_date",
    "period",
    "airport_code",
    "zone_id",
    "zone_name",
    "borough",
    "airport_trip_count",
    "total_trip_count",
    "airport_trip_share",
]

LEADERBOARD_COLUMNS = [
    "snapshot_date",
    "period",
    "airport_code",
    "rank",
    "zone_id",
    "zone_name",
    "borough",
    "active_days_in_window",
    "rolling_airport_trip_count",
    "rolling_total_trip_count",
    "rolling_airport_trip_share",
    "rolling_opportunity_score",
]

ROUND_COLUMNS = {
    "airport_trip_share",
    "rolling_airport_trip_share",
    "rolling_opportunity_score",
}

BATCH_SPECS = {
    "dispatch_batch_a.csv": {
        "parse_dates": ["tpep_pickup_datetime", "tpep_dropoff_datetime"],
        "rename": {
            "tpep_pickup_datetime": "pickup_timestamp",
            "tpep_dropoff_datetime": "dropoff_timestamp",
            "PULocationID": "pickup_location_id",
            "DOLocationID": "dropoff_location_id",
            "trip_distance": "trip_distance_miles",
            "fare_amount": "fare_amount_usd",
            "total_amount": "total_amount_usd",
            "airport_fee": "airport_fee_usd",
        },
    },
    "dispatch_batch_b.csv": {
        "parse_dates": ["pickup_ts", "dropoff_ts"],
        "rename": {
            "pickup_ts": "pickup_timestamp",
            "dropoff_ts": "dropoff_timestamp",
            "pickup_loc_id": "pickup_location_id",
            "dropoff_loc_id": "dropoff_location_id",
            "trip_distance_mi": "trip_distance_miles",
            "fare_amount_usd": "fare_amount_usd",
            "total_amount_usd": "total_amount_usd",
            "airport_fee_amount": "airport_fee_usd",
        },
    },
    "dispatch_batch_c.csv": {
        "parse_dates": ["pickup_at", "dropoff_at"],
        "rename": {
            "pickup_at": "pickup_timestamp",
            "dropoff_at": "dropoff_timestamp",
            "pickup_location_id": "pickup_location_id",
            "dropoff_location_id": "dropoff_location_id",
            "trip_distance": "trip_distance_miles",
            "fare_amount": "fare_amount_usd",
            "total_amount": "total_amount_usd",
            "Airport_fee": "airport_fee_usd",
        },
    },
    "dispatch_batch_d.csv": {
        "parse_dates": ["trip_begin_ts", "trip_end_ts"],
        "rename": {
            "trip_begin_ts": "pickup_timestamp",
            "trip_end_ts": "dropoff_timestamp",
            "pu_location": "pickup_location_id",
            "do_location": "dropoff_location_id",
            "trip_miles": "trip_distance_miles",
            "fare_usd": "fare_amount_usd",
            "total_usd": "total_amount_usd",
            "airport_fee_paid": "airport_fee_usd",
        },
    },
}


def load_contract(data_root: Path = DATA_ROOT) -> dict:
    return json.loads((data_root / "analysis_contract.json").read_text(encoding="utf-8"))


def round_frame(frame: pd.DataFrame) -> pd.DataFrame:
    rounded = frame.copy()
    for column in rounded.columns:
        if column in ROUND_COLUMNS:
            rounded[column] = pd.to_numeric(rounded[column], errors="coerce").round(6)
    return rounded


def format_number(value: float | int | object, digits: int = 3) -> str:
    if pd.isna(value):
        return "n/a"
    return f"{float(value):.{digits}f}"


def load_zone_lookup(data_root: Path = DATA_ROOT) -> pd.DataFrame:
    zone_lookup = pd.read_csv(data_root / "taxi_zone_lookup.csv")
    zone_lookup.columns = [column.lower() for column in zone_lookup.columns]
    return zone_lookup


def load_unified_trips(data_root: Path = DATA_ROOT) -> pd.DataFrame:
    frames: list[pd.DataFrame] = []
    for filename, spec in BATCH_SPECS.items():
        frame = pd.read_csv(data_root / filename, parse_dates=spec["parse_dates"]).rename(
            columns=spec["rename"]
        )
        frame["source_batch"] = filename.removesuffix(".csv")
        frame = frame[
            [
                "source_batch",
                "pickup_timestamp",
                "dropoff_timestamp",
                "pickup_location_id",
                "dropoff_location_id",
                "trip_distance_miles",
                "fare_amount_usd",
                "total_amount_usd",
                "airport_fee_usd",
            ]
        ]
        frames.append(frame)

    trips = pd.concat(frames, ignore_index=True)
    trips["pickup_timestamp"] = pd.to_datetime(trips["pickup_timestamp"])
    trips["dropoff_timestamp"] = pd.to_datetime(trips["dropoff_timestamp"])
    trips["service_date"] = trips["pickup_timestamp"].dt.normalize()
    trips["pickup_hour"] = trips["pickup_timestamp"].dt.hour
    trips["pickup_isodow"] = trips["pickup_timestamp"].dt.isocalendar().day.astype(int)
    trips["trip_duration_min"] = (
        trips["dropoff_timestamp"] - trips["pickup_timestamp"]
    ).dt.total_seconds() / 60.0
    trips["implied_mph"] = np.where(
        trips["trip_duration_min"] > 0,
        trips["trip_distance_miles"] / (trips["trip_duration_min"] / 60.0),
        np.nan,
    )
    return trips


def apply_window_filter(trips: pd.DataFrame, contract: dict) -> pd.DataFrame:
    window = contract["analysis_window"]
    start = pd.Timestamp(window["start_date"])
    end = pd.Timestamp(window["end_date"])
    return trips[
        trips["service_date"].between(start, end)
        & trips["pickup_isodow"].isin(window["weekday_isodow_values"])
    ].copy()


def apply_analysis_filters(trips: pd.DataFrame, contract: dict) -> pd.DataFrame:
    rules = contract["valid_trip_rules"]
    filtered = trips[
        trips["pickup_location_id"].notna()
        & trips["dropoff_location_id"].notna()
        & trips["trip_distance_miles"].ge(rules["min_trip_distance_miles"])
        & trips["fare_amount_usd"].ge(rules["min_fare_amount_usd"])
        & trips["total_amount_usd"].ge(rules["min_total_amount_usd"])
        & trips["trip_duration_min"].between(
            rules["min_trip_duration_min"], rules["max_trip_duration_min"]
        )
        & trips["implied_mph"].le(rules["max_implied_mph"])
    ].copy()

    if rules["exclude_same_zone_short_hops"]:
        filtered = filtered[
            ~(
                (filtered["pickup_location_id"] == filtered["dropoff_location_id"])
                & filtered["trip_distance_miles"].lt(rules["same_zone_short_hop_miles"])
            )
        ].copy()

    return filtered


def enrich_with_zone_names(trips: pd.DataFrame, zone_lookup: pd.DataFrame) -> pd.DataFrame:
    enriched = trips.copy()
    for prefix, key in [("pickup", "pickup_location_id"), ("dropoff", "dropoff_location_id")]:
        zone_side = zone_lookup.rename(
            columns={
                "locationid": key,
                "borough": f"{prefix}_borough",
                "zone": f"{prefix}_zone_name",
                "service_zone": f"{prefix}_service_zone",
            }
        )
        enriched = enriched.merge(zone_side, on=key, how="left")
    return enriched


def get_candidate_zones(zone_lookup: pd.DataFrame, contract: dict) -> pd.DataFrame:
    market = contract["candidate_market"]
    return zone_lookup[
        zone_lookup["borough"].isin(market["boroughs"])
        & zone_lookup["service_zone"].isin(market["service_zones"])
        & ~zone_lookup["zone"].isin(market["exclude_zone_names"])
    ].copy()


def build_period_tables(
    trips: pd.DataFrame,
    candidate_zones: pd.DataFrame,
    contract: dict,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    airport_zone_to_code = {
        mapping["zone_id"]: mapping["airport_code"] for mapping in contract["airport_mapping"]
    }
    candidate_ids = set(candidate_zones["locationid"].tolist())

    period_frames: list[pd.DataFrame] = []
    airport_frames: list[pd.DataFrame] = []

    for period_name, config in contract["periods"].items():
        period_trips = trips[
            trips["pickup_hour"].between(
                config["pickup_hour_start"], config["pickup_hour_end"], inclusive="both"
            )
        ].copy()

        if config["direction"] == "to_airport":
            period_trips["zone_id"] = period_trips["pickup_location_id"]
            period_trips["zone_name"] = period_trips["pickup_zone_name"]
            period_trips["borough"] = period_trips["pickup_borough"]
            period_trips["service_zone"] = period_trips["pickup_service_zone"]
            period_trips["airport_zone_id"] = period_trips["dropoff_location_id"]
        else:
            period_trips["zone_id"] = period_trips["dropoff_location_id"]
            period_trips["zone_name"] = period_trips["dropoff_zone_name"]
            period_trips["borough"] = period_trips["dropoff_borough"]
            period_trips["service_zone"] = period_trips["dropoff_service_zone"]
            period_trips["airport_zone_id"] = period_trips["pickup_location_id"]

        period_trips = period_trips[period_trips["zone_id"].isin(candidate_ids)].copy()
        period_trips["period"] = period_name
        period_trips["airport_code"] = period_trips["airport_zone_id"].map(airport_zone_to_code)
        period_frames.append(period_trips)

        airport_trips = period_trips[
            period_trips["airport_code"].isin(config["airports"])
        ].copy()
        airport_frames.append(airport_trips)

    return pd.concat(period_frames, ignore_index=True), pd.concat(airport_frames, ignore_index=True)


def build_daily_mart(period_trips: pd.DataFrame, airport_trips: pd.DataFrame) -> pd.DataFrame:
    zone_day = (
        period_trips.groupby(
            ["service_date", "period", "zone_id", "zone_name", "borough"], as_index=False
        )
        .size()
        .rename(columns={"size": "total_trip_count"})
    )

    observed_pairs = airport_trips[
        ["period", "airport_code", "zone_id", "zone_name", "borough"]
    ].drop_duplicates()

    airport_zone_day = airport_trips.groupby(
        ["service_date", "period", "airport_code", "zone_id", "zone_name", "borough"],
        as_index=False,
    ).agg(airport_trip_count=("airport_code", "size"))

    panel = observed_pairs.merge(
        zone_day,
        on=["period", "zone_id", "zone_name", "borough"],
        how="left",
    ).merge(
        airport_zone_day,
        on=["service_date", "period", "airport_code", "zone_id", "zone_name", "borough"],
        how="left",
    )

    panel["airport_trip_count"] = panel["airport_trip_count"].fillna(0).astype(int)
    panel["airport_trip_share"] = panel["airport_trip_count"] / panel["total_trip_count"]
    panel = panel[DAILY_COLUMNS].sort_values(
        ["service_date", "period", "airport_code", "zone_id"]
    ).reset_index(drop=True)
    return round_frame(panel)


def build_snapshot_leaderboard(daily: pd.DataFrame, contract: dict) -> pd.DataFrame:
    rolling_window = int(contract["rolling_window"]["service_dates_in_window"])
    snapshots = [pd.Timestamp(value) for value in contract["rolling_window"]["snapshot_dates"]]
    min_active_days = int(contract["rolling_window"]["min_active_days_in_window"])
    frames: list[pd.DataFrame] = []
    for snapshot in snapshots:
        window_start = snapshot - pd.Timedelta(days=rolling_window - 1)
        scoped = daily[
            daily["service_date"].between(window_start, snapshot)
        ].copy()
        if scoped.empty:
            continue
        rolled = scoped.groupby(
            ["period", "airport_code", "zone_id", "zone_name", "borough"], as_index=False
        ).agg(
            active_days_in_window=("airport_trip_count", lambda values: int((values > 0).sum())),
            rolling_airport_trip_count=("airport_trip_count", "sum"),
            rolling_total_trip_count=("total_trip_count", "sum"),
        )
        rolled["rolling_airport_trip_share"] = (
            rolled["rolling_airport_trip_count"] / rolled["rolling_total_trip_count"]
        )
        rolled["snapshot_date"] = snapshot
        frames.append(rolled)

    snapshot_rows = pd.concat(frames, ignore_index=True)
    snapshot_rows = snapshot_rows[snapshot_rows["active_days_in_window"].ge(min_active_days)].copy()

    weights = contract["ranking_score"]
    snapshot_rows["count_component"] = snapshot_rows.groupby(
        ["snapshot_date", "period", "airport_code"]
    )["rolling_airport_trip_count"].transform(
        lambda values: values / values.max() if values.max() else 0.0
    )
    snapshot_rows["share_component"] = snapshot_rows.groupby(
        ["snapshot_date", "period", "airport_code"]
    )["rolling_airport_trip_share"].transform(
        lambda values: values / values.max() if values.max() else 0.0
    )
    snapshot_rows["active_days_component"] = snapshot_rows.groupby(
        ["snapshot_date", "period", "airport_code"]
    )["active_days_in_window"].transform(
        lambda values: values / values.max() if values.max() else 0.0
    )
    snapshot_rows["rolling_opportunity_score"] = (
        weights["count_weight"] * snapshot_rows["count_component"]
        + weights["share_weight"] * snapshot_rows["share_component"]
        + weights["active_days_weight"] * snapshot_rows["active_days_component"]
    )

    frames: list[pd.DataFrame] = []
    for period_name, config in contract["periods"].items():
        period_frame = snapshot_rows[
            (snapshot_rows["period"] == period_name)
            & (snapshot_rows["airport_code"].isin(config["airports"]))
        ].copy()
        period_frame = period_frame.sort_values(
            [
                "snapshot_date",
                "airport_code",
                "rolling_opportunity_score",
                "rolling_airport_trip_count",
                "rolling_airport_trip_share",
                "zone_id",
            ],
            ascending=[True, True, False, False, False, True],
        )
        period_frame["rank"] = period_frame.groupby(["snapshot_date", "airport_code"]).cumcount() + 1
        period_frame = period_frame[period_frame["rank"] <= int(config["top_k"])].copy()
        frames.append(period_frame)

    leaderboard = pd.concat(frames, ignore_index=True)[LEADERBOARD_COLUMNS]
    leaderboard = leaderboard.sort_values(
        ["snapshot_date", "period", "airport_code", "rank", "zone_id"]
    ).reset_index(drop=True)
    return round_frame(leaderboard)


def build_query_pack(contract: dict) -> str:
    window = contract["analysis_window"]
    rules = contract["valid_trip_rules"]
    snapshots = ", ".join(
        f"DATE '{value}'" for value in contract["rolling_window"]["snapshot_dates"]
    )
    rolling_window = int(contract["rolling_window"]["service_dates_in_window"])
    min_active_days = int(contract["rolling_window"]["min_active_days_in_window"])
    morning_top_k = int(contract["periods"]["morning_departures"]["top_k"])
    evening_top_k = int(contract["periods"]["evening_arrivals"]["top_k"])
    score = contract["ranking_score"]

    return textwrap.dedent(
        f"""\
        -- Query 1: build the normalized period-aware fact table
        CREATE SCHEMA IF NOT EXISTS analysis;
        DROP VIEW IF EXISTS analysis.airport_zone_snapshot_leaderboard CASCADE;
        DROP VIEW IF EXISTS analysis.airport_zone_rolling_7d CASCADE;
        DROP MATERIALIZED VIEW IF EXISTS analysis.airport_zone_daily CASCADE;
        DROP TABLE IF EXISTS analysis.trip_fact_normalized CASCADE;

        CREATE TABLE analysis.trip_fact_normalized AS
        WITH unified_trips AS (
            SELECT
                'dispatch_batch_a' AS source_batch,
                tpep_pickup_datetime AS pickup_timestamp,
                tpep_dropoff_datetime AS dropoff_timestamp,
                PULocationID AS pickup_location_id,
                DOLocationID AS dropoff_location_id,
                trip_distance AS trip_distance_miles,
                fare_amount AS fare_amount_usd,
                total_amount AS total_amount_usd,
                airport_fee AS airport_fee_usd
            FROM raw.dispatch_batch_a
            UNION ALL
            SELECT
                'dispatch_batch_b',
                pickup_ts,
                dropoff_ts,
                pickup_loc_id,
                dropoff_loc_id,
                trip_distance_mi,
                fare_amount_usd,
                total_amount_usd,
                airport_fee_amount
            FROM raw.dispatch_batch_b
            UNION ALL
            SELECT
                'dispatch_batch_c',
                pickup_at,
                dropoff_at,
                pickup_location_id,
                dropoff_location_id,
                trip_distance,
                fare_amount,
                total_amount,
                "Airport_fee"
            FROM raw.dispatch_batch_c
            UNION ALL
            SELECT
                'dispatch_batch_d',
                trip_begin_ts,
                trip_end_ts,
                pu_location,
                do_location,
                trip_miles,
                fare_usd,
                total_usd,
                airport_fee_paid
            FROM raw.dispatch_batch_d
        ),
        enriched AS (
            SELECT
                u.*,
                u.pickup_timestamp::date AS service_date,
                EXTRACT(HOUR FROM u.pickup_timestamp)::int AS pickup_hour,
                EXTRACT(ISODOW FROM u.pickup_timestamp)::int AS pickup_isodow,
                EXTRACT(EPOCH FROM (u.dropoff_timestamp - u.pickup_timestamp)) / 60.0 AS trip_duration_min,
                CASE
                    WHEN EXTRACT(EPOCH FROM (u.dropoff_timestamp - u.pickup_timestamp)) > 0
                    THEN u.trip_distance_miles / (EXTRACT(EPOCH FROM (u.dropoff_timestamp - u.pickup_timestamp)) / 3600.0)
                    ELSE NULL
                END AS implied_mph,
                pu.borough AS pickup_borough,
                pu.zone AS pickup_zone_name,
                pu.service_zone AS pickup_service_zone,
                dox.borough AS dropoff_borough,
                dox.zone AS dropoff_zone_name,
                dox.service_zone AS dropoff_service_zone
            FROM unified_trips u
            LEFT JOIN raw.zone_lookup pu
              ON pu.locationid = u.pickup_location_id
            LEFT JOIN raw.zone_lookup dox
              ON dox.locationid = u.dropoff_location_id
        ),
        filtered AS (
            SELECT *
            FROM enriched
            WHERE service_date BETWEEN DATE '{window["start_date"]}' AND DATE '{window["end_date"]}'
              AND pickup_isodow IN ({", ".join(str(v) for v in window["weekday_isodow_values"])})
              AND pickup_location_id IS NOT NULL
              AND dropoff_location_id IS NOT NULL
              AND trip_distance_miles >= {rules["min_trip_distance_miles"]}
              AND fare_amount_usd >= {rules["min_fare_amount_usd"]}
              AND total_amount_usd >= {rules["min_total_amount_usd"]}
              AND trip_duration_min BETWEEN {rules["min_trip_duration_min"]} AND {rules["max_trip_duration_min"]}
              AND implied_mph <= {rules["max_implied_mph"]}
              AND NOT (
                    {str(rules["exclude_same_zone_short_hops"]).upper()}
                AND pickup_location_id = dropoff_location_id
                AND trip_distance_miles < {rules["same_zone_short_hop_miles"]}
              )
        ),
        morning_departures AS (
            SELECT
                service_date,
                'morning_departures'::text AS period,
                pickup_location_id AS zone_id,
                pickup_zone_name AS zone_name,
                pickup_borough AS borough,
                CASE dropoff_location_id
                    WHEN 1 THEN 'EWR'
                    WHEN 132 THEN 'JFK'
                    WHEN 138 THEN 'LGA'
                    ELSE NULL
                END AS airport_code
            FROM filtered
            WHERE pickup_hour BETWEEN 6 AND 10
              AND pickup_borough = 'Manhattan'
              AND pickup_service_zone = 'Yellow Zone'
              AND pickup_zone_name NOT IN ('Outside of NYC', 'Unknown')
        ),
        evening_arrivals AS (
            SELECT
                service_date,
                'evening_arrivals'::text AS period,
                dropoff_location_id AS zone_id,
                dropoff_zone_name AS zone_name,
                dropoff_borough AS borough,
                CASE pickup_location_id
                    WHEN 132 THEN 'JFK'
                    WHEN 138 THEN 'LGA'
                    ELSE NULL
                END AS airport_code
            FROM filtered
            WHERE pickup_hour BETWEEN 17 AND 22
              AND dropoff_borough = 'Manhattan'
              AND dropoff_service_zone = 'Yellow Zone'
              AND dropoff_zone_name NOT IN ('Outside of NYC', 'Unknown')
        )
        SELECT service_date, period, zone_id, zone_name, borough, airport_code
        FROM morning_departures
        UNION ALL
        SELECT service_date, period, zone_id, zone_name, borough, airport_code
        FROM evening_arrivals;

        -- Query 2: add reusable indexes for fact-table scans
        CREATE INDEX idx_trip_fact_period_zone_date
            ON analysis.trip_fact_normalized (period, zone_id, service_date);
        CREATE INDEX idx_trip_fact_period_airport_zone_date
            ON analysis.trip_fact_normalized (period, airport_code, zone_id, service_date)
            WHERE airport_code IS NOT NULL;

        -- Query 3: materialize the zero-filled daily mart
        CREATE MATERIALIZED VIEW analysis.airport_zone_daily AS
        WITH zone_day AS (
            SELECT
                service_date,
                period,
                zone_id,
                zone_name,
                borough,
                COUNT(*)::bigint AS total_trip_count
            FROM analysis.trip_fact_normalized
            GROUP BY 1, 2, 3, 4, 5
        ),
        observed_pairs AS (
            SELECT DISTINCT
                period,
                airport_code,
                zone_id,
                zone_name,
                borough
            FROM analysis.trip_fact_normalized
            WHERE airport_code IS NOT NULL
        ),
        airport_zone_day AS (
            SELECT
                service_date,
                period,
                airport_code,
                zone_id,
                zone_name,
                borough,
                COUNT(*)::bigint AS airport_trip_count
            FROM analysis.trip_fact_normalized
            WHERE airport_code IS NOT NULL
            GROUP BY 1, 2, 3, 4, 5, 6
        )
        SELECT
            z.service_date,
            p.period,
            p.airport_code,
            p.zone_id,
            p.zone_name,
            p.borough,
            COALESCE(a.airport_trip_count, 0)::bigint AS airport_trip_count,
            z.total_trip_count,
            COALESCE(a.airport_trip_count, 0)::double precision / NULLIF(z.total_trip_count, 0) AS airport_trip_share
        FROM observed_pairs p
        JOIN zone_day z
          ON z.period = p.period
         AND z.zone_id = p.zone_id
         AND z.zone_name = p.zone_name
         AND z.borough = p.borough
        LEFT JOIN airport_zone_day a
          ON a.service_date = z.service_date
         AND a.period = p.period
         AND a.airport_code = p.airport_code
         AND a.zone_id = p.zone_id
         AND a.zone_name = p.zone_name
         AND a.borough = p.borough;

        CREATE INDEX idx_airport_zone_daily_lookup
            ON analysis.airport_zone_daily (period, airport_code, service_date, zone_id);
        CREATE INDEX idx_airport_zone_daily_zone_window
            ON analysis.airport_zone_daily (period, zone_id, service_date);

        -- Query 4: derive rolling 7-service-date metrics
        CREATE OR REPLACE VIEW analysis.airport_zone_rolling_7d AS
        SELECT
            service_date AS snapshot_date,
            period,
            airport_code,
            zone_id,
            zone_name,
            borough,
            SUM(airport_trip_count) OVER (
                PARTITION BY period, airport_code, zone_id
                ORDER BY service_date
                ROWS BETWEEN {rolling_window - 1} PRECEDING AND CURRENT ROW
            )::bigint AS rolling_airport_trip_count,
            SUM(total_trip_count) OVER (
                PARTITION BY period, airport_code, zone_id
                ORDER BY service_date
                ROWS BETWEEN {rolling_window - 1} PRECEDING AND CURRENT ROW
            )::bigint AS rolling_total_trip_count,
            SUM(CASE WHEN airport_trip_count > 0 THEN 1 ELSE 0 END) OVER (
                PARTITION BY period, airport_code, zone_id
                ORDER BY service_date
                ROWS BETWEEN {rolling_window - 1} PRECEDING AND CURRENT ROW
            )::bigint AS active_days_in_window,
            (
                SUM(airport_trip_count) OVER (
                    PARTITION BY period, airport_code, zone_id
                    ORDER BY service_date
                    ROWS BETWEEN {rolling_window - 1} PRECEDING AND CURRENT ROW
                )::double precision
                / NULLIF(
                    SUM(total_trip_count) OVER (
                        PARTITION BY period, airport_code, zone_id
                        ORDER BY service_date
                        ROWS BETWEEN {rolling_window - 1} PRECEDING AND CURRENT ROW
                    ),
                    0
                )
            ) AS rolling_airport_trip_share
        FROM analysis.airport_zone_daily;

        -- Query 5: rank snapshot rows for planner-facing leaderboard output
        CREATE OR REPLACE VIEW analysis.airport_zone_snapshot_leaderboard AS
        WITH scoped AS (
            SELECT *
            FROM analysis.airport_zone_rolling_7d
            WHERE snapshot_date IN ({snapshots})
              AND active_days_in_window >= {min_active_days}
        ),
        scored AS (
            SELECT
                snapshot_date,
                period,
                airport_code,
                zone_id,
                zone_name,
                borough,
                active_days_in_window,
                rolling_airport_trip_count,
                rolling_total_trip_count,
                rolling_airport_trip_share,
                (
                    {score["count_weight"]} * (
                        rolling_airport_trip_count::double precision
                        / NULLIF(MAX(rolling_airport_trip_count) OVER (
                            PARTITION BY snapshot_date, period, airport_code
                        ), 0)
                    )
                    + {score["share_weight"]} * (
                        rolling_airport_trip_share
                        / NULLIF(MAX(rolling_airport_trip_share) OVER (
                            PARTITION BY snapshot_date, period, airport_code
                        ), 0)
                    )
                    + {score["active_days_weight"]} * (
                        active_days_in_window::double precision
                        / NULLIF(MAX(active_days_in_window) OVER (
                            PARTITION BY snapshot_date, period, airport_code
                        ), 0)
                    )
                ) AS rolling_opportunity_score
            FROM scoped
        ),
        ranked AS (
            SELECT
                *,
                ROW_NUMBER() OVER (
                    PARTITION BY snapshot_date, period, airport_code
                    ORDER BY rolling_opportunity_score DESC,
                             rolling_airport_trip_count DESC,
                             rolling_airport_trip_share DESC,
                             zone_id ASC
                ) AS rank
            FROM scored
        )
        SELECT
            snapshot_date,
            period,
            airport_code,
            rank,
            zone_id,
            zone_name,
            borough,
            active_days_in_window,
            rolling_airport_trip_count,
            rolling_total_trip_count,
            rolling_airport_trip_share,
            rolling_opportunity_score
        FROM ranked
        WHERE (period = 'morning_departures' AND rank <= {morning_top_k})
           OR (period = 'evening_arrivals' AND rank <= {evening_top_k});
        """
    )


def build_benchmark_report(daily: pd.DataFrame, leaderboard: pd.DataFrame, contract: dict) -> str:
    lines = [
        "# Scope",
        f"- Analysis window: {contract['analysis_window']['start_date']} to {contract['analysis_window']['end_date']}.",
        f"- Rolling window: {contract['rolling_window']['service_dates_in_window']} observed service dates.",
        "",
        "# Daily mart",
        f"- Daily mart rows: {len(daily)}.",
        f"- Distinct airport-zone pairs: {daily[['period', 'airport_code', 'zone_id']].drop_duplicates().shape[0]}.",
        "",
        "# Snapshot leaderboard",
    ]

    for snapshot_date, group in leaderboard.groupby("snapshot_date", sort=True):
        lines.append(f"- {snapshot_date.date()}:")
        for _, row in group.sort_values(["period", "airport_code", "rank", "zone_id"]).iterrows():
            lines.append(
                "  - "
                f"{row['period']} / {row['airport_code']} rank {int(row['rank'])}: "
                f"{row['zone_name']} ({int(row['zone_id'])}), "
                f"rolling trips {int(row['rolling_airport_trip_count'])}, "
                f"share {format_number(row['rolling_airport_trip_share'])}, "
                f"score {format_number(row['rolling_opportunity_score'])}."
            )

    lines.extend(
        [
            "",
            "# Index strategy",
            "- Create a composite lookup index on the normalized fact table for repeated airport-zone window queries.",
            "- Create a composite lookup index on the daily mart so snapshot leaderboard queries can reuse the materialized day panel.",
        ]
    )
    return "\n".join(lines) + "\n"


def expected_bundle(data_root: Path = DATA_ROOT) -> dict[str, object]:
    contract = load_contract(data_root)
    zone_lookup = load_zone_lookup(data_root)
    trips = load_unified_trips(data_root)
    trips = apply_window_filter(trips, contract)
    trips = apply_analysis_filters(trips, contract)
    trips = enrich_with_zone_names(trips, zone_lookup)
    candidate_zones = get_candidate_zones(zone_lookup, contract)
    period_trips, airport_trips = build_period_tables(trips, candidate_zones, contract)
    daily = build_daily_mart(period_trips, airport_trips)
    leaderboard = build_snapshot_leaderboard(daily, contract)
    return {
        "daily": daily,
        "leaderboard": leaderboard,
        "query_pack": build_query_pack(contract),
        "benchmark_report": build_benchmark_report(daily, leaderboard, contract),
    }
