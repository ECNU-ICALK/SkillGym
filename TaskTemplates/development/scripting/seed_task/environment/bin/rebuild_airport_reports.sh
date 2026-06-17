#!/usr/bin/env bash
set -eu

SCRIPT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
APP_ROOT=$(cd "$SCRIPT_DIR/.." && pwd)
DATA_DIR=${AIRPORTS_DATA_DIR:-"$APP_ROOT/data/ourairports"}
OUTPUT_DIR=${AIRPORTS_OUTPUT_DIR:-"$APP_ROOT/output"}
TMP_ROOT=${AIRPORTS_TMP_DIR:-/tmp/airport-report-work}
LOCK_DIR=${TMP_ROOT%/}/.rebuild.lock
WORK_DIR=${TMP_ROOT%/}/current-run
LOG_FILE="$OUTPUT_DIR/rebuild.log"

cleanup_lock() {
  rmdir "$LOCK_DIR" 2>/dev/null || true
}

mkdir -p "$OUTPUT_DIR" "$TMP_ROOT"
mkdir "$LOCK_DIR"
trap cleanup_lock EXIT
rm -rf "$WORK_DIR"
mkdir -p "$WORK_DIR"
echo "pipeline=airport-report start=$(date -u +%Y-%m-%dT%H:%M:%SZ)" > "$LOG_FILE"
echo "stage=extract_open_airports" >> "$LOG_FILE"
"$SCRIPT_DIR/steps/extract_open_airports.sh" "$DATA_DIR/airports.tsv" "$WORK_DIR/open_airports.tsv" >> "$LOG_FILE" 2>&1
echo "stage=join_runway_stats" >> "$LOG_FILE"
"$SCRIPT_DIR/steps/join_runway_stats.sh" "$WORK_DIR/open_airports.tsv" "$DATA_DIR/runways.tsv" "$WORK_DIR/open_airports_with_runways.tsv" >> "$LOG_FILE" 2>&1
echo "stage=build_reports" >> "$LOG_FILE"
"$SCRIPT_DIR/steps/build_reports.sh" "$DATA_DIR/countries.tsv" "$DATA_DIR/regions.tsv" "$DATA_DIR/airports.tsv" "$WORK_DIR/open_airports_with_runways.tsv" "$OUTPUT_DIR/country_airport_summary.csv" "$OUTPUT_DIR/region_priority_report.json" >> "$LOG_FILE" 2>&1
echo "status=ok finished=$(date -u +%Y-%m-%dT%H:%M:%SZ)" >> "$LOG_FILE"
