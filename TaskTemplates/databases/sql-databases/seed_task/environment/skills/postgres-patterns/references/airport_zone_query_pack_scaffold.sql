-- Airport rolling-mart scaffold for the postgres-patterns skill.
-- Fill values from the live analysis_contract.json and raw PostgreSQL tables.

-- Query 1: create contract config tables and clear prior analysis objects
CREATE SCHEMA IF NOT EXISTS analysis;

DROP MATERIALIZED VIEW IF EXISTS analysis.airport_zone_snapshot_leaderboard;
DROP MATERIALIZED VIEW IF EXISTS analysis.airport_zone_rolling_7d;
DROP MATERIALIZED VIEW IF EXISTS analysis.airport_zone_daily;
DROP MATERIALIZED VIEW IF EXISTS analysis.trip_fact_normalized;

DROP TABLE IF EXISTS analysis._cfg_airport_mapping;
DROP TABLE IF EXISTS analysis._cfg_period_rules;
DROP TABLE IF EXISTS analysis._cfg_period_airports;
DROP TABLE IF EXISTS analysis._cfg_snapshot_dates;

-- Query 2: materialize the normalized fact relation
CREATE MATERIALIZED VIEW analysis.trip_fact_normalized AS
WITH unified_trips AS (
    -- UNION ALL the four raw batches into canonical columns
),
enriched AS (
    -- derive service_date, pickup_hour, pickup_isodow, trip_duration_min, implied_mph
    -- and join pickup/dropoff zone lookup attributes
),
filtered AS (
    -- apply analysis window, weekday filter, trip validity rules, and same-zone short-hop rule
),
periodized AS (
    -- route morning_departures from pickup side and evening_arrivals from dropoff side
)
SELECT *
FROM periodized;

CREATE INDEX IF NOT EXISTS idx_trip_fact_period_zone_service_date
    ON analysis.trip_fact_normalized (period, zone_id, service_date);
CREATE INDEX IF NOT EXISTS idx_trip_fact_period_airport_zone_service_date
    ON analysis.trip_fact_normalized (period, airport_code, zone_id, service_date);

-- Query 3: materialize the zero-filled daily mart
CREATE MATERIALIZED VIEW analysis.airport_zone_daily AS
WITH zone_day AS (
    -- qualifying candidate-market zone-days and total_trip_count
),
scoped_airport_pairs AS (
    -- airport-zone pairs observed at least once in the analysis window
),
airport_zone_day AS (
    -- airport-linked counts by service_date, period, airport_code, zone_id
)
SELECT
    zone_day.service_date,
    zone_day.period,
    scoped_airport_pairs.airport_code,
    zone_day.zone_id,
    zone_day.zone_name,
    zone_day.borough,
    COALESCE(airport_zone_day.airport_trip_count, 0) AS airport_trip_count,
    zone_day.total_trip_count,
    COALESCE(airport_zone_day.airport_trip_count, 0)::double precision
        / NULLIF(zone_day.total_trip_count, 0) AS airport_trip_share
FROM zone_day
JOIN scoped_airport_pairs
  ON scoped_airport_pairs.period = zone_day.period
 AND scoped_airport_pairs.zone_id = zone_day.zone_id
LEFT JOIN airport_zone_day
  ON airport_zone_day.service_date = zone_day.service_date
 AND airport_zone_day.period = zone_day.period
 AND airport_zone_day.airport_code = scoped_airport_pairs.airport_code
 AND airport_zone_day.zone_id = zone_day.zone_id;

CREATE UNIQUE INDEX IF NOT EXISTS idx_airport_zone_daily_unique
    ON analysis.airport_zone_daily (service_date, period, airport_code, zone_id);
CREATE INDEX IF NOT EXISTS idx_airport_zone_daily_period_airport_service_date
    ON analysis.airport_zone_daily (period, airport_code, service_date, zone_id);

-- Query 4: materialize the rolling window relation
CREATE MATERIALIZED VIEW analysis.airport_zone_rolling_7d AS
WITH snapshot_rows AS (
    -- join configured snapshot dates to daily rows whose service_date falls in the rolling window
)
SELECT
    snapshot_date,
    period,
    airport_code,
    zone_id,
    zone_name,
    borough,
    COUNT(*) FILTER (WHERE airport_trip_count > 0) AS active_days_in_window,
    SUM(airport_trip_count) AS rolling_airport_trip_count,
    SUM(total_trip_count) AS rolling_total_trip_count,
    SUM(airport_trip_count)::double precision / NULLIF(SUM(total_trip_count), 0) AS rolling_airport_trip_share
FROM snapshot_rows
GROUP BY snapshot_date, period, airport_code, zone_id, zone_name, borough;

CREATE INDEX IF NOT EXISTS idx_airport_zone_rolling_partition
    ON analysis.airport_zone_rolling_7d (snapshot_date, period, airport_code, zone_id);

-- Query 5: materialize the ranked snapshot leaderboard
CREATE MATERIALIZED VIEW analysis.airport_zone_snapshot_leaderboard AS
WITH eligible_rows AS (
    SELECT *
    FROM analysis.airport_zone_rolling_7d
    WHERE active_days_in_window >= /* contract min_active_days_in_window */
),
scored_rows AS (
    SELECT
        eligible_rows.*,
        eligible_rows.rolling_airport_trip_count::double precision
            / NULLIF(MAX(eligible_rows.rolling_airport_trip_count) OVER (
                PARTITION BY eligible_rows.snapshot_date, eligible_rows.period, eligible_rows.airport_code
            ), 0) AS count_component,
        eligible_rows.rolling_airport_trip_share::double precision
            / NULLIF(MAX(eligible_rows.rolling_airport_trip_share) OVER (
                PARTITION BY eligible_rows.snapshot_date, eligible_rows.period, eligible_rows.airport_code
            ), 0) AS share_component,
        eligible_rows.active_days_in_window::double precision
            / NULLIF(MAX(eligible_rows.active_days_in_window) OVER (
                PARTITION BY eligible_rows.snapshot_date, eligible_rows.period, eligible_rows.airport_code
            ), 0) AS active_days_component
    FROM eligible_rows
),
weighted_rows AS (
    SELECT
        scored_rows.*,
        (
            /* count_weight */ * scored_rows.count_component
            + /* share_weight */ * scored_rows.share_component
            + /* active_days_weight */ * scored_rows.active_days_component
        ) AS rolling_opportunity_score
    FROM scored_rows
),
ranked_rows AS (
    SELECT
        weighted_rows.*,
        ROW_NUMBER() OVER (
            PARTITION BY weighted_rows.snapshot_date, weighted_rows.period, weighted_rows.airport_code
            ORDER BY
                weighted_rows.rolling_opportunity_score DESC,
                weighted_rows.rolling_airport_trip_count DESC,
                weighted_rows.rolling_airport_trip_share DESC,
                weighted_rows.zone_id ASC
        ) AS rank
    FROM weighted_rows
)
SELECT
    ranked_rows.snapshot_date,
    ranked_rows.period,
    ranked_rows.airport_code,
    ranked_rows.rank,
    ranked_rows.zone_id,
    ranked_rows.zone_name,
    ranked_rows.borough,
    ranked_rows.active_days_in_window,
    ranked_rows.rolling_airport_trip_count,
    ranked_rows.rolling_total_trip_count,
    ranked_rows.rolling_airport_trip_share,
    ranked_rows.rolling_opportunity_score
FROM ranked_rows
JOIN analysis._cfg_period_rules cfg
  ON cfg.period = ranked_rows.period
JOIN analysis._cfg_period_airports allowed
  ON allowed.period = ranked_rows.period
 AND allowed.airport_code = ranked_rows.airport_code
WHERE ranked_rows.rank <= cfg.top_k;

CREATE INDEX IF NOT EXISTS idx_airport_zone_snapshot_partition_rank
    ON analysis.airport_zone_snapshot_leaderboard (snapshot_date, period, airport_code, rank);

ANALYZE analysis.trip_fact_normalized;
ANALYZE analysis.airport_zone_daily;
ANALYZE analysis.airport_zone_rolling_7d;
ANALYZE analysis.airport_zone_snapshot_leaderboard;
