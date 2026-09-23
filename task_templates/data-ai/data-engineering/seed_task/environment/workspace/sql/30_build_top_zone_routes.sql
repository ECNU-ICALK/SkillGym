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

