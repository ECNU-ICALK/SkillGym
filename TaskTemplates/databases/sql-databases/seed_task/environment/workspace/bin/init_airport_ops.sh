#!/usr/bin/env bash

set -euo pipefail

source /root/workspace/bin/common.sh
/root/workspace/bin/start_postgres.sh >/dev/null

if psql_db -Atqc "SELECT 1 FROM pg_tables WHERE schemaname = 'raw' AND tablename = 'dispatch_batch_a'" | grep -q '^1$'; then
    exit 0
fi

psql_db <<'SQL'
CREATE SCHEMA IF NOT EXISTS raw;

DROP TABLE IF EXISTS raw.dispatch_batch_a;
CREATE TABLE raw.dispatch_batch_a (
    VendorID INTEGER,
    tpep_pickup_datetime TIMESTAMP,
    tpep_dropoff_datetime TIMESTAMP,
    passenger_count DOUBLE PRECISION,
    trip_distance DOUBLE PRECISION,
    RatecodeID DOUBLE PRECISION,
    store_and_fwd_flag TEXT,
    PULocationID INTEGER,
    DOLocationID INTEGER,
    payment_type BIGINT,
    fare_amount DOUBLE PRECISION,
    extra DOUBLE PRECISION,
    mta_tax DOUBLE PRECISION,
    tip_amount DOUBLE PRECISION,
    tolls_amount DOUBLE PRECISION,
    improvement_surcharge DOUBLE PRECISION,
    total_amount DOUBLE PRECISION,
    congestion_surcharge DOUBLE PRECISION,
    airport_fee DOUBLE PRECISION,
    dispatch_channel TEXT
);

DROP TABLE IF EXISTS raw.dispatch_batch_b;
CREATE TABLE raw.dispatch_batch_b (
    VendorID INTEGER,
    pickup_ts TIMESTAMP,
    dropoff_ts TIMESTAMP,
    passenger_count DOUBLE PRECISION,
    trip_distance_mi DOUBLE PRECISION,
    RatecodeID DOUBLE PRECISION,
    store_and_fwd_flag TEXT,
    pickup_loc_id INTEGER,
    dropoff_loc_id INTEGER,
    payment_type BIGINT,
    fare_amount_usd DOUBLE PRECISION,
    extra DOUBLE PRECISION,
    mta_tax DOUBLE PRECISION,
    tip_amount DOUBLE PRECISION,
    tolls_amount DOUBLE PRECISION,
    improvement_surcharge DOUBLE PRECISION,
    total_amount_usd DOUBLE PRECISION,
    congestion_surcharge DOUBLE PRECISION,
    airport_fee_amount DOUBLE PRECISION,
    batch_loaded_at TEXT
);

DROP TABLE IF EXISTS raw.dispatch_batch_c;
CREATE TABLE raw.dispatch_batch_c (
    VendorID INTEGER,
    pickup_at TIMESTAMP,
    dropoff_at TIMESTAMP,
    passenger_count DOUBLE PRECISION,
    trip_distance DOUBLE PRECISION,
    RatecodeID DOUBLE PRECISION,
    store_and_fwd_flag TEXT,
    pickup_location_id INTEGER,
    dropoff_location_id INTEGER,
    payment_type BIGINT,
    fare_amount DOUBLE PRECISION,
    extra DOUBLE PRECISION,
    mta_tax DOUBLE PRECISION,
    tip_amount DOUBLE PRECISION,
    tolls_amount DOUBLE PRECISION,
    improvement_surcharge DOUBLE PRECISION,
    total_amount DOUBLE PRECISION,
    congestion_surcharge DOUBLE PRECISION,
    "Airport_fee" DOUBLE PRECISION,
    record_origin TEXT
);

DROP TABLE IF EXISTS raw.dispatch_batch_d;
CREATE TABLE raw.dispatch_batch_d (
    VendorID INTEGER,
    trip_begin_ts TIMESTAMP,
    trip_end_ts TIMESTAMP,
    passenger_count DOUBLE PRECISION,
    trip_miles DOUBLE PRECISION,
    RatecodeID DOUBLE PRECISION,
    store_and_fwd_flag TEXT,
    pu_location INTEGER,
    do_location INTEGER,
    payment_type BIGINT,
    fare_usd DOUBLE PRECISION,
    extra DOUBLE PRECISION,
    mta_tax DOUBLE PRECISION,
    tip_amount DOUBLE PRECISION,
    tolls_amount DOUBLE PRECISION,
    improvement_surcharge DOUBLE PRECISION,
    total_usd DOUBLE PRECISION,
    congestion_surcharge DOUBLE PRECISION,
    airport_fee_paid DOUBLE PRECISION,
    ops_batch TEXT
);

DROP TABLE IF EXISTS raw.zone_lookup;
CREATE TABLE raw.zone_lookup (
    LocationID INTEGER,
    Borough TEXT,
    Zone TEXT,
    service_zone TEXT
);
SQL

psql_db -c "\copy raw.dispatch_batch_a FROM '$DATA_DIR/dispatch_batch_a.csv' CSV HEADER"
psql_db -c "\copy raw.dispatch_batch_b FROM '$DATA_DIR/dispatch_batch_b.csv' CSV HEADER"
psql_db -c "\copy raw.dispatch_batch_c FROM '$DATA_DIR/dispatch_batch_c.csv' CSV HEADER"
psql_db -c "\copy raw.dispatch_batch_d FROM '$DATA_DIR/dispatch_batch_d.csv' CSV HEADER"
psql_db -c "\copy raw.zone_lookup FROM '$DATA_DIR/taxi_zone_lookup.csv' CSV HEADER"
