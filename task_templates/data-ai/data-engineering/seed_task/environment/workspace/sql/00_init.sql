CREATE DATABASE IF NOT EXISTS analytics;

DROP TABLE IF EXISTS analytics.top_zone_routes;
DROP TABLE IF EXISTS analytics.daily_borough_metrics;
DROP TABLE IF EXISTS analytics.trips_clean;
DROP TABLE IF EXISTS analytics.trips_raw;
DROP TABLE IF EXISTS analytics.zone_lookup;

CREATE TABLE analytics.zone_lookup
(
    location_id UInt16,
    borough String,
    zone String,
    service_zone String
)
ENGINE = MergeTree
ORDER BY location_id;

CREATE TABLE analytics.trips_raw
(
    source_month LowCardinality(String),
    vendor_id Nullable(UInt8),
    pickup_at Nullable(DateTime),
    dropoff_at Nullable(DateTime),
    passenger_count Nullable(Float64),
    trip_distance Nullable(Float64),
    ratecode_id Nullable(UInt16),
    store_and_fwd_flag Nullable(String),
    pu_location_id Nullable(UInt16),
    do_location_id Nullable(UInt16),
    payment_type Nullable(UInt8),
    fare_amount Nullable(Float64),
    extra Nullable(Float64),
    mta_tax Nullable(Float64),
    tip_amount Nullable(Float64),
    tolls_amount Nullable(Float64),
    improvement_surcharge Nullable(Float64),
    total_amount Nullable(Float64),
    congestion_surcharge Nullable(Float64),
    airport_fee Nullable(Float64)
)
ENGINE = MergeTree
PARTITION BY source_month
ORDER BY (source_month, pickup_at, pu_location_id, do_location_id)
SETTINGS allow_nullable_key = 1;
