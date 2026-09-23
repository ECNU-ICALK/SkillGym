#!/usr/bin/env bash
set -Eeuo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"
APP_ROOT="$(cd -- "$SCRIPT_DIR/.." && pwd -P)"
DATA_DIR="${AIRPORTS_DATA_DIR:-$APP_ROOT/data/ourairports}"
OUTPUT_DIR="${AIRPORTS_OUTPUT_DIR:-$APP_ROOT/output}"
TMP_ROOT="${AIRPORTS_TMP_DIR:-${AIRPORTS_TMP_PARENT:-${TMPDIR:-/tmp}}/airport-report-work}"
LOG_FILE="$OUTPUT_DIR/rebuild.log"
TMP_DIR=""
LOCK_DIR="$OUTPUT_DIR/.rebuild.lock"
LOCK_HELD=0

cleanup() {
  if [[ -n "${TMP_DIR:-}" && -d "${TMP_DIR:-}" ]]; then
    rm -rf -- "$TMP_DIR"
  fi
  if [[ "${LOCK_HELD:-0}" -eq 1 && -d "${LOCK_DIR:-}" ]]; then
    rmdir -- "$LOCK_DIR" 2>/dev/null || true
  fi
}

log() {
  printf '[%s] %s\n' "$(date -u +%Y-%m-%dT%H:%M:%SZ)" "$*" >> "$LOG_FILE"
}

on_error() {
  local exit_code=$?
  log "status=error exit_code=${exit_code}"
  exit "$exit_code"
}

trap cleanup EXIT
trap on_error ERR

for command_name in awk join mktemp python3 sort tail; do
  command -v "$command_name" >/dev/null 2>&1 || {
    printf 'missing command: %s\n' "$command_name" >&2
    exit 1
  }
done

mkdir -p -- "$OUTPUT_DIR"
if ! mkdir -- "$LOCK_DIR" 2>/dev/null; then
  printf 'another rebuild is already running for output dir: %s\n' "$OUTPUT_DIR" >&2
  exit 1
fi
LOCK_HELD=1
: > "$LOG_FILE"
rm -f -- \
  "$OUTPUT_DIR/country_airport_summary.csv" \
  "$OUTPUT_DIR/region_priority_report.json"
log "pipeline=airport-report"
log "data_dir=$DATA_DIR"
log "output_dir=$OUTPUT_DIR"

for input_file in \
  "$DATA_DIR/countries.tsv" \
  "$DATA_DIR/regions.tsv" \
  "$DATA_DIR/airports.tsv" \
  "$DATA_DIR/runways.tsv"
do
  [[ -f "$input_file" ]] || {
    printf 'missing input file: %s\n' "$input_file" >&2
    exit 1
  }
done

mkdir -p -- "$TMP_ROOT"
TMP_DIR="$(mktemp -d "${TMP_ROOT%/}/run.XXXXXX")"
log "run_dir=$TMP_DIR"
COUNTRY_STAGE="$TMP_DIR/country_airport_summary.csv"
REGION_STAGE="$TMP_DIR/region_priority_report.json"

log "stage=extract_open_airports"
"$SCRIPT_DIR/steps/extract_open_airports.sh" \
  "$DATA_DIR/airports.tsv" \
  "$TMP_DIR/open_airports.tsv"

log "stage=join_runway_stats"
"$SCRIPT_DIR/steps/join_runway_stats.sh" \
  "$TMP_DIR/open_airports.tsv" \
  "$DATA_DIR/runways.tsv" \
  "$TMP_DIR/open_airports_with_runways.tsv"

log "stage=build_reports"
"$SCRIPT_DIR/steps/build_reports.sh" \
  "$DATA_DIR/countries.tsv" \
  "$DATA_DIR/regions.tsv" \
  "$DATA_DIR/airports.tsv" \
  "$TMP_DIR/open_airports_with_runways.tsv" \
  "$COUNTRY_STAGE" \
  "$REGION_STAGE"

mv -- "$COUNTRY_STAGE" "$OUTPUT_DIR/country_airport_summary.csv"
mv -- "$REGION_STAGE" "$OUTPUT_DIR/region_priority_report.json"
log "status=ok"
