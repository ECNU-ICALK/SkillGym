#!/usr/bin/env bash
set -Eeuo pipefail

COUNTRIES_FILE="$1"
REGIONS_FILE="$2"
AIRPORTS_FILE="$3"
OPEN_AIRPORTS_WITH_RUNWAYS_FILE="$4"
COUNTRY_OUTPUT_FILE="$5"
REGION_OUTPUT_FILE="$6"

for input_file in "$COUNTRIES_FILE" "$REGIONS_FILE" "$AIRPORTS_FILE" "$OPEN_AIRPORTS_WITH_RUNWAYS_FILE"; do
  [[ -f "$input_file" ]] || {
    printf 'missing stage input: %s\n' "$input_file" >&2
    exit 1
  }
done

python3 - "$COUNTRIES_FILE" "$REGIONS_FILE" "$AIRPORTS_FILE" "$OPEN_AIRPORTS_WITH_RUNWAYS_FILE" "$COUNTRY_OUTPUT_FILE" "$REGION_OUTPUT_FILE" <<'PY'
from __future__ import annotations

import csv
import json
import sys
from pathlib import Path

countries_file = Path(sys.argv[1])
regions_file = Path(sys.argv[2])
airports_file = Path(sys.argv[3])
open_with_runways_file = Path(sys.argv[4])
country_output_file = Path(sys.argv[5])
region_output_file = Path(sys.argv[6])


def read_tsv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle, delimiter="\t"))


countries = read_tsv(countries_file)
regions = read_tsv(regions_file)
airports = read_tsv(airports_file)
open_airports_with_runways = read_tsv(open_with_runways_file)

countries_by_code = {row["country_code"]: row for row in countries}
regions_by_code = {row["region_code"]: row for row in regions}
open_airports = [row for row in airports if row["airport_type"] != "closed"]
open_idents = {row["airport_ident"] for row in open_airports}
enriched_idents = {row["airport_ident"] for row in open_airports_with_runways}
if open_idents != enriched_idents:
    missing = sorted(open_idents - enriched_idents)
    extra = sorted(enriched_idents - open_idents)
    raise SystemExit(f"open-airport enrichment mismatch missing={missing[:5]} extra={extra[:5]}")

runway_stats = {}
for row in open_airports_with_runways:
    runway_stats[row["airport_ident"]] = {
        "runway_count": int(row["runway_count"] or 0),
        "longest_runway_ft": int(row["longest_runway_ft"]) if row["longest_runway_ft"] else "",
    }

country_rows: list[list[object]] = [[
    "country_code",
    "country_name",
    "airport_count",
    "open_airport_count",
    "scheduled_open_airport_count",
    "runway_count",
    "longest_runway_ft",
]]

for country in sorted(countries, key=lambda row: row["country_code"]):
    country_airports = [row for row in airports if row["country_code"] == country["country_code"]]
    open_country_airports = [row for row in country_airports if row["airport_type"] != "closed"]
    scheduled_open_airport_count = sum(1 for row in open_country_airports if row["scheduled_service"] == "yes")
    runway_count = 0
    longest: object = ""
    for airport in open_country_airports:
        stats = runway_stats[airport["airport_ident"]]
        runway_count += int(stats["runway_count"])
        candidate = stats["longest_runway_ft"]
        if candidate != "" and (longest == "" or int(candidate) > int(longest)):
            longest = int(candidate)
    country_rows.append([
        country["country_code"],
        country["country_name"],
        len(country_airports),
        len(open_country_airports),
        scheduled_open_airport_count,
        runway_count,
        longest,
    ])

with country_output_file.open("w", newline="", encoding="utf-8") as handle:
    writer = csv.writer(handle)
    writer.writerows(country_rows)

grouped_regions: dict[str, dict[str, object]] = {}
for airport in open_airports:
    region = regions_by_code[airport["region_code"]]
    country = countries_by_code[airport["country_code"]]
    stats = runway_stats[airport["airport_ident"]]
    bucket = grouped_regions.setdefault(
        airport["region_code"],
        {
            "region_code": region["region_code"],
            "region_name": region["region_name"],
            "country_code": country["country_code"],
            "country_name": country["country_name"],
            "open_airport_count": 0,
            "scheduled_open_airport_count": 0,
            "runway_count": 0,
            "longest_runway_ft": "",
        },
    )
    bucket["open_airport_count"] = int(bucket["open_airport_count"]) + 1
    bucket["scheduled_open_airport_count"] = int(bucket["scheduled_open_airport_count"]) + (1 if airport["scheduled_service"] == "yes" else 0)
    bucket["runway_count"] = int(bucket["runway_count"]) + int(stats["runway_count"])
    candidate = stats["longest_runway_ft"]
    if candidate != "" and (bucket["longest_runway_ft"] == "" or int(candidate) > int(bucket["longest_runway_ft"])):
        bucket["longest_runway_ft"] = int(candidate)

ordered_regions = sorted(
    grouped_regions.values(),
    key=lambda row: (-int(row["scheduled_open_airport_count"]), -int(row["open_airport_count"]), row["region_code"]),
)

region_output_file.write_text(
    json.dumps({"generated_from": "ourairports", "regions": ordered_regions}, ensure_ascii=False, indent=2) + "\n",
    encoding="utf-8",
)
PY
