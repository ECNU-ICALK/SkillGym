#!/usr/bin/env python3

from __future__ import annotations

import argparse
import json
import subprocess
import tempfile
from io import StringIO
from pathlib import Path

import pandas as pd

PGHOST = "/tmp/sql-databases-pg"
PGPORT = "55433"
PGUSER = "postgres"
DB_NAME = "airport_ops_task"

DAILY_COLUMNS = [
    "service_date",
    "period",
    "airport_code",
    "zone_id",
    "zone_name",
    "borough",
    "airport_trip_count",
    "total_trip_count",
    "airport_trip_share",
]

LEADERBOARD_COLUMNS = [
    "snapshot_date",
    "period",
    "airport_code",
    "rank",
    "zone_id",
    "zone_name",
    "borough",
    "active_days_in_window",
    "rolling_airport_trip_count",
    "rolling_total_trip_count",
    "rolling_airport_trip_share",
    "rolling_opportunity_score",
]


def sql_quote(value: str) -> str:
    return "'" + value.replace("'", "''") + "'"


def sql_num(value: int | float) -> str:
    return str(value)


def sql_date(value: str) -> str:
    return f"DATE {sql_quote(value)}"


def psql_scalar(query: str) -> str:
    result = subprocess.run(
        [
            "psql",
            "-v",
            "ON_ERROR_STOP=1",
            "-Atq",
            "-h",
            PGHOST,
            "-p",
            PGPORT,
            "-U",
            PGUSER,
            "-d",
            DB_NAME,
            "-c",
            query,
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    return result.stdout.strip()


def query_to_frame(query: str) -> pd.DataFrame:
    result = subprocess.run(
        [
            "psql",
            "-v",
            "ON_ERROR_STOP=1",
            "-h",
            PGHOST,
            "-p",
            PGPORT,
            "-U",
            PGUSER,
            "-d",
            DB_NAME,
            "-c",
            f"COPY ({query}) TO STDOUT WITH CSV HEADER",
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    return pd.read_csv(StringIO(result.stdout))


def execute_query_pack(query_pack: str) -> None:
    with tempfile.NamedTemporaryFile("w", encoding="utf-8", suffix=".sql", delete=False) as fh:
        fh.write(query_pack)
        temp_path = Path(fh.name)
    try:
        subprocess.run(
            [
                "psql",
                "-v",
                "ON_ERROR_STOP=1",
                "-h",
                PGHOST,
                "-p",
                PGPORT,
                "-U",
                PGUSER,
                "-d",
                DB_NAME,
                "-f",
                str(temp_path),
            ],
            check=True,
            capture_output=True,
            text=True,
        )
    finally:
        temp_path.unlink(missing_ok=True)


def build_query_pack(contract: dict) -> str:
    prefix = contract["output_contract"]["query_pack_comment_prefix"]
    window = contract["analysis_window"]
    market = contract["candidate_market"]
    mapping = contract["airport_mapping"]
    periods = contract["periods"]
    rules = contract["valid_trip_rules"]
    rolling = contract["rolling_window"]
    ranking = contract["ranking_score"]

    weekday_values = ", ".join(str(int(v)) for v in window["weekday_isodow_values"])
    borough_values = ", ".join(sql_quote(v) for v in market["boroughs"])
    service_zone_values = ", ".join(sql_quote(v) for v in market["service_zones"])
    exclude_zone_values = ", ".join(sql_quote(v) for v in market["exclude_zone_names"])

    airport_mapping_values = ",\n        ".join(
        f"({sql_quote(m['airport_code'])}, {int(m['zone_id'])})" for m in mapping
    )

    period_rule_values = ",\n        ".join(
        (
            f"({sql_quote(period)}, {sql_quote(cfg['direction'])}, "
            f"{int(cfg['pickup_hour_start'])}, {int(cfg['pickup_hour_end'])}, {int(cfg['top_k'])})"
        )
        for period, cfg in periods.items()
    )

    period_airport_values = ",\n        ".join(
        f"({sql_quote(period)}, {sql_quote(airport_code)})"
        for period, cfg in periods.items()
        for airport_code in cfg["airports"]
    )

    snapshot_values = ",\n        ".join(
        f"({sql_date(snapshot)})" for snapshot in rolling["snapshot_dates"]
    )

    window_days = int(rolling["service_dates_in_window"])
    window_back_days = window_days - 1

    if rules.get("exclude_same_zone_short_hops", False):
        short_hop_clause = (
            "AND NOT (\n"
            "      e.pickup_location_id = e.dropoff_location_id\n"
            f"      AND e.trip_distance_miles < {sql_num(rules['same_zone_short_hop_miles'])}\n"
            "  )"
        )
    else:
        short_hop_clause = ""

    return f"""\
{prefix}1: setup contract tables and clear prior analysis objects
CREATE SCHEMA IF NOT EXISTS analysis;

DROP MATERIALIZED VIEW IF EXISTS analysis.airport_zone_snapshot_leaderboard;
DROP MATERIALIZED VIEW IF EXISTS analysis.airport_zone_rolling_7d;
DROP MATERIALIZED VIEW IF EXISTS analysis.airport_zone_daily;
DROP MATERIALIZED VIEW IF EXISTS analysis.trip_fact_normalized;

DROP TABLE IF EXISTS analysis._cfg_airport_mapping;
DROP TABLE IF EXISTS analysis._cfg_period_rules;
DROP TABLE IF EXISTS analysis._cfg_period_airports;
DROP TABLE IF EXISTS analysis._cfg_snapshot_dates;

CREATE TABLE analysis._cfg_airport_mapping (
    airport_code TEXT NOT NULL,
    zone_id INTEGER NOT NULL PRIMARY KEY
);

INSERT INTO analysis._cfg_airport_mapping (airport_code, zone_id)
VALUES
        {airport_mapping_values};

CREATE TABLE analysis._cfg_period_rules (
    period TEXT PRIMARY KEY,
    direction TEXT NOT NULL,
    pickup_hour_start INTEGER NOT NULL,
    pickup_hour_end INTEGER NOT NULL,
    top_k INTEGER NOT NULL
);

INSERT INTO analysis._cfg_period_rules (
    period,
    direction,
    pickup_hour_start,
    pickup_hour_end,
    top_k
)
VALUES
        {period_rule_values};

CREATE TABLE analysis._cfg_period_airports (
    period TEXT NOT NULL,
    airport_code TEXT NOT NULL,
    PRIMARY KEY (period, airport_code)
);

INSERT INTO analysis._cfg_period_airports (period, airport_code)
VALUES
        {period_airport_values};

CREATE TABLE analysis._cfg_snapshot_dates (
    snapshot_date DATE PRIMARY KEY
);

INSERT INTO analysis._cfg_snapshot_dates (snapshot_date)
VALUES
        {snapshot_values};

{prefix}2: create the normalized fact layer from the four raw dispatch batches
CREATE MATERIALIZED VIEW analysis.trip_fact_normalized AS
WITH candidate_zones AS (
    SELECT
        z.locationid,
        z.borough,
        z.zone,
        z.service_zone
    FROM raw.zone_lookup z
    WHERE z.borough IN ({borough_values})
      AND z.service_zone IN ({service_zone_values})
      AND z.zone NOT IN ({exclude_zone_values})
),
unified_trips AS (
    SELECT
        'dispatch_batch_a'::text AS source_batch,
        tpep_pickup_datetime AS pickup_timestamp,
        tpep_dropoff_datetime AS dropoff_timestamp,
        PULocationID AS pickup_location_id,
        DOLocationID AS dropoff_location_id,
        trip_distance AS trip_distance_miles,
        fare_amount AS fare_amount_usd,
        total_amount AS total_amount_usd,
        airport_fee AS airport_fee_usd
    FROM raw.dispatch_batch_a
    UNION ALL
    SELECT
        'dispatch_batch_b'::text AS source_batch,
        pickup_ts AS pickup_timestamp,
        dropoff_ts AS dropoff_timestamp,
        pickup_loc_id AS pickup_location_id,
        dropoff_loc_id AS dropoff_location_id,
        trip_distance_mi AS trip_distance_miles,
        fare_amount_usd,
        total_amount_usd,
        airport_fee_amount AS airport_fee_usd
    FROM raw.dispatch_batch_b
    UNION ALL
    SELECT
        'dispatch_batch_c'::text AS source_batch,
        pickup_at AS pickup_timestamp,
        dropoff_at AS dropoff_timestamp,
        pickup_location_id,
        dropoff_location_id,
        trip_distance AS trip_distance_miles,
        fare_amount AS fare_amount_usd,
        total_amount AS total_amount_usd,
        "Airport_fee" AS airport_fee_usd
    FROM raw.dispatch_batch_c
    UNION ALL
    SELECT
        'dispatch_batch_d'::text AS source_batch,
        trip_begin_ts AS pickup_timestamp,
        trip_end_ts AS dropoff_timestamp,
        pu_location AS pickup_location_id,
        do_location AS dropoff_location_id,
        trip_miles AS trip_distance_miles,
        fare_usd AS fare_amount_usd,
        total_usd AS total_amount_usd,
        airport_fee_paid AS airport_fee_usd
    FROM raw.dispatch_batch_d
),
enriched AS (
    SELECT
        u.source_batch,
        u.pickup_timestamp,
        u.dropoff_timestamp,
        u.pickup_location_id,
        u.dropoff_location_id,
        u.trip_distance_miles,
        u.fare_amount_usd,
        u.total_amount_usd,
        u.airport_fee_usd,
        u.pickup_timestamp::date AS service_date,
        EXTRACT(HOUR FROM u.pickup_timestamp)::int AS pickup_hour,
        EXTRACT(ISODOW FROM u.pickup_timestamp)::int AS pickup_isodow,
        EXTRACT(EPOCH FROM (u.dropoff_timestamp - u.pickup_timestamp)) / 60.0 AS trip_duration_min,
        CASE
            WHEN EXTRACT(EPOCH FROM (u.dropoff_timestamp - u.pickup_timestamp)) > 0
            THEN u.trip_distance_miles
                 / (EXTRACT(EPOCH FROM (u.dropoff_timestamp - u.pickup_timestamp)) / 3600.0)
            ELSE NULL
        END AS implied_mph,
        pu.borough AS pickup_borough,
        pu.zone AS pickup_zone_name,
        pu.service_zone AS pickup_service_zone,
        dox.borough AS dropoff_borough,
        dox.zone AS dropoff_zone_name,
        dox.service_zone AS dropoff_service_zone
    FROM unified_trips u
    LEFT JOIN raw.zone_lookup pu
      ON pu.locationid = u.pickup_location_id
    LEFT JOIN raw.zone_lookup dox
      ON dox.locationid = u.dropoff_location_id
)
SELECT
    e.source_batch,
    e.pickup_timestamp,
    e.dropoff_timestamp,
    e.pickup_location_id,
    e.dropoff_location_id,
    e.trip_distance_miles,
    e.fare_amount_usd,
    e.total_amount_usd,
    e.airport_fee_usd,
    e.service_date,
    e.pickup_hour,
    e.pickup_isodow,
    e.trip_duration_min,
    e.implied_mph,
    e.pickup_borough,
    e.pickup_zone_name,
    e.pickup_service_zone,
    e.dropoff_borough,
    e.dropoff_zone_name,
    e.dropoff_service_zone
FROM enriched e
WHERE e.service_date BETWEEN {sql_date(window["start_date"])} AND {sql_date(window["end_date"])}
  AND e.pickup_isodow IN ({weekday_values})
  AND e.pickup_location_id IS NOT NULL
  AND e.dropoff_location_id IS NOT NULL
  AND e.trip_distance_miles >= {sql_num(rules["min_trip_distance_miles"])}
  AND e.fare_amount_usd >= {sql_num(rules["min_fare_amount_usd"])}
  AND e.total_amount_usd >= {sql_num(rules["min_total_amount_usd"])}
  AND e.trip_duration_min BETWEEN {sql_num(rules["min_trip_duration_min"])} AND {sql_num(rules["max_trip_duration_min"])}
  AND e.implied_mph <= {sql_num(rules["max_implied_mph"])}
  {short_hop_clause}
  AND (
      e.pickup_location_id IN (SELECT locationid FROM candidate_zones)
      OR e.dropoff_location_id IN (SELECT locationid FROM candidate_zones)
  );

CREATE INDEX IF NOT EXISTS idx_trip_fact_normalized_service_period
    ON analysis.trip_fact_normalized (service_date, pickup_hour, pickup_isodow);
CREATE INDEX IF NOT EXISTS idx_trip_fact_normalized_locations
    ON analysis.trip_fact_normalized (pickup_location_id, dropoff_location_id);

{prefix}3: build the zero-filled daily airport-zone mart
CREATE MATERIALIZED VIEW analysis.airport_zone_daily AS
WITH candidate_zones AS (
    SELECT
        z.locationid,
        z.borough,
        z.zone,
        z.service_zone
    FROM raw.zone_lookup z
    WHERE z.borough IN ({borough_values})
      AND z.service_zone IN ({service_zone_values})
      AND z.zone NOT IN ({exclude_zone_values})
),
periodized AS (
    SELECT
        p.period,
        p.direction,
        t.service_date,
        CASE
            WHEN p.direction = 'to_airport' THEN t.pickup_location_id
            ELSE t.dropoff_location_id
        END AS zone_id,
        CASE
            WHEN p.direction = 'to_airport' THEN t.pickup_zone_name
            ELSE t.dropoff_zone_name
        END AS zone_name,
        CASE
            WHEN p.direction = 'to_airport' THEN t.pickup_borough
            ELSE t.dropoff_borough
        END AS borough,
        CASE
            WHEN p.direction = 'to_airport' THEN t.dropoff_location_id
            ELSE t.pickup_location_id
        END AS airport_zone_id
    FROM analysis.trip_fact_normalized t
    JOIN analysis._cfg_period_rules p
      ON t.pickup_hour BETWEEN p.pickup_hour_start AND p.pickup_hour_end
),
period_candidate_trips AS (
    SELECT
        p.period,
        p.service_date,
        p.zone_id,
        p.zone_name,
        p.borough,
        m.airport_code
    FROM periodized p
    JOIN candidate_zones c
      ON c.locationid = p.zone_id
    LEFT JOIN analysis._cfg_airport_mapping m
      ON m.zone_id = p.airport_zone_id
),
partner_zone_day AS (
    SELECT
        period,
        zone_id,
        zone_name,
        borough,
        service_date,
        COUNT(*)::bigint AS total_trip_count
    FROM period_candidate_trips
    GROUP BY period, zone_id, zone_name, borough, service_date
),
airport_zone_day AS (
    SELECT
        p.period,
        p.airport_code,
        p.zone_id,
        p.zone_name,
        p.borough,
        p.service_date,
        COUNT(*)::bigint AS airport_trip_count
    FROM period_candidate_trips p
    JOIN analysis._cfg_period_airports a
      ON a.period = p.period
     AND a.airport_code = p.airport_code
    GROUP BY p.period, p.airport_code, p.zone_id, p.zone_name, p.borough, p.service_date
),
observed_pairs AS (
    SELECT DISTINCT
        period,
        airport_code,
        zone_id,
        zone_name,
        borough
    FROM airport_zone_day
)
SELECT
    z.service_date,
    p.period,
    p.airport_code,
    p.zone_id,
    p.zone_name,
    p.borough,
    COALESCE(a.airport_trip_count, 0)::bigint AS airport_trip_count,
    z.total_trip_count,
    COALESCE(a.airport_trip_count, 0)::double precision / NULLIF(z.total_trip_count, 0) AS airport_trip_share
FROM observed_pairs p
JOIN partner_zone_day z
  ON z.period = p.period
 AND z.zone_id = p.zone_id
 AND z.zone_name = p.zone_name
 AND z.borough = p.borough
LEFT JOIN airport_zone_day a
  ON a.period = p.period
 AND a.airport_code = p.airport_code
 AND a.zone_id = p.zone_id
 AND a.zone_name = p.zone_name
 AND a.borough = p.borough
 AND a.service_date = z.service_date;

CREATE INDEX IF NOT EXISTS idx_airport_zone_daily_lookup
    ON analysis.airport_zone_daily (period, airport_code, service_date, zone_id);
CREATE INDEX IF NOT EXISTS idx_airport_zone_daily_service_date
    ON analysis.airport_zone_daily (service_date, period, zone_id);

{prefix}4: aggregate rolling window metrics for configured snapshots
CREATE MATERIALIZED VIEW analysis.airport_zone_rolling_7d AS
WITH windowed AS (
    SELECT
        s.snapshot_date,
        d.service_date,
        d.period,
        d.airport_code,
        d.zone_id,
        d.zone_name,
        d.borough,
        d.airport_trip_count,
        d.total_trip_count
    FROM analysis._cfg_snapshot_dates s
    JOIN analysis.airport_zone_daily d
      ON d.service_date BETWEEN (s.snapshot_date - INTERVAL '{window_back_days} day')::date
                           AND s.snapshot_date
)
SELECT
    snapshot_date,
    period,
    airport_code,
    zone_id,
    zone_name,
    borough,
    COUNT(*) FILTER (WHERE airport_trip_count > 0)::int AS active_days_in_window,
    SUM(airport_trip_count)::bigint AS rolling_airport_trip_count,
    SUM(total_trip_count)::bigint AS rolling_total_trip_count,
    SUM(airport_trip_count)::double precision / NULLIF(SUM(total_trip_count), 0) AS rolling_airport_trip_share
FROM windowed
GROUP BY snapshot_date, period, airport_code, zone_id, zone_name, borough;

CREATE INDEX IF NOT EXISTS idx_airport_zone_rolling_7d_lookup
    ON analysis.airport_zone_rolling_7d (snapshot_date, period, airport_code, zone_id);
CREATE INDEX IF NOT EXISTS idx_airport_zone_rolling_7d_active_days
    ON analysis.airport_zone_rolling_7d (active_days_in_window);

{prefix}5: compute weighted rolling opportunity scores and retain top-k leaderboard rows
CREATE MATERIALIZED VIEW analysis.airport_zone_snapshot_leaderboard AS
WITH eligible AS (
    SELECT
        r.snapshot_date,
        r.period,
        r.airport_code,
        r.zone_id,
        r.zone_name,
        r.borough,
        r.active_days_in_window,
        r.rolling_airport_trip_count,
        r.rolling_total_trip_count,
        r.rolling_airport_trip_share
    FROM analysis.airport_zone_rolling_7d r
    WHERE r.active_days_in_window >= {int(rolling["min_active_days_in_window"])}
),
scored AS (
    SELECT
        e.*,
        COALESCE(
            e.rolling_airport_trip_count::double precision
            / NULLIF(MAX(e.rolling_airport_trip_count) OVER (
                PARTITION BY e.snapshot_date, e.period, e.airport_code
            ), 0),
            0.0
        ) AS count_component,
        COALESCE(
            e.rolling_airport_trip_share
            / NULLIF(MAX(e.rolling_airport_trip_share) OVER (
                PARTITION BY e.snapshot_date, e.period, e.airport_code
            ), 0),
            0.0
        ) AS share_component,
        COALESCE(
            e.active_days_in_window::double precision
            / NULLIF(MAX(e.active_days_in_window) OVER (
                PARTITION BY e.snapshot_date, e.period, e.airport_code
            ), 0),
            0.0
        ) AS active_days_component
    FROM eligible e
),
ranked AS (
    SELECT
        s.snapshot_date,
        s.period,
        s.airport_code,
        s.zone_id,
        s.zone_name,
        s.borough,
        s.active_days_in_window,
        s.rolling_airport_trip_count,
        s.rolling_total_trip_count,
        s.rolling_airport_trip_share,
        (
            {sql_num(ranking["count_weight"])} * s.count_component
            + {sql_num(ranking["share_weight"])} * s.share_component
            + {sql_num(ranking["active_days_weight"])} * s.active_days_component
        ) AS rolling_opportunity_score
    FROM scored s
),
ordered AS (
    SELECT
        r.*,
        ROW_NUMBER() OVER (
            PARTITION BY r.snapshot_date, r.period, r.airport_code
            ORDER BY
                r.rolling_opportunity_score DESC,
                r.rolling_airport_trip_count DESC,
                r.rolling_airport_trip_share DESC,
                r.zone_id ASC
        ) AS rank
    FROM ranked r
)
SELECT
    o.snapshot_date,
    o.period,
    o.airport_code,
    o.rank,
    o.zone_id,
    o.zone_name,
    o.borough,
    o.active_days_in_window,
    o.rolling_airport_trip_count,
    o.rolling_total_trip_count,
    o.rolling_airport_trip_share,
    o.rolling_opportunity_score
FROM ordered o
JOIN analysis._cfg_period_rules p
  ON p.period = o.period
WHERE o.rank <= p.top_k;

CREATE INDEX IF NOT EXISTS idx_airport_zone_snapshot_leaderboard_lookup
    ON analysis.airport_zone_snapshot_leaderboard (snapshot_date, period, airport_code, rank);

{prefix}6: refresh planner statistics for repeated analytical runs
ANALYZE analysis.trip_fact_normalized;
ANALYZE analysis.airport_zone_daily;
ANALYZE analysis.airport_zone_rolling_7d;
ANALYZE analysis.airport_zone_snapshot_leaderboard;
"""


def export_outputs(output_root: Path) -> tuple[pd.DataFrame, pd.DataFrame]:
    daily = query_to_frame(
        """
        SELECT
            service_date,
            period,
            airport_code,
            zone_id,
            zone_name,
            borough,
            airport_trip_count,
            total_trip_count,
            airport_trip_share
        FROM analysis.airport_zone_daily
        ORDER BY service_date, period, airport_code, zone_id
        """
    )
    leaderboard = query_to_frame(
        """
        SELECT
            snapshot_date,
            period,
            airport_code,
            rank,
            zone_id,
            zone_name,
            borough,
            active_days_in_window,
            rolling_airport_trip_count,
            rolling_total_trip_count,
            rolling_airport_trip_share,
            rolling_opportunity_score
        FROM analysis.airport_zone_snapshot_leaderboard
        ORDER BY snapshot_date, period, airport_code, rank, zone_id
        """
    )

    daily = daily[DAILY_COLUMNS].copy()
    leaderboard = leaderboard[LEADERBOARD_COLUMNS].copy()
    daily.to_csv(output_root / "airport_zone_daily_mart.csv", index=False)
    leaderboard.to_csv(output_root / "airport_zone_snapshot_leaderboard.tsv", sep="\t", index=False)
    return daily, leaderboard


def build_benchmark_report(contract: dict, daily: pd.DataFrame, leaderboard: pd.DataFrame) -> str:
    benchmark = contract["benchmark"]
    filters = benchmark["benchmark_filters"]
    ranked_rows = leaderboard.sort_values(
        ["snapshot_date", "period", "airport_code", "rank", "zone_id"]
    ).reset_index(drop=True)
    ranked_zones = sorted(ranked_rows["zone_name"].dropna().astype(str).unique().tolist())

    lines: list[str] = []
    lines.append("# Scope")
    lines.append(
        "This report covers the indexed rolling-mart pipeline over weekday service dates in the "
        f"{contract['analysis_window']['start_date']} to {contract['analysis_window']['end_date']} window, "
        "using New York local pickup timestamps for period assignment."
    )
    lines.append(
        f"Benchmark focus filters: periods={filters['periods']}, airports={filters['airport_codes']}, "
        f"service_date range={filters['service_date_from']} to {filters['service_date_to']}."
    )
    lines.append("")
    lines.append("# Daily mart")
    lines.append(
        f"Materialized object `{benchmark['target_relation']}` was rebuilt from "
        "`analysis.trip_fact_normalized` using contract-scoped airport-zone pairs and zero-filled daily rows."
    )
    lines.append(
        f"Exported rows: {len(daily)}. Distinct periods: {daily['period'].nunique()}. "
        f"Distinct airport-zone pairs: {daily[['period', 'airport_code', 'zone_id']].drop_duplicates().shape[0]}."
    )
    lines.append("")
    lines.append("# Snapshot leaderboard")
    lines.append(
        f"Rolling window width: {contract['rolling_window']['service_dates_in_window']} service dates. "
        f"Minimum active days filter: {contract['rolling_window']['min_active_days_in_window']}."
    )
    lines.append(f"Leaderboard rows: {len(leaderboard)}.")
    lines.append("Ranked zones in leaderboard output:")
    if ranked_rows.empty:
        lines.append("- none")
    else:
        for row in ranked_rows.itertuples(index=False):
            lines.append(
                f"- {row.snapshot_date} | {row.period} | {row.airport_code} | rank {int(row.rank)} | "
                f"zone {int(row.zone_id)} {row.zone_name}"
            )
    if ranked_zones:
        lines.append("Unique ranked zone names: " + ", ".join(ranked_zones))
    lines.append("")
    lines.append("# Index strategy")
    lines.append("The SQL pack recreates helper config tables and four contract objects as materialized views.")
    lines.append(
        "Indexes target repeated snapshot runs: "
        "`trip_fact_normalized(service_date,pickup_hour,pickup_isodow)`, "
        "`trip_fact_normalized(pickup_location_id,dropoff_location_id)`, "
        "`airport_zone_daily(period,airport_code,service_date,zone_id)`, "
        "`airport_zone_rolling_7d(snapshot_date,period,airport_code,zone_id)`, and "
        "`airport_zone_snapshot_leaderboard(snapshot_date,period,airport_code,rank)`."
    )
    return "\n".join(lines) + "\n"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--data", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()

    data_root = Path(args.data)
    output_root = Path(args.output)
    output_root.mkdir(parents=True, exist_ok=True)

    subprocess.run(
        ["/root/workspace/bin/init_airport_ops.sh"],
        check=True,
        capture_output=True,
        text=True,
    )

    for table in [
        "raw.dispatch_batch_a",
        "raw.dispatch_batch_b",
        "raw.dispatch_batch_c",
        "raw.dispatch_batch_d",
        "raw.zone_lookup",
    ]:
        psql_scalar(f"SELECT count(*) FROM {table}")

    contract = json.loads((data_root / "analysis_contract.json").read_text(encoding="utf-8"))
    query_pack = build_query_pack(contract)
    (output_root / "query_pack.sql").write_text(query_pack, encoding="utf-8")
    execute_query_pack(query_pack)

    daily, leaderboard = export_outputs(output_root)
    report = build_benchmark_report(contract, daily, leaderboard)
    (output_root / "benchmark_report.md").write_text(report, encoding="utf-8")


if __name__ == "__main__":
    main()
