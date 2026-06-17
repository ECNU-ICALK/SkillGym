#!/usr/bin/env bash
set -Eeuo pipefail

OPEN_AIRPORTS_FILE="$1"
RUNWAYS_FILE="$2"
OUTPUT_FILE="$3"
WORK_DIR="$(dirname -- "$OUTPUT_FILE")"
SORTED_AIRPORTS=""
SORTED_RUNWAYS=""

cleanup() {
  [[ -n "${SORTED_AIRPORTS:-}" && -f "${SORTED_AIRPORTS:-}" ]] && rm -f -- "$SORTED_AIRPORTS"
  [[ -n "${SORTED_RUNWAYS:-}" && -f "${SORTED_RUNWAYS:-}" ]] && rm -f -- "$SORTED_RUNWAYS"
}

trap cleanup EXIT

[[ -f "$OPEN_AIRPORTS_FILE" ]] || {
  printf 'missing open airports input: %s\n' "$OPEN_AIRPORTS_FILE" >&2
  exit 1
}
[[ -f "$RUNWAYS_FILE" ]] || {
  printf 'missing runways input: %s\n' "$RUNWAYS_FILE" >&2
  exit 1
}

SORTED_AIRPORTS="$(mktemp "${WORK_DIR%/}/open-airports.XXXXXX")"
SORTED_RUNWAYS="$(mktemp "${WORK_DIR%/}/runway-stats.XXXXXX")"

tail -n +2 -- "$OPEN_AIRPORTS_FILE" | sort -t $'\t' -k1,1 > "$SORTED_AIRPORTS"
tail -n +2 -- "$RUNWAYS_FILE" | awk -F $'\t' '
  BEGIN { OFS = FS }
  $5 != "1" {
    dedupe_key = $1 OFS $2 OFS $3 OFS $4 OFS $5
    if (seen[dedupe_key]++) {
      next
    }
    count[$1] += 1
    if ($2 != "") {
      runway_length = $2 + 0
      if (!(has_length[$1]) || runway_length > max[$1]) {
        max[$1] = runway_length
      }
      has_length[$1] = 1
    }
  }
  END {
    for (airport in count) {
      longest = has_length[airport] ? max[airport] : ""
      print airport, count[airport], longest
    }
  }
' | sort -t $'\t' -k1,1 > "$SORTED_RUNWAYS"

printf 'airport_ident\tairport_type\tairport_name\tcountry_code\tregion_code\tmunicipality\tscheduled_service\trunway_count\tlongest_runway_ft\n' > "$OUTPUT_FILE"
join -t $'\t' -a 1 -e '' -o '0,1.2,1.3,1.4,1.5,1.6,1.7,2.2,2.3' "$SORTED_AIRPORTS" "$SORTED_RUNWAYS" | awk -F $'\t' '
  BEGIN { OFS = FS }
  {
    if ($8 == "") {
      $8 = 0
    }
    print $1, $2, $3, $4, $5, $6, $7, $8, $9
  }
' >> "$OUTPUT_FILE"
