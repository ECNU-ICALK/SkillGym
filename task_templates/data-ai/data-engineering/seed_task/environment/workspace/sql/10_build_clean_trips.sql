DROP TABLE IF EXISTS analytics.trips_clean;

CREATE TABLE analytics.trips_clean
ENGINE = MergeTree
PARTITION BY source_month
ORDER BY (source_month, service_date, pickup_borough, pickup_zone, dropoff_zone)
SETTINGS allow_nullable_key = 1
AS
SELECT
    r.source_month,
    toDate(r.pickup_at) AS service_date,
    toDate(toStartOfMonth(r.pickup_at)) AS service_month,
    r.pickup_at,
    r.dropoff_at,
    r.trip_distance,
    dateDiff('second', r.pickup_at, r.dropoff_at) / 60.0 AS duration_minutes,
    r.fare_amount,
    r.tip_amount,
    r.total_amount AS gross_revenue,
    pu.borough AS pickup_borough,
    pu.zone AS pickup_zone,
    pu.service_zone AS pickup_service_zone,
    do.borough AS dropoff_borough,
    do.zone AS dropoff_zone,
    do.service_zone AS dropoff_service_zone,
    if(r.fare_amount > 0 AND r.tip_amount >= 0, r.tip_amount / r.fare_amount, NULL) AS tip_pct
FROM analytics.trips_raw AS r
LEFT JOIN analytics.zone_lookup AS pu
    ON r.pu_location_id = pu.location_id
LEFT JOIN analytics.zone_lookup AS do
    ON r.do_location_id = do.location_id
WHERE
    r.pickup_at IS NOT NULL
    AND r.dropoff_at IS NOT NULL
    AND r.dropoff_at > r.pickup_at
    AND r.trip_distance IS NOT NULL
    AND r.trip_distance >= 0
    AND r.fare_amount IS NOT NULL
    AND r.fare_amount >= 0
    AND r.total_amount IS NOT NULL
    AND r.total_amount >= 0
    AND pu.location_id IS NOT NULL
    AND do.location_id IS NOT NULL;
