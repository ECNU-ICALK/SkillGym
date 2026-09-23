DROP TABLE IF EXISTS analytics.daily_borough_metrics;

CREATE TABLE analytics.daily_borough_metrics
(
    service_date Date,
    pickup_borough String,
    trip_count UInt64,
    gross_revenue Decimal(18, 2),
    avg_trip_miles Decimal(18, 4),
    avg_tip_pct Decimal(18, 6),
    airport_trip_count UInt64
)
ENGINE = MergeTree
ORDER BY (service_date, pickup_borough);

INSERT INTO analytics.daily_borough_metrics
SELECT
    service_date,
    pickup_borough,
    count() AS trip_count,
    CAST(round(sum(gross_revenue), 2) AS Decimal(18, 2)) AS gross_revenue,
    CAST(round(avg(trip_distance), 4) AS Decimal(18, 4)) AS avg_trip_miles,
    CAST(round(avg(tip_pct), 6) AS Decimal(18, 6)) AS avg_tip_pct,
    countIf(pickup_service_zone IN ('Airports', 'EWR') OR dropoff_service_zone IN ('Airports', 'EWR')) AS airport_trip_count
FROM analytics.trips_clean
GROUP BY
    service_date,
    pickup_borough
ORDER BY
    service_date,
    pickup_borough;

