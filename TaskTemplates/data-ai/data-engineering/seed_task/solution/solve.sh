#!/usr/bin/env bash

set -euo pipefail

cat <<'EOF' > /app/workspace/pipeline/load_data.sh
#!/usr/bin/env bash

set -euo pipefail

clickhouse-client --query "
INSERT INTO analytics.zone_lookup
SELECT
    toUInt16(LocationID),
    Borough,
    Zone,
    service_zone
FROM file('nyc_tlc_task/taxi_zone_lookup.csv', 'CSVWithNames')
"

clickhouse-client --query "
INSERT INTO analytics.trips_raw
SELECT
    '2023-01' AS source_month,
    accurateCastOrNull(VendorID, 'Nullable(UInt8)'),
    accurateCastOrNull(tpep_pickup_datetime, 'Nullable(DateTime)'),
    accurateCastOrNull(tpep_dropoff_datetime, 'Nullable(DateTime)'),
    accurateCastOrNull(passenger_count, 'Nullable(Float64)'),
    accurateCastOrNull(trip_distance, 'Nullable(Float64)'),
    accurateCastOrNull(RatecodeID, 'Nullable(UInt16)'),
    nullIf(store_and_fwd_flag, ''),
    accurateCastOrNull(PULocationID, 'Nullable(UInt16)'),
    accurateCastOrNull(DOLocationID, 'Nullable(UInt16)'),
    accurateCastOrNull(payment_type, 'Nullable(UInt8)'),
    accurateCastOrNull(fare_amount, 'Nullable(Float64)'),
    accurateCastOrNull(extra, 'Nullable(Float64)'),
    accurateCastOrNull(mta_tax, 'Nullable(Float64)'),
    accurateCastOrNull(tip_amount, 'Nullable(Float64)'),
    accurateCastOrNull(tolls_amount, 'Nullable(Float64)'),
    accurateCastOrNull(improvement_surcharge, 'Nullable(Float64)'),
    accurateCastOrNull(total_amount, 'Nullable(Float64)'),
    accurateCastOrNull(congestion_surcharge, 'Nullable(Float64)'),
    accurateCastOrNull(airport_fee, 'Nullable(Float64)')
FROM file('nyc_tlc_task/yellow_tripdata_2023-01.parquet', Parquet)
"

clickhouse-client --query "
INSERT INTO analytics.trips_raw
SELECT
    '2023-02' AS source_month,
    accurateCastOrNull(VendorID, 'Nullable(UInt8)'),
    accurateCastOrNull(tpep_pickup_datetime, 'Nullable(DateTime)'),
    accurateCastOrNull(tpep_dropoff_datetime, 'Nullable(DateTime)'),
    accurateCastOrNull(passenger_count, 'Nullable(Float64)'),
    accurateCastOrNull(trip_distance, 'Nullable(Float64)'),
    accurateCastOrNull(RatecodeID, 'Nullable(UInt16)'),
    nullIf(store_and_fwd_flag, ''),
    accurateCastOrNull(PULocationID, 'Nullable(UInt16)'),
    accurateCastOrNull(DOLocationID, 'Nullable(UInt16)'),
    accurateCastOrNull(payment_type, 'Nullable(UInt8)'),
    accurateCastOrNull(fare_amount, 'Nullable(Float64)'),
    accurateCastOrNull(extra, 'Nullable(Float64)'),
    accurateCastOrNull(mta_tax, 'Nullable(Float64)'),
    accurateCastOrNull(tip_amount, 'Nullable(Float64)'),
    accurateCastOrNull(tolls_amount, 'Nullable(Float64)'),
    accurateCastOrNull(improvement_surcharge, 'Nullable(Float64)'),
    accurateCastOrNull(total_amount, 'Nullable(Float64)'),
    accurateCastOrNull(congestion_surcharge, 'Nullable(Float64)'),
    accurateCastOrNull(Airport_fee, 'Nullable(Float64)')
FROM file('nyc_tlc_task/yellow_tripdata_2023-02.parquet', Parquet)
"

echo "load_data.sh finished"
EOF

cat <<'EOF' > /app/workspace/sql/30_build_top_zone_routes.sql
DROP TABLE IF EXISTS analytics.top_zone_routes;

CREATE TABLE analytics.top_zone_routes
(
    service_month Date,
    pickup_zone String,
    dropoff_zone String,
    trip_count UInt64,
    gross_revenue Decimal(18, 2),
    avg_duration_minutes Decimal(18, 4),
    revenue_rank UInt32
)
ENGINE = MergeTree
ORDER BY (service_month, revenue_rank, pickup_zone, dropoff_zone);

INSERT INTO analytics.top_zone_routes
WITH route_metrics AS (
    SELECT
        service_month,
        pickup_zone,
        dropoff_zone,
        count() AS trip_count,
        CAST(round(sum(gross_revenue), 2) AS Decimal(18, 2)) AS gross_revenue,
        CAST(round(avg(duration_minutes), 4) AS Decimal(18, 4)) AS avg_duration_minutes
    FROM analytics.trips_clean
    GROUP BY
        service_month,
        pickup_zone,
        dropoff_zone
),
ranked_routes AS (
    SELECT
        service_month,
        pickup_zone,
        dropoff_zone,
        trip_count,
        gross_revenue,
        avg_duration_minutes,
        row_number() OVER (
            PARTITION BY service_month
            ORDER BY
                gross_revenue DESC,
                trip_count DESC,
                pickup_zone ASC,
                dropoff_zone ASC
        ) AS revenue_rank
    FROM route_metrics
)
SELECT
    service_month,
    pickup_zone,
    dropoff_zone,
    trip_count,
    gross_revenue,
    avg_duration_minutes,
    toUInt32(revenue_rank) AS revenue_rank
FROM ranked_routes
WHERE revenue_rank <= 20
ORDER BY
    service_month,
    revenue_rank,
    pickup_zone,
    dropoff_zone;
EOF

chmod +x /app/workspace/pipeline/load_data.sh
/app/workspace/run_pipeline.sh
