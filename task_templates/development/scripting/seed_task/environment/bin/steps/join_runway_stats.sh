#!/usr/bin/env bash
set -eu

OPEN_AIRPORTS_FILE=$1
RUNWAYS_FILE=$2
OUTPUT_FILE=$3

SORTED_AIRPORTS=${OUTPUT_FILE}.airports
SORTED_RUNWAYS=${OUTPUT_FILE}.runways

tail -n +2 "$OPEN_AIRPORTS_FILE" | sort -t $'\t' -k1,1 > "$SORTED_AIRPORTS"
tail -n +2 "$RUNWAYS_FILE" | awk -F $'\t' '
  BEGIN { OFS = FS }
  $5 != "1" {
    count[$1] += 1
    if ($2 != "" && ($2 + 0) > max[$1]) {
      max[$1] = $2 + 0
    }
  }
  END {
    for (airport in count) {
      print airport, count[airport], max[airport]
    }
  }
' | sort -t $'\t' -k1,1 > "$SORTED_RUNWAYS"

printf 'airport_ident\tairport_type\tairport_name\tcountry_code\tregion_code\tmunicipality\tscheduled_service\trunway_count\tlongest_runway_ft\n' > "$OUTPUT_FILE"
join -t $'\t' -1 1 -2 1 "$SORTED_AIRPORTS" "$SORTED_RUNWAYS" | awk -F $'\t' '
  BEGIN { OFS = FS }
  { print $1, $2, $3, $4, $5, $6, $7, $8, $9 }
' >> "$OUTPUT_FILE"
