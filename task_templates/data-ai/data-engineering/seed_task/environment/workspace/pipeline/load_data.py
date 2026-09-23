#!/usr/bin/env python3

import subprocess
from pathlib import Path


ROOT_DIR = Path(__file__).resolve().parents[1]
USER_FILES_DIR = Path("/var/lib/clickhouse/user_files/nyc_tlc_task")


def run_sql(sql: str) -> None:
    subprocess.run(
        ["clickhouse-client", "--query", sql],
        check=True,
        text=True,
    )


def load_zone_lookup() -> None:
    run_sql(
        """
        INSERT INTO analytics.zone_lookup
        SELECT
            toUInt16(LocationID),
            Borough,
            Zone,
            service_zone
        FROM file('/var/lib/clickhouse/user_files/nyc_tlc_task/taxi_zone_lookup.csv', 'CSVWithNames')
        """
    )


def load_month(month: str, parquet_name: str, airport_fee_column: str) -> None:
    sql = f"""
    INSERT INTO analytics.trips_raw
    SELECT
        '{month}' AS source_month,
        toUInt8OrNull(VendorID),
        tpep_pickup_datetime,
        tpep_dropoff_datetime,
        toFloat64OrNull(passenger_count),
        toFloat64OrNull(trip_distance),
        toUInt16OrNull(RatecodeID),
        nullIf(store_and_fwd_flag, ''),
        toUInt16OrNull(PULocationID),
        toUInt16OrNull(DOLocationID),
        toUInt8OrNull(payment_type),
        toFloat64OrNull(fare_amount),
        toFloat64OrNull(extra),
        toFloat64OrNull(mta_tax),
        toFloat64OrNull(tip_amount),
        toFloat64OrNull(tolls_amount),
        toFloat64OrNull(improvement_surcharge),
        toFloat64OrNull(total_amount),
        toFloat64OrNull(congestion_surcharge),
        toFloat64OrNull({airport_fee_column})
    FROM file('/var/lib/clickhouse/user_files/nyc_tlc_task/{parquet_name}', Parquet)
    """
    run_sql(sql)


def main() -> None:
    load_zone_lookup()
    load_month("2023-01", "yellow_tripdata_2023-01.parquet", "airport_fee")

    # BUG: February's parquet changed the airport fee column name to Airport_fee.
    # This loader still asks for airport_fee, swallows the failure, and continues.
    try:
        load_month("2023-02", "yellow_tripdata_2023-02.parquet", "airport_fee")
    except subprocess.CalledProcessError as exc:
        print("warning: February load failed but pipeline continued")
        print(exc)


if __name__ == "__main__":
    main()

