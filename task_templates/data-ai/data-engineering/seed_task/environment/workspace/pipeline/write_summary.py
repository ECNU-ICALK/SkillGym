#!/usr/bin/env python3

import json
import subprocess
from pathlib import Path


ROOT_DIR = Path(__file__).resolve().parents[1]
OUTPUT_PATH = ROOT_DIR / "output" / "summary.json"


def scalar(query: str) -> str:
    result = subprocess.run(
        ["clickhouse-client", "--query", query],
        check=True,
        capture_output=True,
        text=True,
    )
    return result.stdout.strip()


def main() -> None:
    months = scalar(
        """
        SELECT toJSONString(groupArray(source_month))
        FROM (
            SELECT DISTINCT source_month
            FROM analytics.trips_raw
            ORDER BY source_month
        )
        """
    )

    payload = {
        "source_months": json.loads(months) if months else [],
        "raw_trip_rows": int(scalar("SELECT count() FROM analytics.trips_raw")),
        "accepted_trip_rows": int(scalar("SELECT count() FROM analytics.trips_clean")),
        "daily_borough_metrics_rows": int(scalar("SELECT count() FROM analytics.daily_borough_metrics")),
        "top_zone_routes_rows": int(scalar("SELECT count() FROM analytics.top_zone_routes")),
    }

    OUTPUT_PATH.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()

