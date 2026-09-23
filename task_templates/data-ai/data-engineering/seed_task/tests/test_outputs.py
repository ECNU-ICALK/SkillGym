import csv
import json
import subprocess
from decimal import Decimal
from functools import lru_cache
from io import StringIO
from pathlib import Path

import pandas as pd


WORKSPACE = Path("/app/workspace")
DATA_DIR = WORKSPACE / "data"
OUTPUT_PATH = WORKSPACE / "output" / "summary.json"


def run(cmd: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(cmd, check=True, capture_output=True, text=True)


def clickhouse_scalar(query: str) -> str:
    return run(["clickhouse-client", "--query", query]).stdout.strip()


def clickhouse_rows(query: str) -> list[dict[str, str]]:
    result = run(["clickhouse-client", "--query", query, "--format", "CSVWithNames"])
    reader = csv.DictReader(StringIO(result.stdout))
    return list(reader)


def run_pipeline() -> None:
    subprocess.run(
        ["/bin/bash", "-lc", "cd /app/workspace && ./run_pipeline.sh"],
        check=True,
        text=True,
    )


def assert_decimal_text_equal(actual: str, expected: str, tolerance: str = "0") -> None:
    assert abs(Decimal(actual) - Decimal(expected)) <= Decimal(tolerance)


def normalize_trip_frame(path: Path, month: str) -> pd.DataFrame:
    frame = pd.read_parquet(path)
    if "Airport_fee" in frame.columns and "airport_fee" not in frame.columns:
        frame["airport_fee"] = frame["Airport_fee"]
    if "airport_fee" not in frame.columns:
        frame["airport_fee"] = pd.NA
    frame["source_month"] = month
    return frame[
        [
            "source_month",
            "VendorID",
            "tpep_pickup_datetime",
            "tpep_dropoff_datetime",
            "passenger_count",
            "trip_distance",
            "RatecodeID",
            "store_and_fwd_flag",
            "PULocationID",
            "DOLocationID",
            "payment_type",
            "fare_amount",
            "extra",
            "mta_tax",
            "tip_amount",
            "tolls_amount",
            "improvement_surcharge",
            "total_amount",
            "congestion_surcharge",
            "airport_fee",
        ]
    ].copy()


@lru_cache(maxsize=1)
def expected_artifacts() -> dict[str, object]:
    frames = [
        normalize_trip_frame(DATA_DIR / "yellow_tripdata_2023-01.parquet", "2023-01"),
        normalize_trip_frame(DATA_DIR / "yellow_tripdata_2023-02.parquet", "2023-02"),
    ]
    raw = pd.concat(frames, ignore_index=True)
    zones = pd.read_csv(DATA_DIR / "taxi_zone_lookup.csv", keep_default_na=False).rename(
        columns={
            "LocationID": "location_id",
            "Borough": "borough",
            "Zone": "zone",
            "service_zone": "service_zone",
        }
    )

    valid = raw.copy()
    valid = valid[valid["tpep_pickup_datetime"].notna()]
    valid = valid[valid["tpep_dropoff_datetime"].notna()]
    valid = valid[valid["trip_distance"].notna()]
    valid = valid[valid["fare_amount"].notna()]
    valid = valid[valid["total_amount"].notna()]
    valid = valid[valid["tpep_dropoff_datetime"] > valid["tpep_pickup_datetime"]]
    valid = valid[valid["trip_distance"] >= 0]
    valid = valid[valid["fare_amount"] >= 0]
    valid = valid[valid["total_amount"] >= 0]

    valid = valid.merge(
        zones.add_prefix("pickup_"),
        left_on="PULocationID",
        right_on="pickup_location_id",
        how="left",
    )
    valid = valid.merge(
        zones.add_prefix("dropoff_"),
        left_on="DOLocationID",
        right_on="dropoff_location_id",
        how="left",
    )
    valid = valid[valid["pickup_location_id"].notna()]
    valid = valid[valid["dropoff_location_id"].notna()]

    valid["service_date"] = pd.to_datetime(valid["tpep_pickup_datetime"]).dt.strftime("%Y-%m-%d")
    valid["service_month"] = pd.to_datetime(valid["tpep_pickup_datetime"]).dt.to_period("M").dt.to_timestamp().dt.strftime("%Y-%m-%d")
    valid["duration_minutes"] = (
        pd.to_datetime(valid["tpep_dropoff_datetime"]) - pd.to_datetime(valid["tpep_pickup_datetime"])
    ).dt.total_seconds() / 60.0
    valid["tip_pct"] = valid["tip_amount"] / valid["fare_amount"]
    valid.loc[valid["fare_amount"] <= 0, "tip_pct"] = pd.NA
    valid["is_airport_trip"] = (
        valid["pickup_service_zone"].isin(["Airports", "EWR"])
        | valid["dropoff_service_zone"].isin(["Airports", "EWR"])
    )

    daily = (
        valid.groupby(["service_date", "pickup_borough"], dropna=False)
        .agg(
            trip_count=("source_month", "size"),
            gross_revenue=("total_amount", "sum"),
            avg_trip_miles=("trip_distance", "mean"),
            avg_tip_pct=("tip_pct", "mean"),
            airport_trip_count=("is_airport_trip", "sum"),
        )
        .reset_index()
        .sort_values(["service_date", "pickup_borough"], kind="mergesort")
    )

    daily_records = [
        (
            row.service_date,
            row.pickup_borough,
            str(int(row.trip_count)),
            f"{row.gross_revenue:.2f}",
            f"{row.avg_trip_miles:.4f}",
            f"{0.0 if pd.isna(row.avg_tip_pct) else row.avg_tip_pct:.6f}",
            str(int(row.airport_trip_count)),
        )
        for row in daily.itertuples(index=False)
    ]

    route_metrics = (
        valid.groupby(["service_month", "pickup_zone", "dropoff_zone"], dropna=False)
        .agg(
            trip_count=("source_month", "size"),
            gross_revenue=("total_amount", "sum"),
            avg_duration_minutes=("duration_minutes", "mean"),
        )
        .reset_index()
    )
    route_metrics = route_metrics.sort_values(
        ["service_month", "gross_revenue", "trip_count", "pickup_zone", "dropoff_zone"],
        ascending=[True, False, False, True, True],
        kind="mergesort",
    )
    route_metrics["revenue_rank"] = route_metrics.groupby("service_month").cumcount() + 1
    route_metrics = route_metrics[route_metrics["revenue_rank"] <= 20]
    route_metrics = route_metrics.sort_values(
        ["service_month", "revenue_rank", "pickup_zone", "dropoff_zone"],
        kind="mergesort",
    )

    route_records = [
        (
            row.service_month,
            row.pickup_zone,
            row.dropoff_zone,
            str(int(row.trip_count)),
            f"{row.gross_revenue:.2f}",
            f"{row.avg_duration_minutes:.4f}",
            str(int(row.revenue_rank)),
        )
        for row in route_metrics.itertuples(index=False)
    ]

    return {
        "raw_trip_rows": len(raw),
        "accepted_trip_rows": len(valid),
        "daily_rows": len(daily_records),
        "top_rows": len(route_records),
        "daily_records": daily_records,
        "route_records": route_records,
    }


def test_pipeline_runs_successfully() -> None:
    run_pipeline()
    assert OUTPUT_PATH.is_file(), "summary.json was not created"


def test_summary_contract_and_counts() -> None:
    expected = expected_artifacts()
    summary = json.loads(OUTPUT_PATH.read_text(encoding="utf-8"))

    assert summary["source_months"] == ["2023-01", "2023-02"]
    assert summary["raw_trip_rows"] == expected["raw_trip_rows"]
    assert summary["accepted_trip_rows"] == expected["accepted_trip_rows"]
    assert summary["daily_borough_metrics_rows"] == expected["daily_rows"]
    assert summary["top_zone_routes_rows"] == expected["top_rows"]


def test_daily_borough_metrics_match_expected() -> None:
    expected_records = expected_artifacts()["daily_records"]
    actual_rows = clickhouse_rows(
        """
        SELECT
            toString(service_date) AS service_date,
            pickup_borough,
            toString(trip_count) AS trip_count,
            toString(gross_revenue) AS gross_revenue,
            toString(avg_trip_miles) AS avg_trip_miles,
            toString(avg_tip_pct) AS avg_tip_pct,
            toString(airport_trip_count) AS airport_trip_count
        FROM analytics.daily_borough_metrics
        ORDER BY service_date, pickup_borough
        """
    )
    actual_records = [
        (
            row["service_date"],
            row["pickup_borough"],
            row["trip_count"],
            row["gross_revenue"],
            row["avg_trip_miles"],
            row["avg_tip_pct"],
            row["airport_trip_count"],
        )
        for row in actual_rows
    ]
    assert len(actual_records) == len(expected_records)
    for actual, expected in zip(actual_records, expected_records, strict=True):
        assert actual[0] == expected[0]
        assert actual[1] == expected[1]
        assert actual[2] == expected[2]
        assert_decimal_text_equal(actual[3], expected[3], tolerance="0.01")
        assert_decimal_text_equal(actual[4], expected[4], tolerance="0.0001")
        assert_decimal_text_equal(actual[5], expected[5], tolerance="0.000001")
        assert actual[6] == expected[6]


def test_top_zone_routes_match_expected() -> None:
    expected_records = expected_artifacts()["route_records"]
    actual_rows = clickhouse_rows(
        """
        SELECT
            toString(service_month) AS service_month,
            pickup_zone,
            dropoff_zone,
            toString(trip_count) AS trip_count,
            toString(gross_revenue) AS gross_revenue,
            toString(avg_duration_minutes) AS avg_duration_minutes,
            toString(revenue_rank) AS revenue_rank_text
        FROM analytics.top_zone_routes
        ORDER BY service_month, revenue_rank, pickup_zone, dropoff_zone
        """
    )
    actual_records = [
        (
            row["service_month"],
            row["pickup_zone"],
            row["dropoff_zone"],
            row["trip_count"],
            row["gross_revenue"],
            row["avg_duration_minutes"],
            row["revenue_rank_text"],
        )
        for row in actual_rows
    ]
    assert len(actual_records) == len(expected_records)
    for actual, expected in zip(actual_records, expected_records, strict=True):
        assert actual[0] == expected[0]
        assert actual[1] == expected[1]
        assert actual[2] == expected[2]
        assert actual[3] == expected[3]
        assert_decimal_text_equal(actual[4], expected[4], tolerance="0.01")
        assert_decimal_text_equal(actual[5], expected[5], tolerance="0.0001")
        assert actual[6] == expected[6]


def test_pipeline_is_idempotent_and_loads_both_months() -> None:
    expected = expected_artifacts()
    OUTPUT_PATH.unlink(missing_ok=True)
    run_pipeline()

    assert clickhouse_scalar("SELECT uniqExact(source_month) FROM analytics.trips_raw") == "2"
    assert int(clickhouse_scalar("SELECT count() FROM analytics.trips_raw")) == expected["raw_trip_rows"]
    assert int(clickhouse_scalar("SELECT count() FROM analytics.top_zone_routes WHERE service_month = toDate('2023-01-01')")) == 20
    assert int(clickhouse_scalar("SELECT count() FROM analytics.top_zone_routes WHERE service_month = toDate('2023-02-01')")) == 20
    assert OUTPUT_PATH.is_file(), "summary.json was not recreated on rerun"
