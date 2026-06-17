#!/usr/bin/env bash

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")"/.. && pwd)"
OUTPUT_PATH="$ROOT_DIR/output/summary.json"

SOURCE_MONTHS_JSON="$(clickhouse-client --query "
SELECT toJSONString(groupArray(source_month))
FROM (
    SELECT DISTINCT source_month
    FROM analytics.trips_raw
    ORDER BY source_month
)
")"

RAW_TRIP_ROWS="$(clickhouse-client --query "SELECT count() FROM analytics.trips_raw")"
ACCEPTED_TRIP_ROWS="$(clickhouse-client --query "SELECT count() FROM analytics.trips_clean")"
DAILY_ROWS="$(clickhouse-client --query "SELECT count() FROM analytics.daily_borough_metrics")"
TOP_ROWS="$(clickhouse-client --query "SELECT count() FROM analytics.top_zone_routes")"

cat > "$OUTPUT_PATH" <<EOF
{
  "source_months": ${SOURCE_MONTHS_JSON:-[]},
  "raw_trip_rows": ${RAW_TRIP_ROWS},
  "accepted_trip_rows": ${ACCEPTED_TRIP_ROWS},
  "daily_borough_metrics_rows": ${DAILY_ROWS},
  "top_zone_routes_rows": ${TOP_ROWS}
}
EOF

