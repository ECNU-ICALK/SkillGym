#!/usr/bin/env bash
set -euo pipefail

cp /solution/fixed/bin/rebuild_airport_reports.sh /app/bin/rebuild_airport_reports.sh
cp /solution/fixed/bin/steps/extract_open_airports.sh /app/bin/steps/extract_open_airports.sh
cp /solution/fixed/bin/steps/join_runway_stats.sh /app/bin/steps/join_runway_stats.sh
cp /solution/fixed/bin/steps/build_reports.sh /app/bin/steps/build_reports.sh

chmod +x /app/bin/rebuild_airport_reports.sh /app/bin/steps/*.sh
