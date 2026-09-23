from __future__ import annotations

import json
import sqlite3
import textwrap
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import mannwhitneyu

DATA_ROOT = Path("/root/data")

SOURCE_COLUMNS = ["source_name", "path", "grain", "date_range", "key_fields", "note"]
QUALITY_COLUMNS = ["check_id", "dataset", "status", "metric_name", "metric_value", "note"]
SUMMARY_COLUMNS = [
    "period",
    "airport_code",
    "partner_zone_id",
    "partner_zone_name",
    "borough",
    "active_service_days",
    "total_airport_trips",
    "total_partner_zone_trips",
    "avg_airport_trip_share",
    "median_trip_duration_min",
    "median_total_amount",
    "weather_resilience_score",
    "opportunity_score",
]
WEATHER_COLUMNS = [
    "period",
    "airport_code",
    "weather_bucket",
    "avg_airport_trip_count",
    "avg_airport_trip_share",
    "avg_median_trip_duration_min",
    "n_zone_days",
    "vs_dry_u_test_pvalue",
    "effect_direction",
]
RANKING_COLUMNS = [
    "period",
    "airport_code",
    "recommendation_type",
    "rank",
    "zone_id",
    "zone_name",
    "borough",
    "active_service_days",
    "avg_airport_trip_count",
    "avg_airport_trip_share",
    "weather_resilience_score",
    "opportunity_score",
    "recommended_action",
    "reason_code",
]
ROUND_COLUMNS = {
    "avg_airport_trip_share",
    "median_trip_duration_min",
    "median_total_amount",
    "avg_airport_trip_count",
    "vs_dry_u_test_pvalue",
    "weather_resilience_score",
    "opportunity_score",
}

BATCH_QUERIES = {
    "dispatch_batch_a": """
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
        FROM dispatch_batch_a
    """,
    "dispatch_batch_b": """
        SELECT
            'dispatch_batch_b' AS source_batch,
            pickup_ts AS pickup_timestamp,
            dropoff_ts AS dropoff_timestamp,
            pickup_loc_id AS pickup_location_id,
            dropoff_loc_id AS dropoff_location_id,
            trip_distance_mi AS trip_distance_miles,
            fare_amount_usd,
            total_amount_usd,
            airport_fee_amount AS airport_fee_usd
        FROM dispatch_batch_b
    """,
    "dispatch_batch_c": """
        SELECT
            'dispatch_batch_c' AS source_batch,
            pickup_at AS pickup_timestamp,
            dropoff_at AS dropoff_timestamp,
            pickup_location_id,
            dropoff_location_id,
            trip_distance AS trip_distance_miles,
            fare_amount AS fare_amount_usd,
            total_amount AS total_amount_usd,
            Airport_fee AS airport_fee_usd
        FROM dispatch_batch_c
    """,
    "dispatch_batch_d": """
        SELECT
            'dispatch_batch_d' AS source_batch,
            trip_begin_ts AS pickup_timestamp,
            trip_end_ts AS dropoff_timestamp,
            pu_location AS pickup_location_id,
            do_location AS dropoff_location_id,
            trip_miles AS trip_distance_miles,
            fare_usd AS fare_amount_usd,
            total_usd AS total_amount_usd,
            airport_fee_paid AS airport_fee_usd
        FROM dispatch_batch_d
    """,
}


def load_contract(data_root: Path = DATA_ROOT) -> dict:
    return json.loads((data_root / "planning" / "analysis_contract.json").read_text(encoding="utf-8"))


def round_frame(frame: pd.DataFrame) -> pd.DataFrame:
    result = frame.copy()
    for column in result.columns:
        if column in ROUND_COLUMNS:
            result[column] = pd.to_numeric(result[column], errors="coerce").round(6)
    return result


def format_number(value: float | int | object, digits: int = 2) -> str:
    if pd.isna(value):
        return "n/a"
    return f"{float(value):.{digits}f}"


def load_zone_lookup(conn: sqlite3.Connection) -> pd.DataFrame:
    zone_lookup = pd.read_sql_query("SELECT * FROM zone_lookup", conn)
    zone_lookup.columns = [column.lower() for column in zone_lookup.columns]
    return zone_lookup


def load_weather(data_root: Path, contract: dict) -> pd.DataFrame:
    weather = pd.DataFrame(
        json.loads((data_root / "weather" / "airport_daily_weather.json").read_text(encoding="utf-8"))
    )
    weather["service_date"] = pd.to_datetime(weather["DATE"])
    weather["PRCP"] = pd.to_numeric(weather["PRCP"])
    weather["SNOW"] = pd.to_numeric(weather["SNOW"])

    buckets = contract["weather_buckets"]
    weather["weather_bucket"] = np.select(
        [
            weather["SNOW"] > float(buckets["snow_if_snow_gt_cm"]),
            weather["PRCP"] >= float(buckets["heavy_rain_if_prcp_ge_mm"]),
            weather["PRCP"] > float(buckets["light_precip_if_prcp_gt_mm"]),
        ],
        ["snow", "heavy_rain", "light_precip"],
        default=buckets["reference_bucket"],
    )
    return weather[
        ["service_date", "STATION", "NAME", "PRCP", "SNOW", "weather_bucket"]
    ].rename(columns={"STATION": "station_id", "NAME": "station_name"})


def load_unified_trips(conn: sqlite3.Connection) -> tuple[pd.DataFrame, dict[str, int]]:
    frames = []
    raw_counts: dict[str, int] = {}
    for batch_name, query in BATCH_QUERIES.items():
        frame = pd.read_sql_query(query, conn)
        frames.append(frame)
        raw_counts[batch_name] = int(frame.shape[0])

    trips = pd.concat(frames, ignore_index=True)
    trips["pickup_timestamp"] = pd.to_datetime(trips["pickup_timestamp"])
    trips["dropoff_timestamp"] = pd.to_datetime(trips["dropoff_timestamp"])
    trips["service_date"] = trips["pickup_timestamp"].dt.normalize()
    trips["pickup_hour"] = trips["pickup_timestamp"].dt.hour
    trips["weekday"] = trips["pickup_timestamp"].dt.weekday
    trips["trip_duration_min"] = (
        trips["dropoff_timestamp"] - trips["pickup_timestamp"]
    ).dt.total_seconds() / 60.0
    trips["implied_mph"] = np.where(
        trips["trip_duration_min"] > 0,
        trips["trip_distance_miles"] / (trips["trip_duration_min"] / 60.0),
        np.nan,
    )
    return trips, raw_counts


def apply_window_filter(trips: pd.DataFrame, contract: dict) -> pd.DataFrame:
    window = contract["analysis_window"]
    return trips[
        trips["service_date"].between(pd.Timestamp(window["start_date"]), pd.Timestamp(window["end_date"]))
        & trips["weekday"].isin(window["weekday_indexes"])
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
            period_trips["partner_zone_id"] = period_trips["pickup_location_id"]
            period_trips["airport_zone_id"] = period_trips["dropoff_location_id"]
            period_trips["partner_zone_name"] = period_trips["pickup_zone_name"]
            period_trips["borough"] = period_trips["pickup_borough"]
            period_trips["service_zone"] = period_trips["pickup_service_zone"]
        else:
            period_trips["partner_zone_id"] = period_trips["dropoff_location_id"]
            period_trips["airport_zone_id"] = period_trips["pickup_location_id"]
            period_trips["partner_zone_name"] = period_trips["dropoff_zone_name"]
            period_trips["borough"] = period_trips["dropoff_borough"]
            period_trips["service_zone"] = period_trips["dropoff_service_zone"]

        period_trips = period_trips[period_trips["partner_zone_id"].isin(candidate_ids)].copy()
        period_trips["period"] = period_name
        period_frames.append(period_trips)

        airport_trips = period_trips.copy()
        airport_trips["airport_code"] = airport_trips["airport_zone_id"].map(airport_zone_to_code)
        airport_trips = airport_trips[airport_trips["airport_code"].isin(config["airports"])].copy()
        airport_frames.append(airport_trips)

    return pd.concat(period_frames, ignore_index=True), pd.concat(airport_frames, ignore_index=True)


def build_zone_day_tables(
    period_trips: pd.DataFrame,
    airport_trips: pd.DataFrame,
    weather: pd.DataFrame,
    contract: dict,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    airport_code_to_station = {
        mapping["airport_code"]: mapping["station_id"] for mapping in contract["airport_mapping"]
    }

    partner_zone_day = (
        period_trips.groupby(
            ["period", "partner_zone_id", "partner_zone_name", "borough", "service_date"],
            as_index=False,
        )
        .size()
        .rename(columns={"size": "partner_trip_count"})
    )

    airport_zone_day = airport_trips.groupby(
        ["period", "airport_code", "partner_zone_id", "partner_zone_name", "borough", "service_date"],
        as_index=False,
    ).agg(
        airport_trip_count=("airport_code", "size"),
        median_trip_duration_min=("trip_duration_min", "median"),
        median_total_amount=("total_amount_usd", "median"),
    )

    observed_pairs = airport_zone_day[
        ["period", "airport_code", "partner_zone_id", "partner_zone_name", "borough"]
    ].drop_duplicates()

    zone_day = observed_pairs.merge(
        partner_zone_day,
        on=["period", "partner_zone_id", "partner_zone_name", "borough"],
        how="left",
    ).merge(
        airport_zone_day,
        on=[
            "period",
            "airport_code",
            "partner_zone_id",
            "partner_zone_name",
            "borough",
            "service_date",
        ],
        how="left",
    )

    zone_day["airport_trip_count"] = zone_day["airport_trip_count"].fillna(0)
    zone_day["airport_trip_share"] = zone_day["airport_trip_count"] / zone_day["partner_trip_count"]
    zone_day["station_id"] = zone_day["airport_code"].map(airport_code_to_station)
    zone_day = zone_day.merge(weather, on=["service_date", "station_id"], how="left")

    return partner_zone_day, zone_day


def calculate_weather_resilience(zone_day: pd.DataFrame, contract: dict) -> pd.DataFrame:
    reference_bucket = contract["weather_buckets"]["reference_bucket"]
    wet_buckets = set(contract["weather_resilience"]["wet_buckets"])
    cap = float(contract["weather_resilience"]["cap"])
    fallback = float(contract["weather_resilience"]["fallback_if_reference_zero"])

    rows = []
    for (period, airport_code, partner_zone_id), group in zone_day.groupby(
        ["period", "airport_code", "partner_zone_id"]
    ):
        dry_values = group.loc[group["weather_bucket"] == reference_bucket, "airport_trip_count"]
        wet_values = group.loc[group["weather_bucket"].isin(wet_buckets), "airport_trip_count"]

        if wet_values.empty:
            score = 1.0
        elif dry_values.empty or float(dry_values.mean()) == 0.0:
            score = fallback
        else:
            score = min(cap, float(wet_values.mean() / dry_values.mean()))

        rows.append(
            {
                "period": period,
                "airport_code": airport_code,
                "partner_zone_id": partner_zone_id,
                "weather_resilience_score": score,
            }
        )

    return pd.DataFrame(rows)


def build_period_summary(
    zone_day: pd.DataFrame,
    airport_trips: pd.DataFrame,
    contract: dict,
) -> pd.DataFrame:
    summary = zone_day.groupby(
        ["period", "airport_code", "partner_zone_id", "partner_zone_name", "borough"], as_index=False
    ).agg(
        active_service_days=("airport_trip_count", lambda values: int((values > 0).sum())),
        total_airport_trips=("airport_trip_count", "sum"),
        total_partner_zone_trips=("partner_trip_count", "sum"),
        avg_airport_trip_share=("airport_trip_share", "mean"),
    )

    trip_level_medians = airport_trips.groupby(
        ["period", "airport_code", "partner_zone_id"], as_index=False
    ).agg(
        median_trip_duration_min=("trip_duration_min", "median"),
        median_total_amount=("total_amount_usd", "median"),
    )

    summary = summary.merge(
        trip_level_medians,
        on=["period", "airport_code", "partner_zone_id"],
        how="left",
    ).merge(
        calculate_weather_resilience(zone_day, contract),
        on=["period", "airport_code", "partner_zone_id"],
        how="left",
    )

    scoring = contract["opportunity_score"]
    summary["count_component"] = summary.groupby(["period", "airport_code"])["total_airport_trips"].transform(
        lambda values: values / values.max() if values.max() else 0.0
    )
    summary["share_component"] = summary.groupby(["period", "airport_code"])[
        "avg_airport_trip_share"
    ].transform(lambda values: values / values.max() if values.max() else 0.0)
    summary["resilience_component"] = (
        summary["weather_resilience_score"] / scoring["normalize_resilience_by"]
    ).clip(upper=1.0)
    summary["opportunity_score"] = (
        scoring["count_weight"] * summary["count_component"]
        + scoring["share_weight"] * summary["share_component"]
        + scoring["resilience_weight"] * summary["resilience_component"]
    )

    summary = summary.sort_values(
        ["period", "airport_code", "opportunity_score", "avg_airport_trip_share", "total_airport_trips"],
        ascending=[True, True, False, False, False],
    ).reset_index(drop=True)

    return round_frame(summary)


def mann_whitney_pvalue(values: list[float], reference_values: list[float], alternative: str) -> float | None:
    if not values or not reference_values:
        return None
    try:
        return float(mannwhitneyu(values, reference_values, alternative=alternative).pvalue)
    except Exception:
        return None


def build_weather_sensitivity(zone_day: pd.DataFrame, contract: dict) -> pd.DataFrame:
    reference_bucket = contract["weather_buckets"]["reference_bucket"]
    alternative = contract["weather_effect_test"]["alternative"]

    rows = []
    for (period, airport_code), airport_group in zone_day.groupby(["period", "airport_code"]):
        reference_values = airport_group.loc[
            airport_group["weather_bucket"] == reference_bucket, "airport_trip_count"
        ].tolist()

        for weather_bucket_name, bucket_group in airport_group.groupby("weather_bucket"):
            values = bucket_group["airport_trip_count"].tolist()
            if weather_bucket_name == reference_bucket:
                pvalue = None
                effect_direction = "reference"
            else:
                pvalue = mann_whitney_pvalue(values, reference_values, alternative)
                bucket_mean = float(np.mean(values)) if values else 0.0
                reference_mean = float(np.mean(reference_values)) if reference_values else 0.0
                if bucket_mean > reference_mean:
                    effect_direction = "higher"
                elif bucket_mean < reference_mean:
                    effect_direction = "lower"
                else:
                    effect_direction = "no_change"

            rows.append(
                {
                    "period": period,
                    "airport_code": airport_code,
                    "weather_bucket": weather_bucket_name,
                    "avg_airport_trip_count": float(bucket_group["airport_trip_count"].mean()),
                    "avg_airport_trip_share": float(bucket_group["airport_trip_share"].mean()),
                    "avg_median_trip_duration_min": float(
                        bucket_group["median_trip_duration_min"].mean()
                    ),
                    "n_zone_days": int(bucket_group.shape[0]),
                    "vs_dry_u_test_pvalue": pvalue,
                    "effect_direction": effect_direction,
                }
            )

    return round_frame(
        pd.DataFrame(rows, columns=WEATHER_COLUMNS)
        .sort_values(["period", "airport_code", "weather_bucket"])
        .reset_index(drop=True)
    )


def assign_reason_codes(summary: pd.DataFrame, contract: dict) -> pd.Series:
    rules = contract["reason_code_rules"]
    stable_high_share = (
        summary["weather_resilience_score"].ge(rules["stable_high_share_min_resilience"])
        & summary["avg_airport_trip_share"].ge(rules["stable_high_share_min_avg_share"])
    )
    core_volume = summary["count_component"].ge(rules["core_volume_min_count_component"])

    return np.where(
        stable_high_share,
        rules["stable_high_share_code"],
        np.where(core_volume, rules["core_volume_code"], rules["share_pick_code"]),
    )


def build_rankings(summary: pd.DataFrame, contract: dict) -> pd.DataFrame:
    ranked = summary.copy()
    ranked["reason_code"] = assign_reason_codes(ranked, contract)
    ranked["avg_airport_trip_count"] = ranked["total_airport_trips"] / ranked["active_service_days"]

    ranking_frames: list[pd.DataFrame] = []
    min_service_dates = int(contract["ranking_eligibility"]["min_service_dates"])
    for period_name, config in contract["periods"].items():
        eligible = ranked[
            (ranked["period"] == period_name)
            & (ranked["airport_code"].isin(config["airports"]))
            & (ranked["active_service_days"] >= min_service_dates)
        ].copy()
        eligible = eligible.sort_values(
            [
                "airport_code",
                "opportunity_score",
                "avg_airport_trip_share",
                "total_airport_trips",
                "partner_zone_name",
            ],
            ascending=[True, False, False, False, True],
        )
        eligible["rank"] = eligible.groupby("airport_code").cumcount() + 1
        eligible = eligible[eligible["rank"] <= int(config["top_k"])].copy()
        eligible["recommendation_type"] = config["recommendation_type"]
        eligible["recommended_action"] = config["recommended_action"]
        ranking_frames.append(eligible)

    result = pd.concat(ranking_frames, ignore_index=True)[
        [
            "period",
            "airport_code",
            "recommendation_type",
            "rank",
            "partner_zone_id",
            "partner_zone_name",
            "borough",
            "active_service_days",
            "avg_airport_trip_count",
            "avg_airport_trip_share",
            "weather_resilience_score",
            "opportunity_score",
            "recommended_action",
            "reason_code",
        ]
    ].rename(columns={"partner_zone_id": "zone_id", "partner_zone_name": "zone_name"})
    return round_frame(result[RANKING_COLUMNS])


def build_source_inventory(data_root: Path = DATA_ROOT) -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "source_name": "trip_staging_db",
                "path": str(data_root / "trips" / "airport_partner_ops.db"),
                "grain": "trip-level rows across four staging tables plus zone lookup",
                "date_range": "2023-01-01 to 2023-02-07",
                "key_fields": (
                    "pickup/dropoff timestamps; pickup/dropoff location ids; distance; fare; total; airport fee"
                ),
                "note": "Primary trip fact source; dispatch_batch_a..d require field harmonization before analysis.",
            },
            {
                "source_name": "airport_daily_weather",
                "path": str(data_root / "weather" / "airport_daily_weather.json"),
                "grain": "airport-station by date",
                "date_range": "2023-01-01 to 2023-02-07",
                "key_fields": "DATE; STATION; NAME; PRCP; SNOW",
                "note": "Daily weather snapshots for JFK, LGA, and EWR stations used for bucket assignment.",
            },
            {
                "source_name": "analysis_contract",
                "path": str(data_root / "planning" / "analysis_contract.json"),
                "grain": "analysis configuration",
                "date_range": "2023-01-02 to 2023-02-07",
                "key_fields": "analysis_window; airport_mapping; periods; valid_trip_rules; output_contract",
                "note": "Defines scope, filters, thresholds, weather logic, scoring weights, and output contract.",
            },
            {
                "source_name": "reference_docs",
                "path": str(data_root / "reference"),
                "grain": "lookup and documentation files",
                "date_range": "N/A",
                "key_fields": "LocationID; Borough; Zone; service_zone",
                "note": "Includes taxi zone lookup CSV and trip record documentation PDFs for field interpretation.",
            },
        ],
        columns=SOURCE_COLUMNS,
    )


def build_quality_checks(
    raw_trip_count: int,
    window_trip_count: int,
    valid_trip_count: int,
    candidate_zone_count: int,
    weather_join_match_rate: float,
    summary: pd.DataFrame,
    rankings: pd.DataFrame,
    contract: dict,
) -> pd.DataFrame:
    required_recommendations = sum(
        len(config["airports"]) * int(config["top_k"]) for config in contract["periods"].values()
    )
    checks = [
        {
            "check_id": "QC01",
            "dataset": "trip_staging_db",
            "status": "PASS",
            "metric_name": "raw_trip_rows",
            "metric_value": raw_trip_count,
            "note": "Unioned row count across dispatch_batch_a..d before any date or validity filters.",
        },
        {
            "check_id": "QC02",
            "dataset": "trip_staging_db",
            "status": "PASS",
            "metric_name": "analysis_window_rows",
            "metric_value": window_trip_count,
            "note": "Trip rows inside the contract date window and weekday scope before validity filters.",
        },
        {
            "check_id": "QC03",
            "dataset": "trip_staging_db",
            "status": "PASS",
            "metric_name": "valid_trip_rows",
            "metric_value": valid_trip_count,
            "note": "Trip rows remaining after enforcing distance, fare, duration, speed, and short-hop rules.",
        },
        {
            "check_id": "QC04",
            "dataset": "candidate_market",
            "status": "PASS",
            "metric_name": "candidate_zone_count",
            "metric_value": candidate_zone_count,
            "note": "Eligible partner zones in Manhattan Yellow Zone after excluding contract-banlisted names.",
        },
        {
            "check_id": "QC05",
            "dataset": "airport_weather",
            "status": "PASS" if weather_join_match_rate == 1.0 else "WARN",
            "metric_name": "weather_join_match_rate",
            "metric_value": round(weather_join_match_rate, 6),
            "note": "Share of observed period-airport-zone-day rows that matched a weather station-day record.",
        },
        {
            "check_id": "QC06",
            "dataset": "period_summary",
            "status": "PASS" if bool((summary["total_airport_trips"] > 0).all()) else "FAIL",
            "metric_name": "summary_rows",
            "metric_value": int(summary.shape[0]),
            "note": "Summary scope keeps observed period-airport-zone combinations with airport-linked trips.",
        },
        {
            "check_id": "QC07",
            "dataset": "rankings",
            "status": "PASS" if int(rankings.shape[0]) == required_recommendations else "WARN",
            "metric_name": "selected_recommendations",
            "metric_value": int(rankings.shape[0]),
            "note": f"Required support slots from contract: {required_recommendations}.",
        },
    ]
    return pd.DataFrame(checks, columns=QUALITY_COLUMNS)


def build_query_pack(contract: dict) -> str:
    window = contract["analysis_window"]
    market = contract["candidate_market"]
    morning = contract["periods"]["morning_departures"]
    evening = contract["periods"]["evening_arrivals"]
    rules = contract["valid_trip_rules"]
    return textwrap.dedent(
        f"""\
        -- Query 1: harmonize the four staging batches into one reusable trip extract
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
            FROM dispatch_batch_a
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
            FROM dispatch_batch_b
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
                Airport_fee
            FROM dispatch_batch_c
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
            FROM dispatch_batch_d
        )
        SELECT *
        FROM unified_trips;

        -- Query 2: apply the contract date window, weekday scope, validity rules, and partner-zone filter
        WITH unified_trips AS (
            SELECT
                tpep_pickup_datetime AS pickup_timestamp,
                tpep_dropoff_datetime AS dropoff_timestamp,
                PULocationID AS pickup_location_id,
                DOLocationID AS dropoff_location_id,
                trip_distance AS trip_distance_miles,
                fare_amount AS fare_amount_usd,
                total_amount AS total_amount_usd
            FROM dispatch_batch_a
            UNION ALL
            SELECT pickup_ts, dropoff_ts, pickup_loc_id, dropoff_loc_id, trip_distance_mi, fare_amount_usd, total_amount_usd FROM dispatch_batch_b
            UNION ALL
            SELECT pickup_at, dropoff_at, pickup_location_id, dropoff_location_id, trip_distance, fare_amount, total_amount FROM dispatch_batch_c
            UNION ALL
            SELECT trip_begin_ts, trip_end_ts, pu_location, do_location, trip_miles, fare_usd, total_usd FROM dispatch_batch_d
        )
        SELECT COUNT(*) AS valid_trip_rows
        FROM unified_trips
        WHERE date(pickup_timestamp) BETWEEN date('{window["start_date"]}') AND date('{window["end_date"]}')
          AND CAST(strftime('%w', pickup_timestamp) AS INTEGER) BETWEEN 1 AND 5
          AND trip_distance_miles >= {rules["min_trip_distance_miles"]}
          AND fare_amount_usd >= {rules["min_fare_amount_usd"]}
          AND total_amount_usd >= {rules["min_total_amount_usd"]};

        -- Query 3: derive morning-departure airport-linked zone-day counts
        WITH unified_trips AS (
            SELECT tpep_pickup_datetime AS pickup_timestamp, tpep_dropoff_datetime AS dropoff_timestamp, PULocationID AS pickup_location_id, DOLocationID AS dropoff_location_id, trip_distance AS trip_distance_miles, fare_amount AS fare_amount_usd, total_amount AS total_amount_usd FROM dispatch_batch_a
            UNION ALL
            SELECT pickup_ts, dropoff_ts, pickup_loc_id, dropoff_loc_id, trip_distance_mi, fare_amount_usd, total_amount_usd FROM dispatch_batch_b
            UNION ALL
            SELECT pickup_at, dropoff_at, pickup_location_id, dropoff_location_id, trip_distance, fare_amount, total_amount FROM dispatch_batch_c
            UNION ALL
            SELECT trip_begin_ts, trip_end_ts, pu_location, do_location, trip_miles, fare_usd, total_usd FROM dispatch_batch_d
        ),
        valid_trips AS (
            SELECT
                *,
                CAST((julianday(dropoff_timestamp) - julianday(pickup_timestamp)) * 24.0 * 60.0 AS REAL) AS trip_duration_min,
                CASE
                    WHEN julianday(dropoff_timestamp) = julianday(pickup_timestamp) THEN NULL
                    ELSE trip_distance_miles / ((julianday(dropoff_timestamp) - julianday(pickup_timestamp)) * 24.0)
                END AS implied_mph
            FROM unified_trips
            WHERE date(pickup_timestamp) BETWEEN date('{window["start_date"]}') AND date('{window["end_date"]}')
              AND CAST(strftime('%w', pickup_timestamp) AS INTEGER) BETWEEN 1 AND 5
              AND trip_distance_miles >= {rules["min_trip_distance_miles"]}
              AND fare_amount_usd >= {rules["min_fare_amount_usd"]}
              AND total_amount_usd >= {rules["min_total_amount_usd"]}
        )
        SELECT
            date(vt.pickup_timestamp) AS service_date,
            vt.pickup_location_id AS partner_zone_id,
            zpu.Zone AS partner_zone_name,
            CASE vt.dropoff_location_id
                WHEN 1 THEN 'EWR'
                WHEN 132 THEN 'JFK'
                WHEN 138 THEN 'LGA'
            END AS airport_code,
            COUNT(*) AS airport_trip_count
        FROM valid_trips vt
        JOIN zone_lookup zpu ON zpu.LocationID = vt.pickup_location_id
        WHERE vt.trip_duration_min BETWEEN {rules["min_trip_duration_min"]} AND {rules["max_trip_duration_min"]}
          AND vt.implied_mph <= {rules["max_implied_mph"]}
          AND NOT (
              vt.pickup_location_id = vt.dropoff_location_id
              AND vt.trip_distance_miles < {rules["same_zone_short_hop_miles"]}
          )
          AND CAST(strftime('%H', vt.pickup_timestamp) AS INTEGER) BETWEEN {morning["pickup_hour_start"]} AND {morning["pickup_hour_end"]}
          AND zpu.Borough = '{market["boroughs"][0]}'
          AND zpu.service_zone = '{market["service_zones"][0]}'
          AND zpu.Zone NOT IN ('{market["exclude_zone_names"][0]}', '{market["exclude_zone_names"][1]}')
          AND vt.dropoff_location_id IN (1, 132, 138)
        GROUP BY 1, 2, 3, 4
        ORDER BY service_date, airport_code, airport_trip_count DESC;

        -- Query 4: derive evening-arrival airport-linked zone-day counts
        WITH unified_trips AS (
            SELECT tpep_pickup_datetime AS pickup_timestamp, tpep_dropoff_datetime AS dropoff_timestamp, PULocationID AS pickup_location_id, DOLocationID AS dropoff_location_id, trip_distance AS trip_distance_miles, fare_amount AS fare_amount_usd, total_amount AS total_amount_usd FROM dispatch_batch_a
            UNION ALL
            SELECT pickup_ts, dropoff_ts, pickup_loc_id, dropoff_loc_id, trip_distance_mi, fare_amount_usd, total_amount_usd FROM dispatch_batch_b
            UNION ALL
            SELECT pickup_at, dropoff_at, pickup_location_id, dropoff_location_id, trip_distance, fare_amount, total_amount FROM dispatch_batch_c
            UNION ALL
            SELECT trip_begin_ts, trip_end_ts, pu_location, do_location, trip_miles, fare_usd, total_usd FROM dispatch_batch_d
        ),
        valid_trips AS (
            SELECT
                *,
                CAST((julianday(dropoff_timestamp) - julianday(pickup_timestamp)) * 24.0 * 60.0 AS REAL) AS trip_duration_min,
                CASE
                    WHEN julianday(dropoff_timestamp) = julianday(pickup_timestamp) THEN NULL
                    ELSE trip_distance_miles / ((julianday(dropoff_timestamp) - julianday(pickup_timestamp)) * 24.0)
                END AS implied_mph
            FROM unified_trips
            WHERE date(pickup_timestamp) BETWEEN date('{window["start_date"]}') AND date('{window["end_date"]}')
              AND CAST(strftime('%w', pickup_timestamp) AS INTEGER) BETWEEN 1 AND 5
              AND trip_distance_miles >= {rules["min_trip_distance_miles"]}
              AND fare_amount_usd >= {rules["min_fare_amount_usd"]}
              AND total_amount_usd >= {rules["min_total_amount_usd"]}
        )
        SELECT
            date(vt.pickup_timestamp) AS service_date,
            vt.dropoff_location_id AS partner_zone_id,
            zdo.Zone AS partner_zone_name,
            CASE vt.pickup_location_id
                WHEN 132 THEN 'JFK'
                WHEN 138 THEN 'LGA'
            END AS airport_code,
            COUNT(*) AS airport_trip_count
        FROM valid_trips vt
        JOIN zone_lookup zdo ON zdo.LocationID = vt.dropoff_location_id
        WHERE vt.trip_duration_min BETWEEN {rules["min_trip_duration_min"]} AND {rules["max_trip_duration_min"]}
          AND vt.implied_mph <= {rules["max_implied_mph"]}
          AND NOT (
              vt.pickup_location_id = vt.dropoff_location_id
              AND vt.trip_distance_miles < {rules["same_zone_short_hop_miles"]}
          )
          AND CAST(strftime('%H', vt.pickup_timestamp) AS INTEGER) BETWEEN {evening["pickup_hour_start"]} AND {evening["pickup_hour_end"]}
          AND zdo.Borough = '{market["boroughs"][0]}'
          AND zdo.service_zone = '{market["service_zones"][0]}'
          AND zdo.Zone NOT IN ('{market["exclude_zone_names"][0]}', '{market["exclude_zone_names"][1]}')
          AND vt.pickup_location_id IN (132, 138)
        GROUP BY 1, 2, 3, 4
        ORDER BY service_date, airport_code, airport_trip_count DESC;

        -- Query 5: roll up observed service-day partner volume for airport-share denominators
        WITH unified_trips AS (
            SELECT tpep_pickup_datetime AS pickup_timestamp, PULocationID AS pickup_location_id, DOLocationID AS dropoff_location_id FROM dispatch_batch_a
            UNION ALL
            SELECT pickup_ts, pickup_loc_id, dropoff_loc_id FROM dispatch_batch_b
            UNION ALL
            SELECT pickup_at, pickup_location_id, dropoff_location_id FROM dispatch_batch_c
            UNION ALL
            SELECT trip_begin_ts, pu_location, do_location FROM dispatch_batch_d
        )
        SELECT
            date(pickup_timestamp) AS service_date,
            z.Zone AS partner_zone_name,
            COUNT(*) AS partner_trip_count
        FROM unified_trips ut
        JOIN zone_lookup z
          ON z.LocationID = ut.pickup_location_id
        WHERE z.Borough = '{market["boroughs"][0]}'
          AND z.service_zone = '{market["service_zones"][0]}'
          AND z.Zone NOT IN ('{market["exclude_zone_names"][0]}', '{market["exclude_zone_names"][1]}')
        GROUP BY 1, 2
        ORDER BY service_date, partner_trip_count DESC, partner_zone_name;
        """
    )


def build_analysis_brief(
    summary: pd.DataFrame,
    rankings: pd.DataFrame,
    weather_sensitivity: pd.DataFrame,
    contract: dict,
) -> str:
    def ranking_lines(period_name: str) -> str:
        subset = rankings[rankings["period"] == period_name].copy()
        lines = []
        for airport_code, group in subset.groupby("airport_code", sort=True):
            items = []
            for row in group.sort_values("rank").itertuples(index=False):
                items.append(
                    f"{row.zone_name} (rank {row.rank}, avg airport trips {format_number(row.avg_airport_trip_count)}, "
                    f"share {format_number(row.avg_airport_trip_share * 100, 1)}%, "
                    f"resilience {format_number(row.weather_resilience_score)})"
                )
            lines.append(f"- {airport_code}: {'; '.join(items)}")
        return "\n".join(lines)

    weather_notes = []
    for row in weather_sensitivity[
        weather_sensitivity["weather_bucket"] != contract["weather_buckets"]["reference_bucket"]
    ].itertuples(index=False):
        pvalue_text = format_number(row.vs_dry_u_test_pvalue, 4) if pd.notna(row.vs_dry_u_test_pvalue) else "n/a"
        weather_notes.append(
            f"- {row.period} / {row.airport_code} / {row.weather_bucket}: avg airport trip count "
            f"{format_number(row.avg_airport_trip_count)}, share {format_number(row.avg_airport_trip_share * 100, 1)}%, "
            f"effect {row.effect_direction}, Mann-Whitney p={pvalue_text}."
        )

    return textwrap.dedent(
        f"""\
# Airport Partner-Zone Opportunity Analysis

## Scope
Analysis window follows the contract: {contract['analysis_window']['start_date']} to {contract['analysis_window']['end_date']} on weekdays only. The output covers observed airport-linked period-airport-zone combinations and evaluates Manhattan Yellow Zone partner areas against airport demand windows.

## Morning departures
Final support list for departure feeder coverage, derived from the ranked period-airport-zone summary:
{ranking_lines('morning_departures')}

## Evening arrivals
Final support list for arrival return coverage, derived from the ranked period-airport-zone summary:
{ranking_lines('evening_arrivals')}

## Weather notes
Weather buckets were assigned from airport-station daily PRCP/SNOW snapshots and compared to the dry baseline.
{'\n'.join(weather_notes)}

## Method notes
- Four staging tables were harmonized to one trip schema before filtering or aggregation.
- Partner-zone totals use all filtered trips within the period window for the partner side of the trip; airport totals only count trips that match the contract airport mapping and direction.
- `active_service_days` counts dates with at least one airport-linked trip for the airport-zone pair; `avg_airport_trip_share` averages daily airport-trip share across that zone's observed service dates.
- Opportunity ranking combines normalized airport trip volume, average airport-trip share, and weather resilience using the contract weights and top-k limits.
"""
    ).strip() + "\n"


def expected_bundle(data_root: Path = DATA_ROOT) -> dict[str, object]:
    contract = load_contract(data_root)
    conn = sqlite3.connect(data_root / "trips" / "airport_partner_ops.db")
    try:
        zone_lookup = load_zone_lookup(conn)
        weather = load_weather(data_root, contract)
        trips, raw_counts = load_unified_trips(conn)
    finally:
        conn.close()

    raw_trip_count = int(sum(raw_counts.values()))
    window_trips = apply_window_filter(trips, contract)
    valid_trips = apply_analysis_filters(window_trips, contract)
    enriched = enrich_with_zone_names(valid_trips, zone_lookup)
    candidate_zones = get_candidate_zones(zone_lookup, contract)
    period_trips, airport_trips = build_period_tables(enriched, candidate_zones, contract)
    _, zone_day = build_zone_day_tables(period_trips, airport_trips, weather, contract)
    summary = build_period_summary(zone_day, airport_trips, contract)
    weather_sensitivity = build_weather_sensitivity(zone_day, contract)
    rankings = build_rankings(summary, contract)
    period_summary = round_frame(summary[SUMMARY_COLUMNS])
    weather_join_match_rate = float(zone_day["weather_bucket"].notna().mean()) if len(zone_day) else 1.0
    quality_checks = build_quality_checks(
        raw_trip_count=raw_trip_count,
        window_trip_count=int(len(window_trips)),
        valid_trip_count=int(len(valid_trips)),
        candidate_zone_count=int(len(candidate_zones)),
        weather_join_match_rate=weather_join_match_rate,
        summary=period_summary,
        rankings=rankings,
        contract=contract,
    )
    return {
        "source_inventory": build_source_inventory(data_root),
        "quality_checks": quality_checks,
        "period_summary": period_summary,
        "weather_sensitivity": weather_sensitivity,
        "rankings": rankings,
        "analysis_brief": build_analysis_brief(summary, rankings, weather_sensitivity, contract),
        "query_pack": build_query_pack(contract),
    }
